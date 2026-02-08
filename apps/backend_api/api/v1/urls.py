"""
API v1 URL Configuration

v2 API Migration (Phase 4):
- All AI Service calls now use v2 endpoints internally
- Human-in-the-Loop support for Risk and LLM Compare
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

    # AI Service Proxy (v2 API internally)
    path('ai/chat/rag', ai_proxy.rag_chat, name='ai_rag_chat'),
    path('ai/analyze/case', ai_proxy.analyze_case, name='ai_analyze_case'),
    path('ai/generate/document', ai_proxy.generate_document, name='ai_generate_document'),
    path('ai/health', ai_proxy.health_check, name='ai_health'),

    # Risk Analysis (Human-in-the-Loop)
    path('ai/risk/analyze', ai_proxy.analyze_risk, name='ai_risk_analyze'),
    path('ai/risk/resume', ai_proxy.resume_risk_analysis, name='ai_risk_resume'),
    path('ai/risk/status/<str:session_id>', ai_proxy.risk_status, name='ai_risk_status'),

    # LLM Compare (Human-in-the-Loop)
    path('ai/llm/compare', ai_proxy.llm_compare, name='ai_llm_compare'),
    path('ai/llm/select', ai_proxy.llm_select, name='ai_llm_select'),
    path('ai/llm/status/<str:session_id>', ai_proxy.llm_status, name='ai_llm_status'),

    # Dashboard
    path('dashboard/overview/', dashboard.dashboard_overview, name='dashboard_overview'),
]
