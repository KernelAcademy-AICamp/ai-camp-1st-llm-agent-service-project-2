"""
Chat Router - AI Service Proxy
RAG 챗봇 API를 AI Service로 프록시
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import os
import logging

from apps.backend.core.auth.dependencies import get_current_user
from apps.backend.models.user import User
# from apps.backend.models.chat_history import ChatHistory  # 필요시
from apps.backend.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# AI Service URL
AI_SERVICE_URL = os.getenv("AI_SERVICE_URL", "http://localhost:8001")

# ===== Request/Response Models =====

class ChatRequest(BaseModel):
    """채팅 요청"""
    query: str
    top_k: int = 5
    include_sources: bool = True
    enable_critique: bool = True

class ChatResponse(BaseModel):
    """채팅 응답"""
    answer: str
    sources: List[Dict[str, Any]]
    query: str
    model: str
    timestamp: str
    critique_log: Optional[List[Dict[str, Any]]] = None

# ===== Router Setup =====

def setup_chat_routes(**kwargs) -> APIRouter:
    """
    Chat 라우터 설정 (하위 호환성)

    기존 setup_chat_routes(chatbot, llm_client, ...) 시그니처 유지
    하지만 실제로는 사용하지 않고 AI Service로 프록시
    """
    router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

    @router.post("/rag", response_model=ChatResponse)
    async def chat_rag(
        request: ChatRequest,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        """
        RAG 채팅 (AI Service 프록시)

        Flow:
        1. Django Backend: JWT 검증 (get_current_user)
        2. AI Service 호출 (내부 HTTP)
        3. Django Backend: ChatHistory 저장 (선택)
        4. 응답 반환
        """
        try:
            logger.info(f"📨 RAG request from user {current_user.id}: {request.query[:50]}...")

            # AI Service 호출
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{AI_SERVICE_URL}/v1/chat/rag",
                    json=request.dict(),
                    headers={"X-User-ID": str(current_user.id)}
                )
                response.raise_for_status()
                ai_result = response.json()

            # ChatHistory 저장 (선택)
            # chat_history = ChatHistory(
            #     user_id=current_user.id,
            #     query=request.query,
            #     answer=ai_result['answer'],
            #     sources=ai_result['sources'],
            #     model=ai_result['model']
            # )
            # db.add(chat_history)
            # await db.commit()

            logger.info(f"✅ RAG response sent to user {current_user.id}")
            return ChatResponse(**ai_result)

        except httpx.HTTPError as e:
            logger.error(f"❌ AI Service error: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"AI Service unavailable: {str(e)}"
            )
        except Exception as e:
            logger.error(f"❌ Chat error: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail=f"Internal server error: {str(e)}"
            )

    @router.get("/health")
    async def chat_health():
        """Chat 프록시 헬스체크"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{AI_SERVICE_URL}/v1/chat/health")
                response.raise_for_status()
                return {"status": "healthy", "ai_service": response.json()}
        except:
            return {"status": "degraded", "ai_service": "unavailable"}

    return router
