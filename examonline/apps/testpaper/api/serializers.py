"""
Test Paper Management API serializers.
"""

from django.db import transaction
from django.db.models import Sum
from rest_framework import serializers

from testpaper.models import TestPaperInfo, TestPaperTestQ
from testquestion.api.serializers import QuestionListSerializer
from testquestion.models import TestQuestionInfo
from user.api.serializers import SubjectSerializer
from user.models import SubjectInfo


class PaperQuestionReadSerializer(serializers.ModelSerializer):
    """
    시험지 내 문제 조회용 Serializer (nested).
    문제 정보와 배점, 순서 포함.
    """

    test_question = QuestionListSerializer(read_only=True)

    class Meta:
        model = TestPaperTestQ
        fields = ['id', 'test_question', 'score', 'order']
        read_only_fields = ['id']


class PaperQuestionWriteSerializer(serializers.Serializer):
    """
    시험지 문제 추가용 Serializer.
    문제 ID, 배점, 순서 지정.
    """

    question_id = serializers.PrimaryKeyRelatedField(
        queryset=TestQuestionInfo.objects.filter(is_del=False), source='test_question', write_only=True
    )
    score = serializers.IntegerField(default=5, min_value=1)
    order = serializers.IntegerField(default=1, min_value=1)


class TestPaperListSerializer(serializers.ModelSerializer):
    """
    시험지 목록 조회용 경량 Serializer.
    문제 목록 미포함.
    """

    subject = SubjectSerializer(read_only=True)
    create_user_name = serializers.CharField(source='create_user.nick_name', read_only=True)
    tp_degree_display = serializers.CharField(source='get_tp_degree_display', read_only=True)

    class Meta:
        model = TestPaperInfo
        fields = [
            'id',
            'name',
            'subject',
            'tp_degree',
            'tp_degree_display',
            'total_score',
            'passing_score',
            'question_count',
            'create_time',
            'edit_time',
            'create_user_name',
        ]
        read_only_fields = ['id', 'total_score', 'question_count', 'create_time', 'edit_time', 'create_user_name']


class TestPaperDetailSerializer(serializers.ModelSerializer):
    """
    시험지 상세 조회용 Serializer.
    문제 목록 포함.
    """

    subject = SubjectSerializer(read_only=True)
    create_user_name = serializers.CharField(source='create_user.nick_name', read_only=True)
    tp_degree_display = serializers.CharField(source='get_tp_degree_display', read_only=True)
    questions = PaperQuestionReadSerializer(source='testpapertestq_set', many=True, read_only=True)

    class Meta:
        model = TestPaperInfo
        fields = [
            'id',
            'name',
            'subject',
            'tp_degree',
            'tp_degree_display',
            'total_score',
            'passing_score',
            'question_count',
            'create_time',
            'edit_time',
            'create_user_name',
            'questions',
        ]
        read_only_fields = [
            'id',
            'total_score',
            'question_count',
            'create_time',
            'edit_time',
            'create_user_name',
            'questions',
        ]


