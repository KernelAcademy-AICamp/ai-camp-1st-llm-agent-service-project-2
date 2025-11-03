"""
API v1 라우터
"""

from fastapi import APIRouter

from app.api.v1.endpoints import upload, documents, ocr

api_router = APIRouter()

# 엔드포인트 등록
api_router.include_router(upload.router, tags=["upload"])
api_router.include_router(documents.router, tags=["documents"])
api_router.include_router(ocr.router, tags=["ocr"])
