"""
Examination API Filters.
"""
import django_filters

from examination.models import ExaminationInfo


class ExaminationFilter(django_filters.FilterSet):
    """
    시험 필터링.
    """

    subject = django_filters.NumberFilter(field_name='subject_id')
    subject_name = django_filters.CharFilter(field_name='subject__subject_name', lookup_expr='icontains')
    exam_state = django_filters.ChoiceFilter(choices=ExaminationInfo._meta.get_field('exam_state').choices)
    exam_type = django_filters.ChoiceFilter(choices=ExaminationInfo._meta.get_field('exam_type').choices)
    create_user = django_filters.NumberFilter(field_name='create_user_id')
    start_after = django_filters.DateTimeFilter(field_name='start_time', lookup_expr='gte')
    start_before = django_filters.DateTimeFilter(field_name='start_time', lookup_expr='lte')
    end_after = django_filters.DateTimeFilter(field_name='end_time', lookup_expr='gte')
    end_before = django_filters.DateTimeFilter(field_name='end_time', lookup_expr='lte')
    student_num_min = django_filters.NumberFilter(field_name='student_num', lookup_expr='gte')
    student_num_max = django_filters.NumberFilter(field_name='student_num', lookup_expr='lte')

    class Meta:
        model = ExaminationInfo
        fields = []
