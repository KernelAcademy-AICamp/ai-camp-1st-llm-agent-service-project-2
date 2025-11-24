"""
Case Serializers
사건 및 채팅 히스토리 Serializer
"""

from rest_framework import serializers
from .models import Case, ChatHistory


class CaseSerializer(serializers.ModelSerializer):
    """Case CRUD Serializer"""

    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Case
        fields = [
            'id',
            'user',
            'user_email',
            'title',
            'content',
            'analysis',
            'status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'user', 'user_email', 'created_at', 'updated_at']

    def validate_title(self, value):
        """제목 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("제목은 필수입니다.")
        if len(value) > 255:
            raise serializers.ValidationError("제목은 255자를 초과할 수 없습니다.")
        return value.strip()

    def validate_content(self, value):
        """내용 검증"""
        if not value or not value.strip():
            raise serializers.ValidationError("내용은 필수입니다.")
        return value.strip()


class ChatHistorySerializer(serializers.ModelSerializer):
    """ChatHistory Read-Only Serializer"""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    case_title = serializers.CharField(source='case.title', read_only=True, allow_null=True)

    class Meta:
        model = ChatHistory
        fields = [
            'id',
            'user',
            'user_email',
            'case',
            'case_title',
            'query',
            'answer',
            'sources',
            'model',
            'created_at'
        ]
        read_only_fields = ['id', 'user', 'user_email', 'case_title', 'created_at']
