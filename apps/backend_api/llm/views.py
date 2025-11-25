"""
LLM Views
LLM 모델 설정 및 비교 API
"""

import uuid
import httpx
import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django.conf import settings

from .models import LLMModelConfig, LLMCallLog, LLMComparisonResult
from .serializers import (
    LLMModelConfigSerializer, LLMModelConfigListSerializer,
    LLMCallLogSerializer, LLMCallLogListSerializer,
    LLMComparisonResultSerializer,
    CompareRequestSerializer, CompareResponseSerializer,
    EvaluateComparisonSerializer
)

logger = logging.getLogger(__name__)

# AI Service URL
AI_SERVICE_URL = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')


class LLMModelConfigViewSet(viewsets.ModelViewSet):
    """
    LLM Model Config ViewSet

    모델 설정 관리 (CRUD)
    """
    queryset = LLMModelConfig.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return LLMModelConfigListSerializer
        return LLMModelConfigSerializer

    def get_queryset(self):
        queryset = LLMModelConfig.objects.all()

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by provider
        provider = self.request.query_params.get('provider')
        if provider:
            queryset = queryset.filter(provider=provider)

        # Filter active only
        active_only = self.request.query_params.get('active_only')
        if active_only and active_only.lower() == 'true':
            queryset = queryset.filter(status='active')

        return queryset

    def get_permissions(self):
        # Only admin can create/update/delete
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminUser()]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active models"""
        queryset = self.get_queryset().filter(status='active')
        serializer = LLMModelConfigListSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def default(self, request):
        """Get the default model"""
        try:
            model = LLMModelConfig.objects.get(is_default=True, status='active')
            serializer = LLMModelConfigSerializer(model)
            return Response(serializer.data)
        except LLMModelConfig.DoesNotExist:
            return Response(
                {"error": "No default model configured"},
                status=status.HTTP_404_NOT_FOUND
            )


class LLMCallLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    LLM Call Log ViewSet

    호출 로그 조회 (읽기 전용)
    """
    queryset = LLMCallLog.objects.all()
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return LLMCallLogListSerializer
        return LLMCallLogSerializer

    def get_queryset(self):
        queryset = LLMCallLog.objects.filter(user=self.request.user)

        # Filter by task type
        task_type = self.request.query_params.get('task_type')
        if task_type:
            queryset = queryset.filter(task_type=task_type)

        # Filter by model
        model_id = self.request.query_params.get('model_id')
        if model_id:
            queryset = queryset.filter(model_config_id=model_id)

        # Filter by status
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        # Filter by comparison session
        session_id = self.request.query_params.get('session_id')
        if session_id:
            queryset = queryset.filter(comparison_session_id=session_id)

        return queryset

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get usage statistics for current user"""
        from django.db.models import Sum, Avg, Count

        queryset = self.get_queryset()

        stats = queryset.aggregate(
            total_calls=Count('id'),
            total_tokens=Sum('total_tokens'),
            total_cost=Sum('estimated_cost'),
            avg_latency=Avg('latency_ms')
        )

        # By task type
        by_task_type = queryset.values('task_type').annotate(
            count=Count('id'),
            total_tokens=Sum('total_tokens'),
            avg_latency=Avg('latency_ms')
        )

        # By model
        by_model = queryset.values('model_config__name').annotate(
            count=Count('id'),
            total_tokens=Sum('total_tokens'),
            avg_latency=Avg('latency_ms')
        )

        return Response({
            'summary': stats,
            'by_task_type': list(by_task_type),
            'by_model': list(by_model)
        })


class LLMComparisonViewSet(viewsets.ModelViewSet):
    """
    LLM Comparison ViewSet

    모델 비교 기능
    """
    queryset = LLMComparisonResult.objects.all()
    serializer_class = LLMComparisonResultSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return LLMComparisonResult.objects.filter(user=self.request.user)

    @action(detail=False, methods=['post'])
    def compare(self, request):
        """
        POST /api/v1/llm/compare/compare/

        여러 LLM 모델의 응답을 비교합니다.
        실제 LLM 호출은 AI Service로 프록시합니다.
        """
        serializer = CompareRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        text = data['text']
        task_type = data['task_type']
        model_ids = data.get('model_ids', [])
        document_id = data.get('document_id')
        options = data.get('options', {})

        # Get models to compare
        if model_ids:
            models = LLMModelConfig.objects.filter(
                id__in=model_ids,
                status='active'
            )
        else:
            models = LLMModelConfig.objects.filter(status='active')

        if not models.exists():
            return Response(
                {"error": "No active models available for comparison"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Generate session ID
        session_id = uuid.uuid4()

        # Call AI Service for comparison
        try:
            compare_request = {
                "text": text,
                "task_type": task_type,
                "models": [
                    {
                        "id": str(m.id),
                        "name": m.name,
                        "provider": m.provider,
                        "model_id": m.model_id,
                        "api_key_env_var": m.api_key_env_var,
                        "base_url": m.base_url,
                        "temperature": m.default_temperature,
                        "max_tokens": m.default_max_tokens,
                        "input_cost_per_1k": float(m.input_cost_per_1k),
                        "output_cost_per_1k": float(m.output_cost_per_1k)
                    }
                    for m in models
                ],
                "session_id": str(session_id),
                "options": options
            }

            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    f"{AI_SERVICE_URL}/v1/llm/compare",
                    json=compare_request,
                    headers={"X-User-ID": str(request.user.id)}
                )
                response.raise_for_status()
                result = response.json()

        except httpx.TimeoutException:
            return Response(
                {"error": "AI Service timeout"},
                status=status.HTTP_504_GATEWAY_TIMEOUT
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"AI Service error: {e}")
            return Response(
                {"error": f"AI Service error: {e.response.text}"},
                status=status.HTTP_502_BAD_GATEWAY
            )
        except Exception as e:
            logger.error(f"Compare error: {e}", exc_info=True)
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Save comparison result
        comparison_result = LLMComparisonResult.objects.create(
            session_id=session_id,
            user=request.user,
            task_type=task_type,
            input_text=text[:5000],  # Truncate if too long
            results=result.get('results', []),
            total_models=len(result.get('results', [])),
            fastest_model=result.get('fastest_model', ''),
            cheapest_model=result.get('cheapest_model', '')
        )

        # Save individual call logs
        for model_result in result.get('results', []):
            try:
                model_config = LLMModelConfig.objects.get(id=model_result['model_id'])
                LLMCallLog.objects.create(
                    user=request.user,
                    model_config=model_config,
                    task_type='compare',
                    prompt_text=text[:5000],
                    prompt_tokens=model_result.get('prompt_tokens', 0),
                    response_text=model_result.get('response_text', '')[:10000],
                    response_tokens=model_result.get('response_tokens', 0),
                    latency_ms=model_result.get('latency_ms', 0),
                    status=model_result.get('status', 'success'),
                    error_message=model_result.get('error_message', ''),
                    comparison_session_id=session_id,
                    document_id=document_id,
                    meta={'options': options}
                )
            except LLMModelConfig.DoesNotExist:
                logger.warning(f"Model config not found: {model_result.get('model_id')}")

        return Response({
            "session_id": str(session_id),
            "task_type": task_type,
            "input_text": text[:500] + "..." if len(text) > 500 else text,
            "results": result.get('results', []),
            "total_models": len(result.get('results', [])),
            "fastest_model": result.get('fastest_model', ''),
            "cheapest_model": result.get('cheapest_model', ''),
            "summary": result.get('summary', {})
        })

    @action(detail=False, methods=['post'])
    def evaluate(self, request):
        """
        POST /api/v1/llm/compare/evaluate/

        비교 결과에 대한 사용자 평가를 저장합니다.
        """
        serializer = EvaluateComparisonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data
        session_id = data['session_id']
        preferred_model_id = data['preferred_model_id']
        evaluation_notes = data.get('evaluation_notes', '')

        try:
            comparison = LLMComparisonResult.objects.get(
                session_id=session_id,
                user=request.user
            )
        except LLMComparisonResult.DoesNotExist:
            return Response(
                {"error": "Comparison session not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        comparison.preferred_model_id = preferred_model_id
        comparison.evaluation_notes = evaluation_notes
        comparison.save()

        return Response({
            "message": "Evaluation saved successfully",
            "session_id": str(session_id),
            "preferred_model_id": str(preferred_model_id)
        })

    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        GET /api/v1/llm/compare/history/

        사용자의 비교 기록을 조회합니다.
        """
        queryset = self.get_queryset().order_by('-created_at')[:50]
        serializer = LLMComparisonResultSerializer(queryset, many=True)
        return Response(serializer.data)
