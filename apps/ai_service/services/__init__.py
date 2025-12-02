"""
AI Service Services
비즈니스 로직 및 AI 서비스

Lazy Import 패턴 사용:
모듈 로딩 에러 방지를 위해 필요 시 직접 import 권장

예시:
    from apps.ai_service.services.session_service import SessionService
    from apps.ai_service.services.conversation_service import ConversationService
"""

# Lazy import를 위해 직접 import는 최소화
# DatabaseFeedbackProvider는 모듈 경로 문제로 주석 처리
# from .feedback_adapter import DatabaseFeedbackProvider

__all__ = [
    # Session Management (Agent Hub)
    'SessionService',
    'get_session_service',
    'create_session_for_user',
    # Conversation Management
    'ConversationService',
    'get_conversation_service',
    'add_user_message',
    'add_assistant_message',
    'get_conversation_history',
    # Usage Tracking
    'UsageService',
    'get_usage_service',
    'check_user_quota',
    'record_usage',
]


def __getattr__(name: str):
    """
    Lazy import 지원

    사용 예시:
        from apps.ai_service.services import SessionService
    """
    if name == 'SessionService':
        from .session_service import SessionService
        return SessionService
    elif name == 'get_session_service':
        from .session_service import get_session_service
        return get_session_service
    elif name == 'create_session_for_user':
        from .session_service import create_session_for_user
        return create_session_for_user
    elif name == 'ConversationService':
        from .conversation_service import ConversationService
        return ConversationService
    elif name == 'get_conversation_service':
        from .conversation_service import get_conversation_service
        return get_conversation_service
    elif name == 'add_user_message':
        from .conversation_service import add_user_message
        return add_user_message
    elif name == 'add_assistant_message':
        from .conversation_service import add_assistant_message
        return add_assistant_message
    elif name == 'get_conversation_history':
        from .conversation_service import get_conversation_history
        return get_conversation_history
    elif name == 'DatabaseFeedbackProvider':
        from .feedback_adapter import DatabaseFeedbackProvider
        return DatabaseFeedbackProvider
    # Usage Tracking
    elif name == 'UsageService':
        from .usage_service import UsageService
        return UsageService
    elif name == 'get_usage_service':
        from .usage_service import get_usage_service
        return get_usage_service
    elif name == 'check_user_quota':
        from .usage_service import check_user_quota
        return check_user_quota
    elif name == 'record_usage':
        from .usage_service import record_usage
        return record_usage

    raise AttributeError(f"module 'apps.ai_service.services' has no attribute '{name}'")
