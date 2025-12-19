"""
Question Management API filters.
"""

import django_filters

from testquestion.models import TestQuestionInfo


class QuestionFilter(django_filters.FilterSet):
    """
    문제 필터링 FilterSet.
    """

    # 과목 필터
    subject = django_filters.NumberFilter(field_name='subject_id')
    subject_name = django_filters.CharFilter(field_name='subject__subject_name', lookup_expr='icontains')

    # 문제 유형 필터
    tq_type = django_filters.ChoiceFilter(choices=TestQuestionInfo._meta.get_field('tq_type').choices)

    # 난이도 필터
    tq_degree = django_filters.ChoiceFilter(choices=TestQuestionInfo._meta.get_field('tq_degree').choices)

    # 점수 범위 필터
    score_min = django_filters.NumberFilter(field_name='score', lookup_expr='gte')
    score_max = django_filters.NumberFilter(field_name='score', lookup_expr='lte')

    # 공유 여부 필터
    is_share = django_filters.BooleanFilter()

    # 생성일 범위 필터
    created_after = django_filters.DateTimeFilter(field_name='create_time', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='create_time', lookup_expr='lte')

    # 출제자 필터
    create_user = django_filters.NumberFilter(field_name='create_user_id')

    class Meta:
        model = TestQuestionInfo
        fields = [
            'subject',
            'subject_name',
            'tq_type',
            'tq_degree',
            'score_min',
            'score_max',
            'is_share',
            'created_after',
            'created_before',
            'create_user',
        ]
