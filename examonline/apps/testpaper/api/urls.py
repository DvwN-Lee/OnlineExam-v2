"""
Test Paper API URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from testpaper.api.views import TestPaperViewSet

router = DefaultRouter()
router.register(r'papers', TestPaperViewSet, basename='paper')

urlpatterns = [
    path('', include(router.urls)),
]
