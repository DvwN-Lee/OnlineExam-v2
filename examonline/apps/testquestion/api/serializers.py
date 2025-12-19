"""
Question Management API serializers.
"""

from django.db import transaction
from rest_framework import serializers

from testquestion.models import TestQuestionInfo, OptionInfo
from user.api.serializers import SubjectSerializer
from user.models import SubjectInfo


class OptionReadSerializer(serializers.ModelSerializer):
    """
    Option 조회용 Serializer.
    """

    class Meta:
        model = OptionInfo
        fields = ['id', 'option', 'is_right', 'create_time']
        read_only_fields = ['id', 'create_time']


class OptionWriteSerializer(serializers.ModelSerializer):
    """
    Option 생성/수정용 Serializer.
    ID는 optional (수정 시 사용).
    """

    id = serializers.IntegerField(required=False)

    class Meta:
        model = OptionInfo
        fields = ['id', 'option', 'is_right']


class QuestionListSerializer(serializers.ModelSerializer):
    """
    문제 목록 조회용 경량 Serializer.
    옵션은 포함하지 않음.
    """

    subject = SubjectSerializer(read_only=True)
    create_user_name = serializers.CharField(source='create_user.nick_name', read_only=True)
    tq_type_display = serializers.CharField(source='get_tq_type_display', read_only=True)
    tq_degree_display = serializers.CharField(source='get_tq_degree_display', read_only=True)

    class Meta:
        model = TestQuestionInfo
        fields = [
            'id',
            'name',
            'subject',
            'score',
            'tq_type',
            'tq_type_display',
            'tq_degree',
            'tq_degree_display',
            'is_share',
            'create_time',
            'edit_time',
            'create_user_name',
        ]
        read_only_fields = ['id', 'create_time', 'edit_time', 'create_user_name']


class QuestionDetailSerializer(serializers.ModelSerializer):
    """
    문제 상세 조회용 Serializer.
    옵션 목록 포함.
    """

    subject = SubjectSerializer(read_only=True)
    create_user_name = serializers.CharField(source='create_user.nick_name', read_only=True)
    options = OptionReadSerializer(source='optioninfo_set', many=True, read_only=True)
    tq_type_display = serializers.CharField(source='get_tq_type_display', read_only=True)
    tq_degree_display = serializers.CharField(source='get_tq_degree_display', read_only=True)

    class Meta:
        model = TestQuestionInfo
        fields = [
            'id',
            'name',
            'subject',
            'score',
            'tq_type',
            'tq_type_display',
            'tq_degree',
            'tq_degree_display',
            'image',
            'is_share',
            'create_time',
            'edit_time',
            'create_user_name',
            'options',
        ]
        read_only_fields = ['id', 'create_time', 'edit_time', 'create_user_name', 'options']


class QuestionCreateSerializer(serializers.ModelSerializer):
    """
    문제 생성용 Serializer.
    옵션을 nested로 함께 생성.
    """

    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=SubjectInfo.objects.all(), source='subject', write_only=True
    )
    options = OptionWriteSerializer(many=True, required=False)

    class Meta:
        model = TestQuestionInfo
        fields = ['name', 'subject_id', 'score', 'tq_type', 'tq_degree', 'image', 'is_share', 'options']

    def validate(self, attrs):
        """
        객관식(xz)인 경우 최소 2개 이상의 옵션 필요.
        정답 옵션이 최소 1개 이상 있어야 함.
        """
        tq_type = attrs.get('tq_type', 'xz')
        options = attrs.get('options', [])

        if tq_type == 'xz':
            if len(options) < 2:
                raise serializers.ValidationError({'options': '객관식 문제는 최소 2개 이상의 옵션이 필요합니다.'})
            if not any(opt.get('is_right') for opt in options):
                raise serializers.ValidationError({'options': '최소 1개 이상의 정답 옵션이 필요합니다.'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        options_data = validated_data.pop('options', [])
        validated_data['create_user'] = self.context['request'].user

        question = TestQuestionInfo.objects.create(**validated_data)

        for option_data in options_data:
            OptionInfo.objects.create(test_question=question, **option_data)

        return question


class QuestionUpdateSerializer(serializers.ModelSerializer):
    """
    문제 수정용 Serializer.
    옵션은 ID 기반 부분 수정 지원.
    """

    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=SubjectInfo.objects.all(), source='subject', write_only=True, required=False
    )
    options = OptionWriteSerializer(many=True, required=False)

    class Meta:
        model = TestQuestionInfo
        fields = ['name', 'subject_id', 'score', 'tq_type', 'tq_degree', 'image', 'is_share', 'options']

    def validate(self, attrs):
        """
        객관식 문제에 대한 옵션 검증 (update 시에도 적용).
        """
        tq_type = attrs.get('tq_type', self.instance.tq_type if self.instance else 'xz')
        options = attrs.get('options')

        if options is not None and tq_type == 'xz':
            if len(options) < 2:
                raise serializers.ValidationError({'options': '객관식 문제는 최소 2개 이상의 옵션이 필요합니다.'})
            if not any(opt.get('is_right') for opt in options):
                raise serializers.ValidationError({'options': '최소 1개 이상의 정답 옵션이 필요합니다.'})
        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        options_data = validated_data.pop('options', None)

        # Update question fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update options if provided
        if options_data is not None:
            existing_option_ids = set()

            for option_data in options_data:
                option_id = option_data.pop('id', None)
                if option_id:
                    # Update existing option
                    option = OptionInfo.objects.filter(id=option_id, test_question=instance).first()
                    if option:
                        for attr, value in option_data.items():
                            setattr(option, attr, value)
                        option.save()
                        existing_option_ids.add(option_id)
                else:
                    # Create new option
                    new_option = OptionInfo.objects.create(test_question=instance, **option_data)
                    existing_option_ids.add(new_option.id)

            # Delete options not in the update list
            instance.optioninfo_set.exclude(id__in=existing_option_ids).delete()

        return instance


class QuestionShareSerializer(serializers.Serializer):
    """
    문제 공유 상태 변경용 Serializer.
    """

    is_share = serializers.BooleanField(required=True)
