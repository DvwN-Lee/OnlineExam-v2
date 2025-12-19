"""
Examination API Serializers.
"""
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from examination.models import ExaminationInfo, ExamPaperInfo, ExamStudentsInfo
from testpaper.models import TestPaperInfo
from user.models import StudentsInfo, SubjectInfo


class SubjectSerializer(serializers.ModelSerializer):
    """과목 정보 Serializer (읽기 전용)"""

    class Meta:
        model = SubjectInfo
        fields = ['id', 'subject_name', 'create_time']


class PaperInfoSerializer(serializers.ModelSerializer):
    """시험지 정보 Serializer (읽기 전용)"""

    subject = SubjectSerializer(read_only=True)

    class Meta:
        model = TestPaperInfo
        fields = ['id', 'name', 'subject', 'tp_degree', 'total_score', 'question_count']


class StudentInfoSerializer(serializers.ModelSerializer):
    """학생 정보 Serializer (읽기 전용)"""

    class Meta:
        model = StudentsInfo
        fields = ['id', 'student_name', 'student_id', 'student_class', 'student_school']


class ExamPaperSerializer(serializers.ModelSerializer):
    """시험-시험지 관계 Serializer (읽기 전용)"""

    paper = PaperInfoSerializer(read_only=True)

    class Meta:
        model = ExamPaperInfo
        fields = ['id', 'paper']


class ExamPaperWriteSerializer(serializers.Serializer):
    """시험-시험지 관계 Serializer (쓰기 전용)"""

    paper_id = serializers.PrimaryKeyRelatedField(
        queryset=TestPaperInfo.objects.all(), source='paper', write_only=True
    )


class ExaminationListSerializer(serializers.ModelSerializer):
    """
    시험 목록용 Serializer (경량).
    """

    subject = SubjectSerializer(read_only=True)
    exam_state_display = serializers.CharField(source='get_exam_state_display', read_only=True)
    exam_type_display = serializers.CharField(source='get_exam_type_display', read_only=True)
    create_user_name = serializers.CharField(source='create_user.nick_name', read_only=True)
    duration = serializers.SerializerMethodField()

    class Meta:
        model = ExaminationInfo
        fields = [
            'id',
            'name',
            'subject',
            'start_time',
            'end_time',
            'duration',
            'student_num',
            'actual_num',
            'exam_state',
            'exam_state_display',
            'exam_type',
            'exam_type_display',
            'create_user_name',
            'create_time',
        ]

    def get_duration(self, obj):
        """시험 시간 (분 단위)"""
        duration = obj.end_time - obj.start_time
        return int(duration.total_seconds() / 60)


class ExaminationDetailSerializer(serializers.ModelSerializer):
    """
    시험 상세 조회용 Serializer.
    시험지 및 응시 학생 정보 포함.
    """

    subject = SubjectSerializer(read_only=True)
    exam_state_display = serializers.CharField(source='get_exam_state_display', read_only=True)
    exam_type_display = serializers.CharField(source='get_exam_type_display', read_only=True)
    create_user_name = serializers.CharField(source='create_user.nick_name', read_only=True)
    papers = serializers.SerializerMethodField()
    enrolled_students_count = serializers.SerializerMethodField()
    duration = serializers.SerializerMethodField()

    class Meta:
        model = ExaminationInfo
        fields = [
            'id',
            'name',
            'subject',
            'start_time',
            'end_time',
            'duration',
            'student_num',
            'actual_num',
            'exam_state',
            'exam_state_display',
            'exam_type',
            'exam_type_display',
            'create_user_name',
            'create_time',
            'papers',
            'enrolled_students_count',
        ]

    def get_papers(self, obj):
        """시험에 포함된 시험지 목록"""
        exam_papers = ExamPaperInfo.objects.filter(exam=obj).select_related('paper__subject')
        return ExamPaperSerializer(exam_papers, many=True).data

    def get_enrolled_students_count(self, obj):
        """등록된 학생 수"""
        return ExamStudentsInfo.objects.filter(exam=obj).count()

    def get_duration(self, obj):
        """시험 시간 (분 단위)"""
        duration = obj.end_time - obj.start_time
        return int(duration.total_seconds() / 60)


