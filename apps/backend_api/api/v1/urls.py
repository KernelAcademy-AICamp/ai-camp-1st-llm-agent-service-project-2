"""
API v1 URL Configuration
"""

from django.urls import path
from . import auth, ai_proxy, dashboard

urlpatterns = [
    # Authentication
    path('auth/signup', auth.signup, name='signup'),
    path('auth/login', auth.login, name='login'),
    path('auth/logout', auth.logout, name='logout'),
    path('auth/me', auth.me, name='me'),
    path('auth/profile', auth.update_profile, name='update_profile'),
    path('auth/change-password', auth.change_password, name='change_password'),

    # AI Service Proxy
    path('ai/chat/rag', ai_proxy.rag_chat, name='ai_rag_chat'),
    path('ai/analyze/case', ai_proxy.analyze_case, name='ai_analyze_case'),
    path('ai/generate/document', ai_proxy.generate_document, name='ai_generate_document'),
    path('ai/health', ai_proxy.health_check, name='ai_health'),

    # Dashboard
    path('dashboard/overview/', dashboard.dashboard_overview, name='dashboard_overview'),
]
