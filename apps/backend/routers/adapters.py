"""
Adapters Router - AI Service Proxy
Constitutional AI 어댑터 API
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import httpx
import os
import logging

from apps.backend.core.auth.dependencies import get_current_user
from apps.backend.models.user import User

logger = logging.getLogger(__name__)

AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")

# ===== Request/Response Models =====

class AdapterRequest(BaseModel):
    """어댑터 요청"""
    query: str
    top_k: int = 5

class AdapterResponse(BaseModel):
    """어댑터 응답"""
    answer: str
    sources: list
    critique_log: Optional[list] = None

# ===== Router Setup =====

def setup_adapter_routes(**kwargs) -> APIRouter:
    """Adapter 라우터 설정"""
    router = APIRouter(prefix="/api/v1/adapters", tags=["adapters"])

    @router.post("/chat", response_model=AdapterResponse)
    async def adapter_chat(
        request: AdapterRequest,
        current_user: User = Depends(get_current_user)
    ):
        """Constitutional AI 어댑터 채팅 (프록시)"""
        try:
            # AI Service의 /v1/chat/rag 호출 (Constitutional AI 포함)
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{AI_SERVICE_URL}/v1/chat/rag",
                    json={
                        "query": request.query,
                        "top_k": request.top_k,
                        "include_sources": True,
                        "enable_critique": True  # Constitutional AI 활성화
                    },
                    headers={"X-User-ID": str(current_user.id)}
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            raise HTTPException(
                status_code=503,
                detail=f"AI Service unavailable: {str(e)}"
            )

    return router
