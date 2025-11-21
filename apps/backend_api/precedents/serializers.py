"""
Precedent Serializers
"""

from rest_framework import serializers
from .models import Precedent, PrecedentFeedback, PrecedentFeedbackStats

class PrecedentSerializer(serializers.ModelSerializer):
    """판례 Serializer"""

    class Meta:
        model = Precedent
        fields = [
            'id',
            'case_number',
            'title',
            'summary',
            'full_text',
            'judgment_summary',
            'reference_statutes',
            'reference_precedents',
            'precedent_id',
            'court',
            'decision_date',
            'case_type',
            'specialization_tags',
            'citation',
            'case_link',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

class PrecedentListSerializer(serializers.ModelSerializer):
    """판례 목록 Serializer (간략)"""

    class Meta:
        model = Precedent
        fields = [
            'id',
            'case_number',
            'title',
            'summary',
            'court',
            'decision_date',
            'case_type',
            'specialization_tags'
        ]

class PrecedentFeedbackSerializer(serializers.ModelSerializer):
    """판례 피드백 Serializer"""

    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = PrecedentFeedback
        fields = [
            'id',
            'user',
            'user_email',
            'precedent_id',
            'query',
            'feedback_type',
            'is_helpful',
            'relevance_score',
            'comment',
            'session_id',
            'created_at'
        ]
        read_only_fields = ['id', 'user', 'created_at']

class PrecedentFeedbackCreateSerializer(serializers.ModelSerializer):
    """판례 피드백 생성 Serializer"""

    class Meta:
        model = PrecedentFeedback
        fields = [
            'precedent_id',
            'query',
            'feedback_type',
            'is_helpful',
            'relevance_score',
            'comment',
            'session_id'
        ]

class PrecedentFeedbackStatsSerializer(serializers.ModelSerializer):
    """판례 피드백 통계 Serializer (필드명 업데이트)"""

    class Meta:
        model = PrecedentFeedbackStats
        fields = [
            'precedent_id',
            'total_likes',  # like_count → total_likes
            'total_dislikes',  # dislike_count → total_dislikes
            'total_feedback_count',  # total_count → total_feedback_count
            'like_ratio',
            'avg_relevance_score',  # 추가
            'should_exclude',
            'exclusion_threshold',  # 추가
            'last_updated'  # updated_at → last_updated
        ]
