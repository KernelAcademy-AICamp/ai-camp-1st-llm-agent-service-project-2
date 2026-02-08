"""
JWT Authentication Middleware for Agent Hub

Backend API (Django)의 JWT 토큰을 검증하고 사용자 정보를 추출하는 미들웨어.

설계 문서: docs/AGENT_HUB_BACKEND_INTEGRATION.md Section 3.2
"""

import jwt
import httpx
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from functools import lru_cache

from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from apps.ai_service.config.settings import settings

# HTTPBearer 인스턴스 (자동 토큰 추출)
security = HTTPBearer(auto_error=True)
optional_security = HTTPBearer(auto_error=False)

# ============================================================
# 사용자 정보 캐시 (메모리 기반, 5분 TTL)
# TODO: Redis로 교체 가능
# ============================================================
_user_info_cache: Dict[str, Dict[str, Any]] = {}


def _get_cache(user_id: str) -> Optional[Dict[str, Any]]:
    """캐시에서 사용자 정보 조회"""
    cached = _user_info_cache.get(f"user_info:{user_id}")
    if cached and cached["expires_at"] > datetime.now():
        return cached["data"]
    return None


def _set_cache(user_id: str, user_info: Dict[str, Any], ttl_minutes: int = 5):
    """캐시에 사용자 정보 저장"""
    _user_info_cache[f"user_info:{user_id}"] = {
        "data": user_info,
        "expires_at": datetime.now() + timedelta(minutes=ttl_minutes)
    }


def invalidate_user_cache(user_id: str) -> bool:
    """
    사용자 캐시 무효화

    사용 케이스:
    - 사용자 역할 변경 시
    - 조직 변경 시
    - 로그아웃 시

    Args:
        user_id: 사용자 UUID

    Returns:
        캐시가 존재했으면 True, 없었으면 False
    """
    cache_key = f"user_info:{user_id}"
    if cache_key in _user_info_cache:
        del _user_info_cache[cache_key]
        return True
    return False


def clear_expired_cache():
    """만료된 캐시 항목 정리 (주기적으로 호출 권장)"""
    now = datetime.now()
    expired_keys = [
        key for key, value in _user_info_cache.items()
        if value["expires_at"] <= now
    ]
    for key in expired_keys:
        del _user_info_cache[key]


# ============================================================
# JWT 토큰 검증 함수
# ============================================================


async def verify_token(
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> Dict[str, Any]:
    """
    JWT 토큰 검증 및 사용자 정보 추출

    FastAPI Dependency로 사용:
        @router.post("/chat")
        async def chat(user_info: Dict = Depends(verify_token)):
            ...

    Args:
        credentials: HTTP Bearer 토큰

    Returns:
        사용자 정보 딕셔너리:
        {
            "user_id": "uuid",
            "email": "user@example.com",
            "name": "홍길동",
            "organization_id": "uuid" or None,
            "organization_name": "법무법인 ABC" or None,
            "role": "ADMIN" | "EDITOR" | "VIEWER",
            "permissions": {
                "can_edit": bool,
                "can_admin": bool
            }
        }

    Raises:
        HTTPException 401: 토큰이 유효하지 않은 경우
        HTTPException 503: Backend API 연결 실패
    """
    token = credentials.credentials

    try:
        # 1. JWT 디코딩 (서명 검증)
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        # SimpleJWT는 user_id 필드 사용
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="토큰에 사용자 ID가 없습니다",
                headers={"WWW-Authenticate": "Bearer"}
            )

        # 2. 캐시 확인 (5분 내 조회한 사용자)
        cached_info = _get_cache(str(user_id))
        if cached_info:
            return cached_info

        # 3. Backend API에서 최신 사용자 정보 조회
        # DEBUG 모드에서는 payload를 전달하여 Backend API 호출 없이 테스트 가능
        user_info = await fetch_user_info_from_backend(str(user_id), token, jwt_payload=payload)

        # 4. 캐시 저장 (5분)
        _set_cache(str(user_id), user_info, ttl_minutes=5)

        return user_info

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="토큰이 만료되었습니다. 다시 로그인해주세요.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"유효하지 않은 토큰입니다: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except HTTPException:
        # HTTPException은 그대로 전파
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"인증 처리 중 오류가 발생했습니다: {str(e)}"
        )


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(optional_security)
) -> Optional[Dict[str, Any]]:
    """
    선택적 인증 (토큰이 없어도 요청 허용)

    인증이 선택적인 엔드포인트에서 사용:
        @router.get("/public")
        async def public(user_info: Optional[Dict] = Depends(get_optional_user)):
            if user_info:
                # 로그인된 사용자
            else:
                # 익명 사용자
    """
    if credentials is None:
        return None

    try:
        return await verify_token(credentials)
    except HTTPException:
        return None


# ============================================================
# Backend API 통신
# ============================================================


async def fetch_user_info_from_backend(
    user_id: str,
    token: str,
    jwt_payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Backend API에서 사용자 정보 조회

    Args:
        user_id: 사용자 UUID
        token: JWT 토큰
        jwt_payload: JWT 디코딩 결과 (DEBUG 모드용)

    Returns:
        사용자 정보 딕셔너리

    Raises:
        HTTPException 401: 인증 실패
        HTTPException 503: Backend API 연결 실패
    """
    # DEBUG 모드에서는 JWT payload에서 직접 사용자 정보 추출
    # (Backend API 호출 없이 테스트 가능)
    if settings.DEBUG and jwt_payload:
        role = jwt_payload.get("role", "ADMIN")  # 기본 역할을 ADMIN으로 변경
        return {
            "user_id": str(jwt_payload.get("user_id", user_id)),
            "email": jwt_payload.get("email", ""),
            "name": jwt_payload.get("name", ""),
            "organization_id": jwt_payload.get("organization_id"),
            "organization_name": jwt_payload.get("organization_name"),
            "role": role,
            "permissions": {
                "can_edit": role in ["ADMIN", "EDITOR"],
                "can_admin": role == "ADMIN"
            }
        }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{settings.BACKEND_API_URL}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0  # 5초 타임아웃
            )

            if response.status_code == 401:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Backend API 인증 실패",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail=f"사용자 정보 조회 실패 (status: {response.status_code})"
                )

            user_data = response.json()

            # 사용자 정보 변환 (Backend API 응답 형식 → Agent Hub 형식)
            organization = user_data.get("organization") or {}
            role = user_data.get("role") or organization.get("role") or "ADMIN"  # 기본 역할을 ADMIN으로

            return {
                "user_id": str(user_data["id"]),
                "email": user_data["email"],
                "name": user_data.get("full_name") or user_data.get("name") or "",
                "organization_id": str(organization.get("id")) if organization.get("id") else None,
                "organization_name": organization.get("name"),
                "role": role,
                "permissions": {
                    "can_edit": role in ["ADMIN", "EDITOR"],
                    "can_admin": role == "ADMIN"
                }
            }

        except httpx.TimeoutException:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Backend API 응답 시간 초과"
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Backend API 연결 실패: {str(e)}"
            )
