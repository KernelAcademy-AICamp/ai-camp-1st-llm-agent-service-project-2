"""
Crawler Views

크롤링 시스템 API Views
"""
import logging
import httpx
from django.conf import settings
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import DataSource, CrawlJob, CrawlLog
from .serializers import (
    DataSourceSerializer, DataSourceListSerializer,
    CrawlJobSerializer, CrawlJobListSerializer,
    CrawlLogSerializer, CrawlLogListSerializer,
    TriggerCrawlSerializer, CrawlJobStatusSerializer
)

logger = logging.getLogger(__name__)


class DataSourceViewSet(viewsets.ModelViewSet):
    """
    DataSource ViewSet

    데이터 소스 CRUD 및 크롤링 트리거 기능 제공
    """
    queryset = DataSource.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['source_type', 'is_active', 'api_key_required']
    search_fields = ['name', 'description', 'base_url']
    ordering_fields = ['name', 'created_at', 'updated_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return DataSourceListSerializer
        return DataSourceSerializer

    @action(detail=True, methods=['post'], url_path='crawl')
    def trigger_crawl(self, request, pk=None):
        """
        크롤링 트리거

        POST /api/v1/data-sources/{id}/crawl/
        """
        data_source = self.get_object()

        # 활성화 여부 확인
        if not data_source.is_active:
            return Response(
                {'error': '비활성화된 데이터 소스입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 요청 데이터 검증
        serializer = TriggerCrawlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # CrawlJob 생성
        crawl_job = CrawlJob.objects.create(
            data_source=data_source,
            schedule_type=serializer.validated_data.get('schedule_type', 'MANUAL'),
            filters=serializer.validated_data.get('filters', {})
        )

        # AI Service 크롤러 호출 (비동기)
        try:
            self._call_ai_service_crawler(data_source, crawl_job, serializer.validated_data)
        except Exception as e:
            logger.error(f"크롤링 서비스 호출 실패: {e}")
            crawl_job.fail(str(e))
            return Response(
                {'error': f'크롤링 서비스 호출 실패: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # 응답
        return Response({
            'job_id': str(crawl_job.id),
            'status': crawl_job.status,
            'status_display': crawl_job.get_status_display(),
            'message': '크롤링 작업이 시작되었습니다.',
            'data_source': {
                'id': str(data_source.id),
                'name': data_source.name,
                'source_type': data_source.source_type
            }
        }, status=status.HTTP_202_ACCEPTED)

    def _call_ai_service_crawler(self, data_source, crawl_job, validated_data):
        """AI Service 크롤러 호출"""
        ai_service_url = getattr(settings, 'AI_SERVICE_URL', 'http://localhost:8001')

        # 소스 타입에 따른 엔드포인트 결정
        endpoint_map = {
            'COURT_API': '/v1/crawler/court-precedents',
            'STATUTE_API': '/v1/crawler/statutes',
            'WEB_CRAWL': '/v1/crawler/web'
        }
        endpoint = endpoint_map.get(data_source.source_type, '/v1/crawler/web')

        # 요청 데이터
        payload = {
            'data_source_id': str(data_source.id),
            'job_id': str(crawl_job.id),
            'base_url': data_source.base_url,
            'config': data_source.config,
            'filters': validated_data.get('filters', {})
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{ai_service_url}{endpoint}",
                    json=payload
                )

                if response.status_code >= 400:
                    logger.error(f"AI Service 에러: {response.text}")
                    raise Exception(f"AI Service 응답 에러: {response.status_code}")

                # 작업 시작 상태 업데이트
                crawl_job.start()
                logger.info(f"크롤링 작업 시작: {crawl_job.id}")

        except httpx.TimeoutException:
            logger.warning("AI Service 타임아웃 - 백그라운드 처리 가정")
            crawl_job.start()
        except httpx.RequestError as e:
            raise Exception(f"AI Service 연결 실패: {str(e)}")


class CrawlJobViewSet(viewsets.ReadOnlyModelViewSet):
    """
    CrawlJob ViewSet

    크롤링 작업 조회 (읽기 전용)
    """
    queryset = CrawlJob.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['data_source', 'status', 'schedule_type']
    search_fields = ['data_source__name']
    ordering_fields = ['created_at', 'started_at', 'finished_at', 'documents_collected']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return CrawlJobListSerializer
        return CrawlJobSerializer

    @action(detail=True, methods=['get'], url_path='status')
    def job_status(self, request, pk=None):
        """
        작업 상태 조회

        GET /api/v1/crawl-jobs/{id}/status/
        """
        crawl_job = self.get_object()
        serializer = CrawlJobStatusSerializer({
            'job_id': crawl_job.id,
            'status': crawl_job.status,
            'status_display': crawl_job.get_status_display(),
            'documents_collected': crawl_job.documents_collected,
            'errors': crawl_job.errors,
            'started_at': crawl_job.started_at,
            'finished_at': crawl_job.finished_at,
            'duration_seconds': crawl_job.duration_seconds
        })
        return Response(serializer.data)

    @action(detail=True, methods=['get'], url_path='logs')
    def logs(self, request, pk=None):
        """
        작업 로그 조회

        GET /api/v1/crawl-jobs/{id}/logs/
        """
        crawl_job = self.get_object()
        logs = crawl_job.crawl_logs.all()

        # 필터링
        status_filter = request.query_params.get('status')
        if status_filter:
            logs = logs.filter(status=status_filter)

        serializer = CrawlLogListSerializer(logs[:100], many=True)
        return Response({
            'count': logs.count(),
            'results': serializer.data
        })

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        """
        작업 취소

        POST /api/v1/crawl-jobs/{id}/cancel/
        """
        crawl_job = self.get_object()

        if crawl_job.status not in ['PENDING', 'RUNNING']:
            return Response(
                {'error': '취소할 수 없는 상태입니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        crawl_job.status = CrawlJob.Status.CANCELLED
        crawl_job.save()

        CrawlLog.log_info(crawl_job, '작업이 사용자에 의해 취소되었습니다.')

        return Response({
            'job_id': str(crawl_job.id),
            'status': crawl_job.status,
            'message': '작업이 취소되었습니다.'
        })


class CrawlLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    CrawlLog ViewSet

    크롤링 로그 조회 (읽기 전용)
    """
    queryset = CrawlLog.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['crawl_job', 'status', 'document']
    search_fields = ['message', 'error_message']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return CrawlLogListSerializer
        return CrawlLogSerializer
