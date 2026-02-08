"""
Role-Based Access Control (RBAC) for Agent Hub

설계 문서: docs/AGENT_HUB_BACKEND_INTEGRATION.md Section 5.2

역할 정의:
- VIEWER: 읽기 전용, RAG 질의응답만 가능
- EDITOR: 편집, 문서 분석/리스크 평가 가능
- ADMIN: 관리자, 모든 기능 + LLM 비교, Analytics
"""

from typing import List, Dict, Any, Callable, Optional
from functools import wraps
from enum import Enum

from fastapi import HTTPException, status, Depends

from apps.ai_service.middleware.auth import verify_token


# ============================================================
# 역할 정의
# ============================================================

class Role(str, Enum):
    """사용자 역할"""
    VIEWER = "VIEWER"
    EDITOR = "EDITOR"
    ADMIN = "ADMIN"


# 역할 계층 (상위 역할은 하위 역할의 권한 포함)
ROLE_HIERARCHY = {
    Role.ADMIN: [Role.ADMIN, Role.EDITOR, Role.VIEWER],
    Role.EDITOR: [Role.EDITOR, Role.VIEWER],
    Role.VIEWER: [Role.VIEWER],
}


# ============================================================
# 워크플로우별 권한 매핑
# ============================================================

WORKFLOW_PERMISSIONS: Dict[str, Dict[str, Any]] = {
    # RAG 질의응답 - 모든 역할 사용 가능
    "rag_workflow": {
        "required_roles": [Role.VIEWER, Role.EDITOR, Role.ADMIN],
        "description": "법률 질의응답",
        "quota_weight": 1  # 쿼터 가중치 (기본)
    },

    # 문서 분석 - EDITOR 이상
    "document_workflow": {
        "required_roles": [Role.EDITOR, Role.ADMIN],
        "description": "문서 분석",
        "quota_weight": 3
    },

    # 사건 분석 - EDITOR 이상
    "case_workflow": {
        "required_roles": [Role.EDITOR, Role.ADMIN],
        "description": "사건 분석",
        "quota_weight": 3
    },

    # 리스크 평가 - EDITOR 이상
    "risk_workflow": {
        "required_roles": [Role.EDITOR, Role.ADMIN],
        "description": "리스크 평가",
        "quota_weight": 5
    },

    # LLM 비교 분석 - ADMIN만
    "llm_comparison_workflow": {
        "required_roles": [Role.ADMIN],
        "description": "LLM 비교 분석 (고급 기능)",
        "quota_weight": 10
    },

    # 통계 및 분석 - ADMIN만
    "analytics_workflow": {
        "required_roles": [Role.ADMIN],
        "description": "통계 및 분석",
        "quota_weight": 2
    },

    # 크롤러 - ADMIN만
    "crawler_workflow": {
        "required_roles": [Role.ADMIN],
        "description": "크롤러 (외부 데이터 수집)",
        "quota_weight": 8
    },
}


# ============================================================
# 권한 검증 함수
# ============================================================

def check_workflow_permission(workflow_name: str, user_role: str) -> bool:
    """
    워크플로우 실행 권한 확인

    Args:
        workflow_name: 워크플로우 이름
        user_role: 사용자 역할 (ADMIN, EDITOR, VIEWER)

    Returns:
        권한 있으면 True, 없으면 False

    Examples:
        >>> check_workflow_permission("rag_workflow", "VIEWER")
        True
        >>> check_workflow_permission("document_workflow", "VIEWER")
        False
        >>> check_workflow_permission("llm_comparison_workflow", "ADMIN")
        True
    """
    workflow_config = WORKFLOW_PERMISSIONS.get(workflow_name)

    if not workflow_config:
        # 정의되지 않은 워크플로우는 ADMIN만 실행 가능
        return user_role == Role.ADMIN.value

    # 문자열을 Role enum으로 변환
    try:
        role_enum = Role(user_role)
    except ValueError:
        return False

    return role_enum in workflow_config["required_roles"]


def get_workflow_config(workflow_name: str) -> Optional[Dict[str, Any]]:
    """
    워크플로우 설정 조회

    Args:
        workflow_name: 워크플로우 이름

    Returns:
        워크플로우 설정 딕셔너리 또는 None
    """
    return WORKFLOW_PERMISSIONS.get(workflow_name)


def get_quota_weight(workflow_name: str) -> int:
    """
    워크플로우 쿼터 가중치 조회

    Args:
        workflow_name: 워크플로우 이름

    Returns:
        쿼터 가중치 (기본값: 1)
    """
    config = WORKFLOW_PERMISSIONS.get(workflow_name)
    return config.get("quota_weight", 1) if config else 1


def get_allowed_workflows(user_role: str) -> List[str]:
    """
    사용자 역할에 허용된 워크플로우 목록 반환

    Args:
        user_role: 사용자 역할

    Returns:
        허용된 워크플로우 이름 목록

    Examples:
        >>> get_allowed_workflows("VIEWER")
        ['rag_workflow']
        >>> get_allowed_workflows("ADMIN")
        ['rag_workflow', 'document_workflow', ...]
    """
    allowed = []
    for workflow_name in WORKFLOW_PERMISSIONS:
        if check_workflow_permission(workflow_name, user_role):
            allowed.append(workflow_name)
    return allowed


