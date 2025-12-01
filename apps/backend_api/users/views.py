"""
User Views
Django REST Framework ViewSets
"""

from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import SearchHistory
from .serializers import SearchHistorySerializer, SearchHistoryCreateSerializer


class SearchHistoryViewSet(viewsets.ModelViewSet):
    """
    검색 기록 ViewSet

    사용자별 검색 기록 CRUD 작업
    - GET /search-history/ : 검색 기록 목록 조회
    - POST /search-history/ : 검색 기록 생성
    - DELETE /search-history/{id}/ : 검색 기록 삭제
    - DELETE /search-history/clear/ : 전체 검색 기록 삭제
    """

    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SearchHistorySerializer

    def get_queryset(self):
        """현재 사용자의 검색 기록만 조회"""
        return SearchHistory.objects.filter(
            user=self.request.user
        ).order_by('-created_at')[:50]  # 최대 50개

    def get_serializer_class(self):
        """액션에 따른 Serializer 선택"""
        if self.action == 'create':
            return SearchHistoryCreateSerializer
        return SearchHistorySerializer

    def create(self, request, *args, **kwargs):
        """검색 기록 생성"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # 응답은 전체 필드를 반환
        response_serializer = SearchHistorySerializer(instance)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        """검색 기록 삭제"""
        instance = self.get_object()
        # 다른 사용자의 검색 기록은 삭제 불가
        if instance.user != request.user:
            return Response(
                {"error": "권한이 없습니다."},
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['delete'])
    def clear(self, request):
        """전체 검색 기록 삭제"""
        deleted_count, _ = SearchHistory.objects.filter(
            user=request.user
        ).delete()

        return Response(
            {"message": f"{deleted_count}개의 검색 기록이 삭제되었습니다."},
            status=status.HTTP_200_OK
        )
