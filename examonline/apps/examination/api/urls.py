"""
Examination API URL configuration.
"""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from examination.api.views import ExaminationViewSet
from examination.api.taking_views import ExamTakingViewSet

router = DefaultRouter()
router.register(r'exams', ExaminationViewSet, basename='exam')
router.register(r'taking', ExamTakingViewSet, basename='taking')

urlpatterns = [
    path('', include(router.urls)),
]