def filter_workflows_by_permission(
    workflows: List[str],
    user_role: str
) -> tuple[List[str], List[Dict[str, Any]]]:
    """
    워크플로우 목록에서 권한 있는 것만 필터링

    Args:
        workflows: 실행하려는 워크플로우 목록
        user_role: 사용자 역할

    Returns:
        (허용된 워크플로우 목록, 거부된 워크플로우 정보 목록)
    """
    allowed = []
    denied = []

    for workflow_name in workflows:
        if check_workflow_permission(workflow_name, user_role):
            allowed.append(workflow_name)
        else:
            config = WORKFLOW_PERMISSIONS.get(workflow_name, {})
            denied.append({
                "workflow": workflow_name,
                "required_roles": [r.value for r in config.get("required_roles", [Role.ADMIN])],
                "user_role": user_role,
                "description": config.get("description", "알 수 없는 워크플로우")
            })

    return allowed, denied


# ============================================================
# FastAPI 데코레이터
# ============================================================

def require_permission(permission: str):
    """
    특정 권한 필요 데코레이터

    Args:
        permission: 필요한 권한 (can_edit, can_admin 등)

    Usage:
        @router.post("/edit")
        @require_permission("can_edit")
        async def edit_document(user_info: Dict = Depends(verify_token)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # user_info는 Depends(verify_token)으로 주입됨
            user_info = kwargs.get("user_info")
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="인증이 필요합니다"
                )

            permissions = user_info.get("permissions", {})
            if not permissions.get(permission, False):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"권한이 없습니다: {permission}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(allowed_roles: List[str]):
    """
    특정 역할 필요 데코레이터

    Args:
        allowed_roles: 허용된 역할 목록

    Usage:
        @router.post("/admin")
        @require_role(["ADMIN"])
        async def admin_only(user_info: Dict = Depends(verify_token)):
            ...

        @router.post("/edit")
        @require_role(["ADMIN", "EDITOR"])
        async def editor_and_above(user_info: Dict = Depends(verify_token)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # user_info는 Depends(verify_token)으로 주입됨
            user_info = kwargs.get("user_info")
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="인증이 필요합니다"
                )

            user_role = user_info.get("role", "VIEWER")
            if user_role not in allowed_roles:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"이 기능은 {', '.join(allowed_roles)} 역할만 사용할 수 있습니다. 현재 역할: {user_role}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_workflow_permission(workflow_name: str):
    """
    특정 워크플로우 실행 권한 필요 데코레이터

    Args:
        workflow_name: 워크플로우 이름

    Usage:
        @router.post("/analyze-document")
        @require_workflow_permission("document_workflow")
        async def analyze_document(user_info: Dict = Depends(verify_token)):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            user_info = kwargs.get("user_info")
            if not user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="인증이 필요합니다"
                )

            user_role = user_info.get("role", "VIEWER")
            if not check_workflow_permission(workflow_name, user_role):
                config = WORKFLOW_PERMISSIONS.get(workflow_name, {})
                required_roles = [r.value for r in config.get("required_roles", [Role.ADMIN])]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"{workflow_name}은(는) {', '.join(required_roles)} 역할만 실행할 수 있습니다. 현재 역할: {user_role}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================
# FastAPI Dependency 방식 (대안)
# ============================================================

class PermissionChecker:
    """
    FastAPI Dependency 방식의 권한 검사

    Usage:
        @router.post("/admin")
        async def admin_only(
            user_info: Dict = Depends(verify_token),
            _: None = Depends(PermissionChecker(["ADMIN"]))
        ):
            ...
    """

    def __init__(self, allowed_roles: List[str]):
        self.allowed_roles = allowed_roles

    async def __call__(self, user_info: Dict[str, Any] = Depends(verify_token)):
        user_role = user_info.get("role", "VIEWER")
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"이 기능은 {', '.join(self.allowed_roles)} 역할만 사용할 수 있습니다"
            )
        return None


class WorkflowPermissionChecker:
    """
    워크플로우 권한 검사 Dependency

    Usage:
        @router.post("/analyze")
        async def analyze(
            user_info: Dict = Depends(verify_token),
            _: None = Depends(WorkflowPermissionChecker("document_workflow"))
        ):
            ...
    """

    def __init__(self, workflow_name: str):
        self.workflow_name = workflow_name

    async def __call__(self, user_info: Dict[str, Any] = Depends(verify_token)):
        user_role = user_info.get("role", "VIEWER")
        if not check_workflow_permission(self.workflow_name, user_role):
            config = WORKFLOW_PERMISSIONS.get(self.workflow_name, {})
            required_roles = [r.value for r in config.get("required_roles", [Role.ADMIN])]
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"{self.workflow_name}은(는) {', '.join(required_roles)} 역할만 실행할 수 있습니다"
            )
        return None
