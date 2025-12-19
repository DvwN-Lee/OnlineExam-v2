from django.contrib import admin

from .models import TestQuestionInfo, OptionInfo


# admin-문제정보 등록
@admin.register(TestQuestionInfo)
class TestQuestionInfoAdmin(admin.ModelAdmin):
    # admin 헤더
    list_display = (
        'name',
        'subject',
        'score',
        'tq_type',
        'tq_degree',
        'image',
        'is_del',
        'is_share',
        'create_time',
        'create_user',
        'edit_time',
    )
    # 검색
    search_fields = ('name', 'subject')
    # 페이지
    list_per_page = 20


# admin-옵션 정보 등록
@admin.register(OptionInfo)
class OptionInfoAdmin(admin.ModelAdmin):
    # admin 헤더
    list_display = ('test_question', 'option', 'is_right', 'create_time')
    # 검색
    search_fields = ('test_question',)
    # 페이지
    list_per_page = 20
