"""
LLM URLs
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LLMModelConfigViewSet, LLMCallLogViewSet, LLMComparisonViewSet

router = DefaultRouter()
router.register(r'models', LLMModelConfigViewSet, basename='llm-models')
router.register(r'logs', LLMCallLogViewSet, basename='llm-logs')
router.register(r'compare', LLMComparisonViewSet, basename='llm-compare')

urlpatterns = [
    path('', include(router.urls)),
]
