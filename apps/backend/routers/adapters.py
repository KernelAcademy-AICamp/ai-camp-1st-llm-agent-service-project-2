"""
Adapters Router
QDoRA Adapter 관리 엔드포인트
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/adapter", tags=["adapters"])


class AdapterLoadRequest(BaseModel):
    adapter_name: str


class AdapterInfoResponse(BaseModel):
    current_adapter: Optional[str]
    is_adapter_loaded: bool
    available_adapters: List[str]
    metrics: Dict[str, Any]


def setup_adapter_routes(constitutional_chatbot):
    """Adapter 관리 라우트 설정"""

    @router.post("/load")
    async def load_adapter(request: AdapterLoadRequest):
        """QDoRA Adapter 로드"""
        if not constitutional_chatbot:
            raise HTTPException(status_code=503, detail="Chatbot not available")

        # AdapterChatbot 타입 체크
        if not hasattr(constitutional_chatbot, 'load_adapter'):
            raise HTTPException(status_code=400, detail="Adapter feature not supported")

        try:
            success = constitutional_chatbot.load_adapter(request.adapter_name)

            if success:
                return {
                    "success": True,
                    "message": f"Adapter '{request.adapter_name}' loaded successfully",
                    "current_adapter": request.adapter_name
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to load adapter '{request.adapter_name}'. Check if it exists in Ollama.",
                    "current_adapter": None
                }

        except Exception as e:
            logger.error(f"Adapter load error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/unload")
    async def unload_adapter():
        """Adapter 언로드 (Base Model로 복귀)"""
        if not constitutional_chatbot:
            raise HTTPException(status_code=503, detail="Chatbot not available")

        if not hasattr(constitutional_chatbot, 'unload_adapter'):
            raise HTTPException(status_code=400, detail="Adapter feature not supported")

        try:
            constitutional_chatbot.unload_adapter()

            return {
                "success": True,
                "message": "Adapter unloaded, returned to base model",
                "current_adapter": None
            }

        except Exception as e:
            logger.error(f"Adapter unload error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/list")
    async def list_adapters():
        """사용 가능한 Adapter 목록 조회"""
        if not constitutional_chatbot:
            raise HTTPException(status_code=503, detail="Chatbot not available")

        if not hasattr(constitutional_chatbot, 'list_available_adapters'):
            return []

        try:
            adapters = constitutional_chatbot.list_available_adapters()
            return adapters

        except Exception as e:
            logger.error(f"List adapters error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/info", response_model=AdapterInfoResponse)
    async def get_adapter_info():
        """현재 Adapter 정보 및 메트릭 조회"""
        if not constitutional_chatbot:
            raise HTTPException(status_code=503, detail="Chatbot not available")

        if not hasattr(constitutional_chatbot, 'get_adapter_info'):
            return AdapterInfoResponse(
                current_adapter=None,
                is_adapter_loaded=False,
                available_adapters=[],
                metrics={}
            )

        try:
            info = constitutional_chatbot.get_adapter_info()
            return AdapterInfoResponse(**info)

        except Exception as e:
            logger.error(f"Get adapter info error: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return router
