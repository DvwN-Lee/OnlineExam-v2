"""
Question API URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from testquestion.api.views import QuestionViewSet

router = DefaultRouter()
router.register(r'questions', QuestionViewSet, basename='question')

urlpatterns = [
    path('', include(router.urls)),
]
