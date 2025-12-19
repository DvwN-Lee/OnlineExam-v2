from django.db import models
from django.utils import timezone

from user.models import UserProfile, SubjectInfo


# 시험 문제 정보
class TestQuestionInfo(models.Model):
    name = models.CharField(max_length=500, default='', verbose_name='시험 문제 제목')
    subject = models.ForeignKey(SubjectInfo, on_delete=models.PROTECT, verbose_name='소속 과목', default='')
    score = models.IntegerField(default=0, verbose_name='점수')
    tq_type = models.CharField(
        choices=(('xz', '객관식'), ('pd', '주관식'), ('tk', '빈칸 채우기')), max_length=2, verbose_name='시험 문제 유형', default='xz'
    )
    tq_degree = models.CharField(
        choices=(('jd', '쉬움'), ('zd', '보통'), ('kn', '어려움')), max_length=2, verbose_name='시험 난이도', default='jd'
    )
    image = models.ImageField(upload_to='test_question/%Y/%m', max_length=200, verbose_name='시험 문제 사진', blank=True, null=True)
    is_del = models.BooleanField(default=False, verbose_name='삭제 여부')
    is_share = models.BooleanField(default=False, verbose_name='공유 여부')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='생성 시간')
    create_user = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, verbose_name='출제자')
    edit_time = models.DateTimeField(auto_now=True, verbose_name='수정 시간')

    class Meta:
        verbose_name = '시험 문제 정보'
        verbose_name_plural = verbose_name
        indexes = [
            models.Index(fields=['subject', 'tq_type', 'tq_degree']),
            models.Index(fields=['is_del', 'is_share']),
        ]

    def __str__(self):
        return self.name


# 시험 문제 선택표
class OptionInfo(models.Model):
    test_question = models.ForeignKey(TestQuestionInfo, on_delete=models.CASCADE, verbose_name='시험 문제 정보')
    option = models.CharField(max_length=100, default='', verbose_name='옵션')
    is_right = models.BooleanField(default=True, verbose_name='정답 여부')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='생성 시간')

    class Meta:
        verbose_name = '문제 선택 정보'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.test_question.name
