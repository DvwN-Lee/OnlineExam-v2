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


# ==================== 성적 관련 Serializers ====================

from testpaper.models import TestScores
from testquestion.models import OptionInfo
from user.models import StudentsInfo


class StudentBasicSerializer(serializers.ModelSerializer):
    """학생 기본 정보 Serializer"""

    class Meta:
        model = StudentsInfo
        fields = ['id', 'student_name', 'student_id', 'student_class']


class MyScoreListSerializer(serializers.ModelSerializer):
    """
    학생용 성적 목록 Serializer.
    """

    exam_name = serializers.CharField(source='exam.name', read_only=True)
    subject_name = serializers.CharField(source='exam.subject.subject_name', read_only=True)
    exam_date = serializers.DateTimeField(source='exam.start_time', read_only=True)
    paper_name = serializers.CharField(source='test_paper.name', read_only=True)
    passed = serializers.SerializerMethodField()

    class Meta:
        model = TestScores
        fields = [
            'id',
            'exam_name',
            'subject_name',
            'exam_date',
            'paper_name',
            'test_score',
            'start_time',
            'submit_time',
            'time_used',
            'passed',
        ]

    def get_passed(self, obj):
        """합격 여부"""
        if obj.test_paper and obj.is_submitted:
            return obj.test_score >= obj.test_paper.passing_score
        return None


class QuestionResultSerializer(serializers.Serializer):
    """문제별 결과 Serializer"""

    question_id = serializers.IntegerField()
    question_name = serializers.CharField()
    question_type = serializers.CharField()
    question_type_display = serializers.CharField()
    user_answer = serializers.CharField(allow_blank=True, allow_null=True)
    correct_answer = serializers.CharField(allow_blank=True, allow_null=True)
    is_correct = serializers.BooleanField(allow_null=True)
    score = serializers.IntegerField()
    max_score = serializers.IntegerField()


class MyScoreDetailSerializer(serializers.ModelSerializer):
    """
    학생용 성적 상세 Serializer.
    문제별 정답/오답 포함.
    """

    exam_name = serializers.CharField(source='exam.name', read_only=True)
    subject_name = serializers.CharField(source='exam.subject.subject_name', read_only=True)
    paper_name = serializers.CharField(source='test_paper.name', read_only=True)
    total_possible = serializers.IntegerField(source='test_paper.total_score', read_only=True)
    passing_score = serializers.IntegerField(source='test_paper.passing_score', read_only=True)
    passed = serializers.SerializerMethodField()
    question_results = serializers.SerializerMethodField()

    class Meta:
        model = TestScores
        fields = [
            'id',
            'exam_name',
            'subject_name',
            'paper_name',
            'test_score',
            'total_possible',
            'passing_score',
            'passed',
            'start_time',
            'submit_time',
            'time_used',
            'question_results',
        ]

    def get_passed(self, obj):
        """합격 여부"""
        if obj.test_paper:
            return obj.test_score >= obj.test_paper.passing_score
        return False

    def get_question_results(self, obj):
        """문제별 결과"""
        if not obj.detail_records:
            return []

        # 시험지의 문제 목록 가져오기
        paper_questions = TestPaperTestQ.objects.filter(test_paper=obj.test_paper).select_related(
            'test_question'
        ).order_by('order')

        results = []
        for pq in paper_questions:
            question = pq.test_question
            question_id_str = str(question.id)
            record = obj.detail_records.get(question_id_str, {})

            # 정답 찾기
            correct_answer = None
            if question.tq_type in ['xz', 'pd']:  # 객관식, OX
                try:
                    correct_option = OptionInfo.objects.get(test_question=question, is_right=True)
                    correct_answer = correct_option.option
                except OptionInfo.DoesNotExist:
                    pass

            results.append({
                'question_id': question.id,
                'question_name': question.name,
                'question_type': question.tq_type,
                'question_type_display': question.get_tq_type_display(),
                'user_answer': record.get('answer', ''),
                'correct_answer': correct_answer,
                'is_correct': record.get('is_correct'),
                'score': record.get('score', 0),
                'max_score': pq.score,
            })

        return results


class ExamScoreListSerializer(serializers.ModelSerializer):
    """
    교사용 시험별 성적 목록 Serializer.
    """

    student = StudentBasicSerializer(source='user', read_only=True)
    passed = serializers.SerializerMethodField()

    class Meta:
        model = TestScores
        fields = [
            'id',
            'student',
            'test_score',
            'start_time',
            'submit_time',
            'time_used',
            'is_submitted',
            'passed',
        ]

    def get_passed(self, obj):
        """합격 여부"""
        if obj.test_paper and obj.is_submitted:
            return obj.test_score >= obj.test_paper.passing_score
        return None


class ExamStatisticsSerializer(serializers.Serializer):
    """시험 성적 통계 Serializer"""

    exam_id = serializers.IntegerField()
    exam_name = serializers.CharField()
    total_students = serializers.IntegerField()
    submitted_count = serializers.IntegerField()
    not_submitted_count = serializers.IntegerField()
    average_score = serializers.FloatField()
    highest_score = serializers.IntegerField()
    lowest_score = serializers.IntegerField()
    pass_count = serializers.IntegerField()
    fail_count = serializers.IntegerField()
    pass_rate = serializers.FloatField()


class ManualGradeSerializer(serializers.Serializer):
    """수동 채점용 Serializer"""

    question_id = serializers.IntegerField()
    score = serializers.IntegerField(min_value=0)
    comment = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        """배점 검증"""
        question_id = attrs['question_id']
        score = attrs['score']

        # TestScores 인스턴스 가져오기
        test_score = self.context.get('test_score')
        if not test_score:
            raise serializers.ValidationError('성적 정보를 찾을 수 없습니다.')

        # 문제의 최대 배점 확인
        try:
            pq = TestPaperTestQ.objects.get(test_paper=test_score.test_paper, test_question_id=question_id)
            if score > pq.score:
                raise serializers.ValidationError({'score': f'배점은 최대 {pq.score}점까지 가능합니다.'})
        except TestPaperTestQ.DoesNotExist:
            raise serializers.ValidationError({'question_id': '시험지에 없는 문제입니다.'})

        return attrs
