from django.db import models
from django.utils import timezone

from testquestion.models import TestQuestionInfo
from user.models import UserProfile, StudentsInfo, SubjectInfo


# 시험지 정보
class TestPaperInfo(models.Model):
    name = models.CharField(max_length=50, default='', verbose_name='시험지 이름')
    subject = models.ForeignKey(SubjectInfo, on_delete=models.PROTECT, verbose_name='시험지 과목', default='')
    tp_degree = models.CharField(
        choices=(('jd', '쉬움'), ('zd', '중간'), ('kn', '어려움')), max_length=2, verbose_name='시험지 난이도', default='jd'
    )
    total_score = models.IntegerField(default=100, verbose_name='총점')
    passing_score = models.IntegerField(default=60, verbose_name='합격점')
    question_count = models.IntegerField(default=0, verbose_name='총 문항 수')
    create_user = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, verbose_name='작성자')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='생성 시간')
    edit_time = models.DateTimeField(auto_now=True, verbose_name='수정 시간')

    class Meta:
        verbose_name = '시험지 정보'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


# 시험지-문제 매핑 (M:N Through Model)
class TestPaperTestQ(models.Model):
    test_paper = models.ForeignKey(TestPaperInfo, on_delete=models.CASCADE, verbose_name='시험지')
    test_question = models.ForeignKey(TestQuestionInfo, on_delete=models.CASCADE, verbose_name='시험 문제')
    score = models.IntegerField(default=5, verbose_name='문제 배점')
    order = models.PositiveIntegerField(default=1, verbose_name='문제 순서')

    class Meta:
        verbose_name = '시험지 문제 정보'
        verbose_name_plural = verbose_name
        ordering = ['order']
        unique_together = ('test_paper', 'test_question')
        indexes = [
            models.Index(fields=['test_paper', 'order']),
        ]


# 학생 성적 정보
class TestScores(models.Model):
    user = models.ForeignKey(StudentsInfo, on_delete=models.CASCADE, verbose_name='학생 정보')
    test_paper = models.ForeignKey(TestPaperInfo, on_delete=models.SET_NULL, null=True, verbose_name='시험지 정보')
    test_score = models.IntegerField(default=0, verbose_name='시험 성적')
    detail_records = models.JSONField(default=dict, verbose_name='상세 답안 기록', blank=True)
    create_time = models.DateTimeField(default=timezone.now, verbose_name='생성 시간')

    # 시험 응시 관련 필드
    exam = models.ForeignKey('examination.ExaminationInfo', on_delete=models.SET_NULL, null=True, blank=True, verbose_name='시험 정보')
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='시험 시작 시간')
    submit_time = models.DateTimeField(null=True, blank=True, verbose_name='제출 시간')
    is_submitted = models.BooleanField(default=False, verbose_name='제출 여부')
    time_used = models.IntegerField(default=0, verbose_name='소요 시간(분)')

    class Meta:
        verbose_name = '학생 성적 정보'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['user', 'test_paper']),
            models.Index(fields=['exam', 'user']),
        ]

    def __str__(self):
        return self.user.student_name
