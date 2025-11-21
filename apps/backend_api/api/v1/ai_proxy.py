"""
AI Service Proxy
Django → AI Service HTTP 통신
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import httpx
import os
import logging

from cases.models import ChatHistory

logger = logging.getLogger(__name__)

AI_SERVICE_URL = os.getenv('AI_SERVICE_URL', 'http://localhost:8001')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rag_chat(request):
    """
    RAG 챗봇 (AI Service 프록시)

    POST /api/v1/ai/chat/rag
    {
        "query": "음주운전 처벌 기준은?",
        "top_k": 5,
        "include_sources": true,
        "enable_critique": true
    }

    Flow:
    1. Django: JWT 검증 (IsAuthenticated)
    2. AI Service 호출 (내부 HTTP)
    3. Django: ChatHistory 저장
    4. 응답 반환
    """
    try:
        user = request.user
        query = request.data.get('query')

        if not query:
            return Response(
                {"error": "query is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"📨 RAG request from {user.email}: {query[:50]}...")

        # AI Service 호출 (⭐ 수정: Django는 sync, httpx.Client 사용)
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{AI_SERVICE_URL}/v1/chat/rag",
                json=request.data,
                headers={"X-User-ID": str(user.id)}
            )
            response.raise_for_status()
            ai_result = response.json()

        # ChatHistory 저장
        ChatHistory.objects.create(
            user=user,
            query=query,
            answer=ai_result.get('answer', ''),
            sources=ai_result.get('sources', []),
            model=ai_result.get('model', '')
        )

        logger.info(f"✅ RAG response sent to {user.email}")
        return Response(ai_result)

    except httpx.HTTPError as e:
        logger.error(f"❌ AI Service error: {e}")
        return Response(
            {"error": f"AI Service unavailable: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"❌ RAG chat error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_case(request):
    """
    사건 분석 (AI Service 프록시)

    POST /api/v1/ai/analyze/case
    {
        "text": "사건 내용...",
        "include_related_cases": true
    }
    """
    try:
        user = request.user
        text = request.data.get('text')

        if not text:
            return Response(
                {"error": "text is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"📨 Case analysis request from {user.email}")

        # AI Service 호출 (⭐ 수정: Django는 sync, httpx.Client 사용)
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{AI_SERVICE_URL}/v1/analyze/case",
                json=request.data,
                headers={"X-User-ID": str(user.id)}
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"✅ Case analysis response sent to {user.email}")
        return Response(result)

    except httpx.HTTPError as e:
        logger.error(f"❌ AI Service error: {e}")
        return Response(
            {"error": f"AI Service unavailable: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"❌ Case analysis error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_document(request):
    """
    문서 생성 (AI Service 프록시)

    POST /api/v1/ai/generate/document
    {
        "case_info": {...},
        "document_type": "complaint"
    }
    """
    try:
        user = request.user

        logger.info(f"📨 Document generation request from {user.email}")

        # AI Service 호출 (⭐ 수정: Django는 sync, httpx.Client 사용)
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{AI_SERVICE_URL}/v1/analyze/generate",
                json=request.data,
                headers={"X-User-ID": str(user.id)}
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"✅ Document generation response sent to {user.email}")
        return Response(result)

    except httpx.HTTPError as e:
        logger.error(f"❌ AI Service error: {e}")
        return Response(
            {"error": f"AI Service unavailable: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"❌ Document generation error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def health_check(request):
    """AI Service 헬스체크 (동기 버전)"""
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{AI_SERVICE_URL}/health")
            response.raise_for_status()
            return Response({
                "status": "healthy",
                "ai_service": response.json()
            })
    except:
        return Response({
            "status": "degraded",
            "ai_service": "unavailable"
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
