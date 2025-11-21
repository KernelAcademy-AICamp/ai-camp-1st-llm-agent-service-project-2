"""
Precedent Admin
"""

from django.contrib import admin
from .models import Precedent, PrecedentFeedback, PrecedentFeedbackStats

@admin.register(Precedent)
class PrecedentAdmin(admin.ModelAdmin):
    """판례 Admin"""

    list_display = [
        'case_number',
        'title_short',
        'court',
        'decision_date',
        'case_type',
        'created_at'
    ]
    list_filter = ['case_type', 'court', 'decision_date']
    search_fields = ['case_number', 'title', 'summary']
    date_hierarchy = 'decision_date'
    ordering = ['-decision_date']

    fieldsets = (
        ('기본 정보', {
            'fields': ('case_number', 'title', 'court', 'decision_date', 'case_type')
        }),
        ('판례 내용', {
            'fields': ('summary', 'full_text', 'judgment_summary')
        }),
        ('참조', {
            'fields': ('reference_statutes', 'reference_precedents', 'citation', 'case_link')
        }),
        ('분류', {
            'fields': ('specialization_tags', 'precedent_id')
        }),
    )

    def title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_short.short_description = '제목'

@admin.register(PrecedentFeedback)
class PrecedentFeedbackAdmin(admin.ModelAdmin):
    """판례 피드백 Admin"""

    list_display = ['user', 'precedent_id', 'feedback_type', 'is_helpful', 'relevance_score', 'created_at']
    list_filter = ['feedback_type', 'is_helpful', 'created_at']
    search_fields = ['user__email', 'precedent_id', 'query']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

@admin.register(PrecedentFeedbackStats)
class PrecedentFeedbackStatsAdmin(admin.ModelAdmin):
    """판례 피드백 통계 Admin (필드명 업데이트)"""

    list_display = [
        'precedent_id',
        'total_likes',  # like_count → total_likes
        'total_dislikes',  # dislike_count → total_dislikes
        'total_feedback_count',  # total_count → total_feedback_count
        'like_ratio',
        'avg_relevance_score',  # 추가
        'should_exclude',
        'last_updated'  # updated_at → last_updated
    ]
    list_filter = ['should_exclude']
    search_fields = ['precedent_id']
    ordering = ['-last_updated']  # updated_at → last_updated
    readonly_fields = ['last_updated']  # created_at 제거, updated_at → last_updated