class ExaminationCreateSerializer(serializers.ModelSerializer):
    """
    시험 생성용 Serializer.
    시험지를 nested로 함께 추가 가능.
    """

    subject_id = serializers.PrimaryKeyRelatedField(queryset=SubjectInfo.objects.all(), source='subject', write_only=True)
    papers = ExamPaperWriteSerializer(many=True, required=False, write_only=True)
    duration = serializers.IntegerField(write_only=True, help_text='시험 시간 (분 단위)')

    class Meta:
        model = ExaminationInfo
        fields = [
            'id',
            'name',
            'subject_id',
            'start_time',
            'duration',
            'exam_type',
            'papers',
            'student_num',
            'exam_state',
        ]
        read_only_fields = ['id', 'student_num', 'exam_state']

    def validate(self, attrs):
        """비즈니스 로직 검증"""
        start_time = attrs.get('start_time')
        duration = attrs.get('duration')

        # 시작 시간 검증
        if start_time and start_time < timezone.now():
            raise serializers.ValidationError({'start_time': '시작 시간은 현재 시간 이후여야 합니다.'})

        # 시험 시간 검증
        if duration and duration <= 0:
            raise serializers.ValidationError({'duration': '시험 시간은 0보다 커야 합니다.'})

        # 시험지 최소 1개 검증
        papers = attrs.get('papers', [])
        if not papers:
            raise serializers.ValidationError({'papers': '최소 1개 이상의 시험지가 필요합니다.'})

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        """시험 생성"""
        papers_data = validated_data.pop('papers', [])
        duration = validated_data.pop('duration')

        # end_time 계산
        start_time = validated_data.get('start_time')
        validated_data['end_time'] = start_time + timezone.timedelta(minutes=duration)
        validated_data['create_user'] = self.context['request'].user
        validated_data['exam_state'] = '0'  # 시험 전
        validated_data['student_num'] = 0
        validated_data['actual_num'] = 0

        exam = ExaminationInfo.objects.create(**validated_data)

        # 시험지 추가
        for paper_data in papers_data:
            paper = paper_data['paper']
            ExamPaperInfo.objects.create(exam=exam, paper=paper)

        return exam


class ExaminationUpdateSerializer(serializers.ModelSerializer):
    """
    시험 수정용 Serializer.
    """

    subject_id = serializers.PrimaryKeyRelatedField(
        queryset=SubjectInfo.objects.all(), source='subject', required=False
    )
    duration = serializers.IntegerField(write_only=True, required=False, help_text='시험 시간 (분 단위)')

    class Meta:
        model = ExaminationInfo
        fields = ['name', 'subject_id', 'start_time', 'duration', 'exam_type']

    def validate(self, attrs):
        """비즈니스 로직 검증"""
        exam = self.instance

        # 시험 시작 후 수정 제한
        if exam.exam_state != '0':
            raise serializers.ValidationError('시험이 시작되었거나 종료된 경우 수정할 수 없습니다.')

        start_time = attrs.get('start_time', exam.start_time)
        duration = attrs.get('duration')

        # 시작 시간 검증
        if start_time < timezone.now():
            raise serializers.ValidationError({'start_time': '시작 시간은 현재 시간 이후여야 합니다.'})

        # 시험 시간 검증
        if duration and duration <= 0:
            raise serializers.ValidationError({'duration': '시험 시간은 0보다 커야 합니다.'})

        return attrs

    def update(self, instance, validated_data):
        """시험 수정"""
        duration = validated_data.pop('duration', None)

        # end_time 재계산
        if duration:
            start_time = validated_data.get('start_time', instance.start_time)
            instance.end_time = start_time + timezone.timedelta(minutes=duration)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class EnrollStudentsSerializer(serializers.Serializer):
    """
    학생 일괄 등록용 Serializer.
    """

    student_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1, help_text='학생 ID 목록'
    )

    def validate_student_ids(self, value):
        """학생 ID 검증"""
        # 중복 제거
        unique_ids = list(set(value))
        if len(unique_ids) != len(value):
            raise serializers.ValidationError('중복된 학생 ID가 있습니다.')

        # 존재하는 학생인지 검증
        existing_students = StudentsInfo.objects.filter(id__in=unique_ids).values_list('id', flat=True)
        if len(existing_students) != len(unique_ids):
            missing_ids = set(unique_ids) - set(existing_students)
            raise serializers.ValidationError(f'존재하지 않는 학생 ID: {missing_ids}')

        return unique_ids


