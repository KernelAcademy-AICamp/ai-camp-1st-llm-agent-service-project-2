"""
User URLs
Django REST Framework Router
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SearchHistoryViewSet

router = DefaultRouter()
router.register(r'search-history', SearchHistoryViewSet, basename='search-history')

urlpatterns = [
    path('', include(router.urls)),
]