class TestPaperCreateSerializer(serializers.ModelSerializer):
    """
    시험지 생성용 Serializer.
    문제를 nested로 함께 추가 가능 (선택적).
    """

    subject_id = serializers.PrimaryKeyRelatedField(queryset=SubjectInfo.objects.all(), source='subject', write_only=True)
    questions = PaperQuestionWriteSerializer(many=True, required=False, write_only=True)
    total_score = serializers.IntegerField(read_only=True)
    question_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = TestPaperInfo
        fields = ['id', 'name', 'subject_id', 'tp_degree', 'passing_score', 'questions', 'total_score', 'question_count']
        read_only_fields = ['id', 'total_score', 'question_count']

    def validate(self, attrs):
        """
        passing_score는 total_score 이하여야 함.
        문제가 있는 경우 중복 검증.
        """
        questions = attrs.get('questions', [])

        # 중복 문제 검증
        if questions:
            question_ids = [q['test_question'].id for q in questions]
            if len(question_ids) != len(set(question_ids)):
                raise serializers.ValidationError({'questions': '동일한 문제를 중복하여 추가할 수 없습니다.'})

        # passing_score는 나중에 total_score 계산 후 검증 (create 메서드에서)
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        questions_data = validated_data.pop('questions', [])
        validated_data['create_user'] = self.context['request'].user

        # 시험지 생성
        paper = TestPaperInfo.objects.create(**validated_data)

        # 문제 추가
        total_score = 0
        for question_data in questions_data:
            test_question = question_data.pop('test_question')
            score = question_data.get('score', 5)
            order = question_data.get('order', 1)

            TestPaperTestQ.objects.create(test_paper=paper, test_question=test_question, score=score, order=order)
            total_score += score

        # total_score, question_count 업데이트
        paper.total_score = total_score
        paper.question_count = len(questions_data)
        paper.save()

        # passing_score 검증 (문제가 있는 경우에만)
        if questions_data and paper.passing_score > paper.total_score:
            raise serializers.ValidationError({'passing_score': f'합격점은 총점({paper.total_score}) 이하여야 합니다.'})

        return paper


class TestPaperUpdateSerializer(serializers.ModelSerializer):
    """
    시험지 수정용 Serializer.
    문제는 ID 기반 부분 수정 지원.
    """

    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=SubjectInfo.objects.all(), source='subject', write_only=True, required=False
    )
    questions = PaperQuestionWriteSerializer(many=True, required=False, write_only=True)

    class Meta:
        model = TestPaperInfo
        fields = ['name', 'subject_id', 'tp_degree', 'passing_score', 'questions']

    def validate(self, attrs):
        """
        passing_score 검증 및 중복 문제 검증.
        """
        questions = attrs.get('questions')

        if questions is not None:
            question_ids = [q['test_question'].id for q in questions]
            if len(question_ids) != len(set(question_ids)):
                raise serializers.ValidationError({'questions': '동일한 문제를 중복하여 추가할 수 없습니다.'})

        return attrs

    @transaction.atomic
    def update(self, instance, validated_data):
        questions_data = validated_data.pop('questions', None)

        # Update paper fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update questions if provided
        if questions_data is not None:
            # 기존 문제 전체 삭제 후 재생성
            instance.testpapertestq_set.all().delete()

            # 새 문제 추가
            total_score = 0
            for question_data in questions_data:
                test_question = question_data.pop('test_question')
                score = question_data.get('score', 5)
                order = question_data.get('order', 1)

                TestPaperTestQ.objects.create(test_paper=instance, test_question=test_question, score=score, order=order)
                total_score += score

            # total_score, question_count 업데이트
            instance.total_score = total_score
            instance.question_count = len(questions_data)
        else:
            # 문제 변경 없으면 기존 total_score 재계산
            result = instance.testpapertestq_set.aggregate(total=Sum('score'))
            instance.total_score = result['total'] or 0
            instance.question_count = instance.testpapertestq_set.count()

        instance.save()

        # passing_score 검증 (문제가 있는 경우에만)
        if instance.question_count > 0 and instance.passing_score > instance.total_score:
            raise serializers.ValidationError({'passing_score': f'합격점은 총점({instance.total_score}) 이하여야 합니다.'})

        return instance


class AddQuestionsSerializer(serializers.Serializer):
    """
    시험지에 문제 추가용 Serializer.
    """

    questions = PaperQuestionWriteSerializer(many=True, required=True)

    def validate_questions(self, value):
        """
        중복 문제 검증.
        """
        if not value:
            raise serializers.ValidationError('최소 1개 이상의 문제를 추가해야 합니다.')

        question_ids = [q['test_question'].id for q in value]
        if len(question_ids) != len(set(question_ids)):
            raise serializers.ValidationError('동일한 문제를 중복하여 추가할 수 없습니다.')

        return value
