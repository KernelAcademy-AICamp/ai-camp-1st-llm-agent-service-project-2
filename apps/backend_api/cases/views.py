"""
Case Views
사건 및 채팅 히스토리 ViewSet
"""

from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import Case, ChatHistory
from .serializers import CaseSerializer, ChatHistorySerializer


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