class EnrolledStudentSerializer(serializers.ModelSerializer):
    """
    등록된 학생 정보 Serializer.
    """

    student = StudentInfoSerializer(read_only=True)

    class Meta:
        model = ExamStudentsInfo
        fields = ['id', 'student']


# ==================== 시험 응시 관련 Serializers ====================

from testpaper.models import TestScores, TestPaperTestQ
from testquestion.models import TestQuestionInfo, OptionInfo


class QuestionOptionSerializer(serializers.ModelSerializer):
    """문제 선택지 Serializer"""

    class Meta:
        model = OptionInfo
        fields = ['id', 'option']  # 정답 정보는 제외


class ExamQuestionSerializer(serializers.ModelSerializer):
    """
    시험 문제 Serializer (학생용).
    정답 정보 제외.
    """

    options = QuestionOptionSerializer(many=True, read_only=True, source='optioninfo_set')
    paper_question_id = serializers.IntegerField(source='id', read_only=True)
    assigned_score = serializers.SerializerMethodField()
    tq_type_display = serializers.CharField(source='get_tq_type_display', read_only=True)
    tq_degree_display = serializers.CharField(source='get_tq_degree_display', read_only=True)

    class Meta:
        model = TestQuestionInfo
        fields = [
            'paper_question_id',
            'id',
            'name',
            'tq_type',
            'tq_type_display',
            'tq_degree',
            'tq_degree_display',
            'image',
            'options',
            'assigned_score',
        ]

    def get_assigned_score(self, obj):
        """이 시험지에서의 배점"""
        paper_id = self.context.get('paper_id')
        if paper_id:
            try:
                pq = TestPaperTestQ.objects.get(test_paper_id=paper_id, test_question=obj)
                return pq.score
            except TestPaperTestQ.DoesNotExist:
                return 0
        return 0


class ExamInfoSerializer(serializers.Serializer):
    """
    시험 정보 조회용 Serializer (시험 시작 전).
    """

    exam_id = serializers.IntegerField()
    exam_name = serializers.CharField()
    subject_name = serializers.CharField()
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
    duration = serializers.IntegerField(help_text='시험 시간 (분)')
    total_score = serializers.IntegerField()
    passing_score = serializers.IntegerField()
    question_count = serializers.IntegerField()
    questions = ExamQuestionSerializer(many=True)
    is_started = serializers.BooleanField()
    is_submitted = serializers.BooleanField()


class AnswerItemSerializer(serializers.Serializer):
    """개별 답안 Serializer"""

    question_id = serializers.IntegerField(help_text='문제 ID')
    answer = serializers.CharField(allow_blank=True, required=False, help_text='답안 (객관식: 옵션 ID, 주관식: 텍스트)')


class AnswerSubmissionSerializer(serializers.Serializer):
    """
    답안 제출용 Serializer.
    """

    answers = AnswerItemSerializer(many=True)

    def validate_answers(self, value):
        """답안 검증"""
        if not value:
            raise serializers.ValidationError('최소 1개 이상의 답안이 필요합니다.')
        return value


class ExamStatusSerializer(serializers.Serializer):
    """
    시험 응시 상태 Serializer.
    """

    exam_id = serializers.IntegerField()
    exam_name = serializers.CharField()
    is_started = serializers.BooleanField()
    is_submitted = serializers.BooleanField()
    start_time = serializers.DateTimeField(allow_null=True)
    submit_time = serializers.DateTimeField(allow_null=True)
    time_remaining = serializers.IntegerField(allow_null=True, help_text='남은 시간 (분)')
    draft_answers = serializers.JSONField(allow_null=True)
    score = serializers.IntegerField(allow_null=True)


class SaveDraftSerializer(serializers.Serializer):
    """
    답안 임시 저장용 Serializer.
    """

    answers = serializers.JSONField(help_text='답안 데이터 (JSON)')

    def validate_answers(self, value):
        """답안 형식 검증"""
        if not isinstance(value, dict):
            raise serializers.ValidationError('answers는 객체(object) 형식이어야 합니다.')
        return value
