"""
Cases URL Configuration
"""

from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'cases', views.CaseViewSet, basename='case')
router.register(r'chat-history', views.ChatHistoryViewSet, basename='chathistory')

urlpatterns = router.urls
