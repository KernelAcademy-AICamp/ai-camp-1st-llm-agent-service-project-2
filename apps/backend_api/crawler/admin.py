"""
Crawler Admin

크롤링 시스템 Admin 페이지 등록
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.http import HttpResponseRedirect
from django.contrib import messages

from .models import DataSource, CrawlJob, CrawlLog


class CrawlJobInline(admin.TabularInline):
    """CrawlJob Inline - DataSource에서 작업 목록 표시"""
    model = CrawlJob
    extra = 0
    readonly_fields = ['id', 'status', 'schedule_type', 'documents_collected', 'created_at']
    fields = ['status', 'schedule_type', 'documents_collected', 'started_at', 'finished_at']
    ordering = ['-created_at']
    max_num = 10
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class CrawlLogInline(admin.TabularInline):
    """CrawlLog Inline - CrawlJob에서 로그 표시"""
    model = CrawlLog
    extra = 0
    readonly_fields = ['id', 'status', 'message', 'error_message', 'created_at']
    fields = ['status', 'message', 'error_message', 'created_at']
    ordering = ['-created_at']
    max_num = 20
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    """DataSource Admin"""
    list_display = [
        'name', 'source_type_display', 'is_active_display', 'base_url_truncated',
        'total_jobs_display', 'total_documents_display', 'created_at'
    ]
    list_filter = ['source_type', 'is_active', 'api_key_required', 'created_at']
    search_fields = ['name', 'base_url', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'total_jobs_display', 'total_documents_display']
    ordering = ['-created_at']
    inlines = [CrawlJobInline]

    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'name', 'source_type', 'description')
        }),
        ('연결 설정', {
            'fields': ('base_url', 'api_key_required', 'is_active')
        }),
        ('크롤링 설정', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
        ('통계', {
            'fields': ('total_jobs_display', 'total_documents_display'),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def source_type_display(self, obj):
        """소스 유형 표시"""
        return obj.get_source_type_display()
    source_type_display.short_description = '소스 유형'

    def is_active_display(self, obj):
        """활성화 상태 아이콘 표시"""
        if obj.is_active:
            return format_html('<span style="color: green;">✓ 활성</span>')
        return format_html('<span style="color: red;">✗ 비활성</span>')
    is_active_display.short_description = '상태'

    def base_url_truncated(self, obj):
        """URL 요약 표시"""
        url = obj.base_url
        if len(url) > 50:
            return f"{url[:50]}..."
        return url
    base_url_truncated.short_description = 'URL'

    def total_jobs_display(self, obj):
        """총 작업 수 표시"""
        return f"{obj.total_jobs}개"
    total_jobs_display.short_description = '총 작업'

    def total_documents_display(self, obj):
        """수집 문서 수 표시"""
        return f"{obj.total_documents_collected}개"
    total_documents_display.short_description = '수집 문서'


@admin.register(CrawlJob)
class CrawlJobAdmin(admin.ModelAdmin):
    """CrawlJob Admin"""
    list_display = [
        'id_short', 'data_source', 'status_badge', 'schedule_type_display',
        'documents_collected', 'duration_display', 'error_count_display', 'created_at'
    ]
    list_filter = ['status', 'schedule_type', 'data_source', 'created_at']
    search_fields = ['id', 'data_source__name']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'started_at', 'finished_at',
        'duration_display', 'log_count_display', 'error_count_display'
    ]
    ordering = ['-created_at']
    inlines = [CrawlLogInline]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'data_source', 'status', 'schedule_type')
        }),
        ('실행 정보', {
            'fields': ('started_at', 'finished_at', 'duration_display', 'last_run_at', 'next_run_at')
        }),
        ('결과', {
            'fields': ('documents_collected', 'errors', 'log_count_display', 'error_count_display')
        }),
        ('필터 조건', {
            'fields': ('filters',),
            'classes': ('collapse',)
        }),
        ('시간 정보', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def id_short(self, obj):
        """ID 짧게 표시"""
        return str(obj.id)[:8]
    id_short.short_description = 'ID'

    def status_badge(self, obj):
        """상태 배지 표시"""
        colors = {
            'PENDING': '#6c757d',  # gray
            'RUNNING': '#007bff',  # blue
            'COMPLETED': '#28a745',  # green
            'FAILED': '#dc3545',  # red
            'CANCELLED': '#ffc107',  # yellow
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = '상태'

    def schedule_type_display(self, obj):
        """스케줄 유형 표시"""
        return obj.get_schedule_type_display()
    schedule_type_display.short_description = '스케줄'

    def duration_display(self, obj):
        """실행 시간 표시"""
        duration = obj.duration_seconds
        if duration is None:
            return '-'
        if duration < 60:
            return f"{duration:.1f}초"
        elif duration < 3600:
            return f"{duration/60:.1f}분"
        else:
            return f"{duration/3600:.1f}시간"
    duration_display.short_description = '실행 시간'

    def log_count_display(self, obj):
        """로그 개수 표시"""
        return f"{obj.log_count}개"
    log_count_display.short_description = '로그 수'

    def error_count_display(self, obj):
        """에러 개수 표시"""
        count = obj.error_count
        if count > 0:
            return format_html('<span style="color: red;">{}</span>', f"{count}개")
        return '0개'
    error_count_display.short_description = '에러 수'


@admin.register(CrawlLog)
class CrawlLogAdmin(admin.ModelAdmin):
    """CrawlLog Admin"""
    list_display = [
        'id_short', 'crawl_job_link', 'status_badge', 'message_truncated',
        'document_link', 'created_at'
    ]
    list_filter = ['status', 'crawl_job__data_source', 'created_at']
    search_fields = ['message', 'error_message', 'crawl_job__id']
    readonly_fields = ['id', 'created_at']
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('기본 정보', {
            'fields': ('id', 'crawl_job', 'status')
        }),
        ('메시지', {
            'fields': ('message', 'error_message')
        }),
        ('관련 정보', {
            'fields': ('document', 'metadata')
        }),
        ('시간 정보', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def id_short(self, obj):
        """ID 짧게 표시"""
        return str(obj.id)[:8]
    id_short.short_description = 'ID'

    def crawl_job_link(self, obj):
        """CrawlJob 링크"""
        url = reverse('admin:crawler_crawljob_change', args=[obj.crawl_job.id])
        return format_html('<a href="{}">{}</a>', url, str(obj.crawl_job.id)[:8])
    crawl_job_link.short_description = '크롤링 작업'

    def status_badge(self, obj):
        """상태 배지 표시"""
        colors = {
            'INFO': '#17a2b8',  # cyan
            'SUCCESS': '#28a745',  # green
            'WARNING': '#ffc107',  # yellow
            'ERROR': '#dc3545',  # red
        }
        color = colors.get(obj.status, '#6c757d')
        text_color = 'black' if obj.status == 'WARNING' else 'white'
        return format_html(
            '<span style="background-color: {}; color: {}; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, text_color, obj.get_status_display()
        )
    status_badge.short_description = '상태'

    def message_truncated(self, obj):
        """메시지 요약 표시"""
        message = obj.message
        if len(message) > 80:
            return f"{message[:80]}..."
        return message
    message_truncated.short_description = '메시지'

    def document_link(self, obj):
        """관련 문서 링크"""
        if obj.document:
            url = reverse('admin:documents_document_change', args=[obj.document.id])
            return format_html('<a href="{}">{}</a>', url, obj.document.title[:20])
        return '-'
    document_link.short_description = '관련 문서'
