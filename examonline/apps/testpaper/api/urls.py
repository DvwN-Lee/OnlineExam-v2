"""
Test Paper API URL configuration.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from testpaper.api.views import TestPaperViewSet
from testpaper.api.scores_views import ScoresViewSet

router = DefaultRouter()
router.register(r'papers', TestPaperViewSet, basename='paper')
router.register(r'scores', ScoresViewSet, basename='score')

urlpatterns = [
    path('', include(router.urls)),
]
