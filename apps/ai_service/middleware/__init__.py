"""
AI Service Middleware

- auth: JWT 인증 미들웨어
- permissions: 역할 기반 접근 제어 (RBAC)
"""

from .auth import verify_token, get_optional_user, invalidate_user_cache
from .permissions import (
    Role,
    WORKFLOW_PERMISSIONS,
    check_workflow_permission,
    get_allowed_workflows,
    filter_workflows_by_permission,
    require_permission,
    require_role,
    require_workflow_permission,
    PermissionChecker,
    WorkflowPermissionChecker,
)

__all__ = [
    # Auth
    "verify_token",
    "get_optional_user",
    "invalidate_user_cache",
    # Permissions
    "Role",
    "WORKFLOW_PERMISSIONS",
    "check_workflow_permission",
    "get_allowed_workflows",
    "filter_workflows_by_permission",
    "require_permission",
    "require_role",
    "require_workflow_permission",
    "PermissionChecker",
    "WorkflowPermissionChecker",
]
