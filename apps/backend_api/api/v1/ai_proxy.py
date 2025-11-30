"""
AI Service Proxy
Django → AI Service HTTP 통신

v2 API Migration (Phase 4):
- RAG: /v1/chat/rag → /v2/rag/chat
- Case Analysis: /v1/analyze/case → /v2/cases/analyze
- Document Generation: /v1/analyze/generate → /v2/documents/analyze/text
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
import httpx
import os
import logging
import uuid

from cases.models import ChatHistory

logger = logging.getLogger(__name__)

AI_SERVICE_URL = os.getenv('AI_SERVICE_URL', 'http://localhost:8001')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rag_chat(request):
    """
    RAG 챗봇 (AI Service 프록시) - v2 API

    POST /api/v1/ai/chat/rag
    {
        "query": "음주운전 처벌 기준은?",
        "top_k": 5,
        "include_sources": true,
        "mode": "standard"  # concise, standard, detailed
    }

    Flow:
    1. Django: JWT 검증 (IsAuthenticated)
    2. AI Service v2 호출 (/v2/rag/chat)
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

        # v2 API 요청 형식으로 변환
        v2_request = {
            "query": query,
            "mode": request.data.get('mode', 'standard'),
            "top_k": request.data.get('top_k', 5),
            "include_sources": request.data.get('include_sources', True),
            "include_critique_log": request.data.get('enable_critique', False),
            "session_id": request.data.get('session_id'),
            "stream": False  # Django는 동기 호출
        }

        # AI Service v2 호출
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{AI_SERVICE_URL}/v2/rag/chat",
                json=v2_request,
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
    사건 분석 (AI Service 프록시) - v2 API

    POST /api/v1/ai/analyze/case
    {
        "text": "사건 내용...",
        "case_type": "criminal",  # criminal, civil, administrative, other
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

        # v2 API 요청 형식으로 변환
        v2_request = {
            "case_content": text,
            "case_type": request.data.get('case_type', 'other'),
            "session_id": request.data.get('session_id') or str(uuid.uuid4())
        }

        # AI Service v2 호출
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{AI_SERVICE_URL}/v2/cases/analyze",
                json=v2_request,
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
    문서 생성 (AI Service 프록시) - v2 API

    POST /api/v1/ai/generate/document
    {
        "case_info": {...},
        "document_type": "complaint",
        "text": "문서 내용..."
    }
    """
    try:
        user = request.user

        logger.info(f"📨 Document generation request from {user.email}")

        # v2 API 요청 형식으로 변환
        text = request.data.get('text', '')
        case_info = request.data.get('case_info', {})

        # case_info가 있으면 텍스트로 변환
        if case_info and not text:
            text = str(case_info)

        v2_request = {
            "text": text,
            "doc_type": request.data.get('document_type', 'OTHER').upper(),
            "document_id": request.data.get('document_id'),
            "session_id": request.data.get('session_id') or str(uuid.uuid4())
        }

        # AI Service v2 호출
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{AI_SERVICE_URL}/v2/documents/analyze/text",
                json=v2_request,
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
@permission_classes([AllowAny])
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


# ===== Human-in-the-Loop Support (Risk Analysis) =====

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def analyze_risk(request):
    """
    리스크 분석 (AI Service 프록시) - v2 API

    POST /api/v1/ai/risk/analyze
    {
        "text": "계약서 내용...",
        "doc_type": "CONTRACT",
        "document_id": "optional-uuid"
    }

    Returns:
        - awaiting_review=True: 전문가 검토 대기 중 (resume 필요)
        - awaiting_review=False: 분석 완료
    """
    try:
        user = request.user
        text = request.data.get('text')

        if not text or len(text) < 50:
            return Response(
                {"error": "text is required (min 50 chars)"},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"📨 Risk analysis request from {user.email}")

        session_id = request.data.get('session_id') or str(uuid.uuid4())

        v2_request = {
            "text": text,
            "doc_type": request.data.get('doc_type', 'CONTRACT'),
            "document_id": request.data.get('document_id'),
            "session_id": session_id
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{AI_SERVICE_URL}/v2/risk/analyze",
                json=v2_request,
                headers={"X-User-ID": str(user.id)}
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"✅ Risk analysis response: awaiting_review={result.get('awaiting_review')}")
        return Response(result)

    except httpx.HTTPError as e:
        logger.error(f"❌ AI Service error: {e}")
        return Response(
            {"error": f"AI Service unavailable: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"❌ Risk analysis error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resume_risk_analysis(request):
    """
    리스크 분석 재개 (Human-in-the-Loop) - v2 API

    POST /api/v1/ai/risk/resume
    {
        "session_id": "uuid",
        "human_review": {
            "approved": true,
            "comments": "검토 의견",
            "modified_risks": [...]  # optional
        }
    }
    """
    try:
        user = request.user
        session_id = request.data.get('session_id')
        human_review = request.data.get('human_review')

        if not session_id or not human_review:
            return Response(
                {"error": "session_id and human_review are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"📨 Risk resume request from {user.email}: session={session_id}")

        v2_request = {
            "session_id": session_id,
            "human_review": human_review
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{AI_SERVICE_URL}/v2/risk/resume",
                json=v2_request,
                headers={"X-User-ID": str(user.id)}
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"✅ Risk resume completed: session={session_id}")
        return Response(result)

    except httpx.HTTPError as e:
        logger.error(f"❌ AI Service error: {e}")
        return Response(
            {"error": f"AI Service unavailable: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"❌ Risk resume error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def risk_status(request, session_id):
    """
    리스크 분석 상태 조회 - v2 API

    GET /api/v1/ai/risk/status/{session_id}
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{AI_SERVICE_URL}/v2/risk/status/{session_id}",
                headers={"X-User-ID": str(request.user.id)}
            )
            response.raise_for_status()
            return Response(response.json())

    except httpx.HTTPError as e:
        logger.error(f"❌ AI Service error: {e}")
        return Response(
            {"error": f"AI Service unavailable: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"❌ Risk status error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# ===== Human-in-the-Loop Support (LLM Compare) =====

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def llm_compare(request):
    """
    LLM 비교 시작 - v2 API

    POST /api/v1/ai/llm/compare
    {
        "task": "summarize",
        "input_data": {"text": "..."},
        "models": [{"model_name": "gpt-4", ...}]
    }

    Returns:
        - awaiting_selection=True: 사용자 선택 대기 중 (select 필요)
        - awaiting_selection=False: 비교 완료
    """
    try:
        user = request.user
        task = request.data.get('task')
        input_data = request.data.get('input_data')
        models = request.data.get('models')

        if not task or not input_data or not models:
            return Response(
                {"error": "task, input_data, and models are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"📨 LLM compare request from {user.email}: task={task}")

        session_id = request.data.get('session_id') or str(uuid.uuid4())

        v2_request = {
            "task": task,
            "input_data": input_data,
            "models": models,
            "session_id": session_id
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{AI_SERVICE_URL}/v2/llm/compare",
                json=v2_request,
                headers={"X-User-ID": str(user.id)}
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"✅ LLM compare response: awaiting_selection={result.get('awaiting_selection')}")
        return Response(result)

    except httpx.HTTPError as e:
        logger.error(f"❌ AI Service error: {e}")
        return Response(
            {"error": f"AI Service unavailable: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"❌ LLM compare error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def llm_select(request):
    """
    LLM 모델 선택 (Human-in-the-Loop) - v2 API

    POST /api/v1/ai/llm/select
    {
        "session_id": "uuid",
        "selected_model": "gpt-4"
    }
    """
    try:
        user = request.user
        session_id = request.data.get('session_id')
        selected_model = request.data.get('selected_model')

        if not session_id or not selected_model:
            return Response(
                {"error": "session_id and selected_model are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.info(f"📨 LLM select request from {user.email}: session={session_id}, model={selected_model}")

        v2_request = {
            "session_id": session_id,
            "selected_model": selected_model
        }

        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{AI_SERVICE_URL}/v2/llm/select",
                json=v2_request,
                headers={"X-User-ID": str(user.id)}
            )
            response.raise_for_status()
            result = response.json()

        logger.info(f"✅ LLM select completed: session={session_id}")
        return Response(result)

    except httpx.HTTPError as e:
        logger.error(f"❌ AI Service error: {e}")
        return Response(
            {"error": f"AI Service unavailable: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"❌ LLM select error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def llm_status(request, session_id):
    """
    LLM 비교 상태 조회 - v2 API

    GET /api/v1/ai/llm/status/{session_id}
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                f"{AI_SERVICE_URL}/v2/llm/status/{session_id}",
                headers={"X-User-ID": str(request.user.id)}
            )
            response.raise_for_status()
            return Response(response.json())

    except httpx.HTTPError as e:
        logger.error(f"❌ AI Service error: {e}")
        return Response(
            {"error": f"AI Service unavailable: {str(e)}"},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    except Exception as e:
        logger.error(f"❌ LLM status error: {e}", exc_info=True)
        return Response(
            {"error": str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
