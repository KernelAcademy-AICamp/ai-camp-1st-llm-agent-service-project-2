"""
Case Views
사건 및 채팅 히스토리 ViewSet
"""

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
import httpx
import os
import logging

from .models import Case, ChatHistory
from .serializers import CaseSerializer, ChatHistorySerializer

logger = logging.getLogger(__name__)
AI_SERVICE_URL = os.getenv('AI_SERVICE_URL', 'http://localhost:8001')


class CaseViewSet(viewsets.ModelViewSet):
    """
    Case CRUD API

    사용자는 자신의 Case만 조회/수정/삭제 가능
    """
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """현재 사용자의 Case만 반환"""
        return Case.objects.filter(user=self.request.user).select_related('user')

    def perform_create(self, serializer):
        """Case 생성 시 현재 사용자 자동 설정"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def chat_histories(self, request, pk=None):
        """
        특정 Case의 채팅 히스토리 조회

        GET /api/v1/cases/{uuid}/chat_histories/
        """
        case = self.get_object()
        histories = ChatHistory.objects.filter(case=case).order_by('-created_at')
        serializer = ChatHistorySerializer(histories, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def update_status(self, request, pk=None):
        """
        Case 상태 업데이트

        PATCH /api/v1/cases/{uuid}/update_status/
        Body: {"status": "analyzed"}
        """
        case = self.get_object()
        new_status = request.data.get('status')

        if not new_status:
            return Response(
                {'error': 'status 필드가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        valid_statuses = [choice[0] for choice in Case.STATUS_CHOICES]
        if new_status not in valid_statuses:
            return Response(
                {'error': f'유효하지 않은 상태입니다. 가능한 값: {valid_statuses}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        case.status = new_status
        case.save()

        serializer = self.get_serializer(case)
        return Response(serializer.data)

    @action(detail=True, methods=['patch'])
    def update_analysis(self, request, pk=None):
        """
        AI 분석 결과 업데이트

        PATCH /api/v1/cases/{uuid}/update_analysis/
        Body: {"analysis": {...}}
        """
        case = self.get_object()
        analysis = request.data.get('analysis')

        if analysis is None:
            return Response(
                {'error': 'analysis 필드가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        case.analysis = analysis
        case.status = 'analyzed'  # 분석 완료로 상태 변경
        case.save()

        serializer = self.get_serializer(case)
        return Response(serializer.data)

    @action(detail=False, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload(self, request):
        """
        파일 업로드 및 Case 생성

        POST /api/v1/cases/upload/
        Form Data:
            - files: 업로드할 파일들 (multiple)
        """
        files = request.FILES.getlist('files')

        if not files:
            return Response(
                {'error': '업로드할 파일이 없습니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 파일 내용 읽기
        file_contents = []
        uploaded_files = []

        for file in files:
            try:
                content = file.read().decode('utf-8')
                file_contents.append(f"[{file.name}]\n{content}")
                uploaded_files.append({
                    'filename': file.name,
                    'size': file.size
                })
            except Exception as e:
                file_contents.append(f"[{file.name}]\n파일을 읽을 수 없습니다: {str(e)}")
                uploaded_files.append({
                    'filename': file.name,
                    'size': 0
                })

        full_content = "\n\n".join(file_contents)

        # Case 생성 (분석 전)
        case = Case.objects.create(
            user=request.user,
            title=f"사건 - {files[0].name}",
            content=full_content,
            status='analyzing'  # 분석 중 상태
        )

        logger.info(f"📁 Case created: {case.id}, starting AI analysis...")

        # AI 분석 호출
        try:
            with httpx.Client(timeout=300.0) as client:  # 5분 타임아웃
                ai_response = client.post(
                    f"{AI_SERVICE_URL}/v1/analyze/case",
                    json={
                        "text": full_content,
                        "include_related_cases": True
                    },
                    headers={"X-User-ID": str(request.user.id)}
                )
                ai_response.raise_for_status()
                ai_result = ai_response.json()

            logger.info(f"✅ AI analysis completed for case {case.id}")

            # AI 분석 결과를 Case에 저장
            case.analysis = ai_result
            case.status = 'analyzed'
            case.title = ai_result.get('suggested_case_name', case.title)
            case.save()

            # 프론트엔드가 기대하는 형식으로 응답 반환
            response_data = {
                'case_id': str(case.id),
                'summary': ai_result.get('summary', f'{len(files)}개 파일 업로드됨'),
                'document_types': ai_result.get('document_types', []),
                'issues': ai_result.get('issues', []),
                'key_dates': ai_result.get('key_dates', {}),
                'parties': ai_result.get('parties', {}),
                'related_cases': ai_result.get('related_cases', []),
                'suggested_case_name': ai_result.get('suggested_case_name', case.title),
                'suggested_next_steps': ai_result.get('suggested_next_steps', []),
                'uploaded_files': uploaded_files,
                'scenario': ai_result.get('scenario')
            }

        except httpx.HTTPError as e:
            logger.error(f"❌ AI Service error for case {case.id}: {e}")
            # AI 분석 실패 시 기본 응답
            case.status = 'draft'
            case.save()

            response_data = {
                'case_id': str(case.id),
                'summary': f'{len(files)}개 파일 업로드됨 (AI 분석 실패)',
                'document_types': [],
                'issues': [],
                'key_dates': {},
                'parties': {},
                'related_cases': [],
                'suggested_case_name': case.title,
                'suggested_next_steps': [],
                'uploaded_files': uploaded_files,
                'scenario': None
            }

        except Exception as e:
            logger.error(f"❌ Unexpected error for case {case.id}: {e}", exc_info=True)
            case.status = 'draft'
            case.save()

            response_data = {
                'case_id': str(case.id),
                'summary': f'{len(files)}개 파일 업로드됨 (처리 중 오류 발생)',
                'document_types': [],
                'issues': [],
                'key_dates': {},
                'parties': {},
                'related_cases': [],
                'suggested_case_name': case.title,
                'suggested_next_steps': [],
                'uploaded_files': uploaded_files,
                'scenario': None
            }

        return Response(response_data, status=status.HTTP_201_CREATED)


class ChatHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ChatHistory Read-Only API

    채팅 히스토리는 AI Proxy에서 자동 생성되므로
    사용자는 조회만 가능
    """
    serializer_class = ChatHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """현재 사용자의 ChatHistory만 반환"""
        return ChatHistory.objects.filter(user=self.request.user).select_related('user', 'case')
