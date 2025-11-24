"""
Case Admin
Django Admin 설정
"""

from django.contrib import admin
from .models import Case, ChatHistory


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    """Case Django Admin"""

    list_display = ['title', 'user', 'status', 'created_at', 'updated_at']
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['title', 'content', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'user', 'title', 'status')
        }),
        ('사건 내용', {
            'fields': ('content',)
        }),
        ('AI 분석 결과', {
            'fields': ('analysis',),
            'classes': ('collapse',)
        }),
        ('메타데이터', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """사용자 정보를 미리 로드"""
        return super().get_queryset(request).select_related('user')


@admin.register(ChatHistory)
class ChatHistoryAdmin(admin.ModelAdmin):
    """ChatHistory Django Admin"""

    list_display = ['user', 'query_preview', 'case', 'model', 'created_at']
    list_filter = ['model', 'created_at']
    search_fields = ['query', 'answer', 'user__email', 'case__title']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'user', 'case', 'model')
        }),
        ('대화 내용', {
            'fields': ('query', 'answer')
        }),
        ('출처 판례', {
            'fields': ('sources',),
            'classes': ('collapse',)
        }),
        ('메타데이터', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """관련 정보를 미리 로드"""
        return super().get_queryset(request).select_related('user', 'case')

    def query_preview(self, obj):
        """질문 미리보기 (30자)"""
        return obj.query[:30] + '...' if len(obj.query) > 30 else obj.query
    query_preview.short_description = '질문'
