"""
Test Paper Management API filters.
"""

import django_filters

from testpaper.models import TestPaperInfo


class TestPaperFilter(django_filters.FilterSet):
    """
    시험지 필터링 FilterSet.
    """

    # 과목 필터
    subject = django_filters.NumberFilter(field_name='subject_id')
    subject_name = django_filters.CharFilter(field_name='subject__subject_name', lookup_expr='icontains')

    # 난이도 필터
    tp_degree = django_filters.ChoiceFilter(choices=TestPaperInfo._meta.get_field('tp_degree').choices)

    # 총점 범위 필터
    score_min = django_filters.NumberFilter(field_name='total_score', lookup_expr='gte')
    score_max = django_filters.NumberFilter(field_name='total_score', lookup_expr='lte')

    # 문항 수 범위 필터
    question_count_min = django_filters.NumberFilter(field_name='question_count', lookup_expr='gte')
    question_count_max = django_filters.NumberFilter(field_name='question_count', lookup_expr='lte')

    # 생성일 범위 필터
    created_after = django_filters.DateTimeFilter(field_name='create_time', lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name='create_time', lookup_expr='lte')

    # 작성자 필터
    create_user = django_filters.NumberFilter(field_name='create_user_id')

    class Meta:
        model = TestPaperInfo
        fields = [
            'subject',
            'subject_name',
            'tp_degree',
            'score_min',
            'score_max',
            'question_count_min',
            'question_count_max',
            'created_after',
            'created_before',
            'create_user',
        ]
