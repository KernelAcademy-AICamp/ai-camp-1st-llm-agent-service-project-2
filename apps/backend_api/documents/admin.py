from django.contrib import admin
from .models import Document, DocumentChunk, Summary, KeyClause, RiskAnalysisResult, CaseAnalysis


class DocumentChunkInline(admin.TabularInline):
    """Inline admin for DocumentChunk"""
    model = DocumentChunk
    extra = 0
    readonly_fields = ('id', 'chunk_index', 'is_embedded', 'created_at')
    fields = ('chunk_index', 'text', 'embedding_id', 'token_count', 'page_number', 'is_embedded', 'created_at')
    can_delete = True
    show_change_link = True
    max_num = 10  # Only show first 10 chunks in inline


class CaseAnalysisInline(admin.StackedInline):
    """Inline admin for CaseAnalysis"""
    model = CaseAnalysis
    extra = 0
    readonly_fields = ('id', 'created_at', 'updated_at')
    fields = (
        'suggested_case_name',
        'document_types',
        'parties',
        'key_dates',
        'issues',
        'related_precedents',
        'suggested_next_steps',
        'scenario',
        'llm_model',
        'created_at',
        'updated_at',
    )
    can_delete = False
    show_change_link = True


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Admin interface for Document model"""

    list_display = (
        'title',
        'doc_type',
        'user',
        'status',
        'language',
        'chunk_count',
        'file_size_display',
        'created_at',
    )

    list_filter = (
        'doc_type',
        'status',
        'source_type',
        'language',
        'created_at',
    )

    search_fields = (
        'title',
        'user__email',
        'user__full_name',
    )

    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'chunk_count',
        'is_processing_complete',
        'file_size_display',
    )

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id',
                'user',
                'title',
                'doc_type',
                'language',
            )
        }),
        ('File Information', {
            'fields': (
                'source_type',
                'original_file',
                'file_type',
                'file_size',
                'file_size_display',
                'page_count',
            )
        }),
        ('Processing Status', {
            'fields': (
                'status',
                'is_processing_complete',
                'chunk_count',
                'error_message',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    inlines = [DocumentChunkInline, CaseAnalysisInline]

    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def file_size_display(self, obj):
        """Display file size in human-readable format"""
        if not obj.file_size:
            return '-'

        size = obj.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"

    file_size_display.short_description = 'File Size'

    def chunk_count(self, obj):
        """Display chunk count"""
        return obj.chunk_count

    chunk_count.short_description = 'Chunks'


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    """Admin interface for DocumentChunk model"""

    list_display = (
        'document',
        'chunk_index',
        'text_preview',
        'is_embedded',
        'token_count',
        'page_number',
        'created_at',
    )

    list_filter = (
        'document__doc_type',
        'created_at',
    )

    search_fields = (
        'document__title',
        'text',
        'embedding_id',
    )

    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'is_embedded',
        'text_preview',
    )

    fieldsets = (
        ('Chunk Information', {
            'fields': (
                'id',
                'document',
                'chunk_index',
                'text',
                'text_preview',
            )
        }),
        ('Position Metadata', {
            'fields': (
                'start_offset',
                'end_offset',
                'page_number',
            )
        }),
        ('Vector DB', {
            'fields': (
                'embedding_id',
                'is_embedded',
                'token_count',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    date_hierarchy = 'created_at'
    ordering = ('document', 'chunk_index')

    def text_preview(self, obj):
        """Display first 100 characters of text"""
        if len(obj.text) > 100:
            return f"{obj.text[:100]}..."
        return obj.text

    text_preview.short_description = 'Text Preview'


@admin.register(Summary)
class SummaryAdmin(admin.ModelAdmin):
    """Admin interface for Summary model"""

    list_display = (
        'document',
        'summary_type',
        'llm_model',
        'content_preview',
        'created_at',
    )

    list_filter = (
        'summary_type',
        'llm_model',
        'created_at',
    )

    search_fields = (
        'document__title',
        'content',
    )

    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'content_preview',
    )

    fieldsets = (
        ('Summary Information', {
            'fields': (
                'id',
                'document',
                'summary_type',
                'llm_model',
            )
        }),
        ('Content', {
            'fields': (
                'content',
                'content_preview',
            )
        }),
        ('Metadata', {
            'fields': (
                'meta',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def content_preview(self, obj):
        """Display first 200 characters of summary content"""
        if len(obj.content) > 200:
            return f"{obj.content[:200]}..."
        return obj.content

    content_preview.short_description = 'Content Preview'


@admin.register(KeyClause)
class KeyClauseAdmin(admin.ModelAdmin):
    """Admin interface for KeyClause model"""

    list_display = (
        'document',
        'title',
        'clause_type',
        'importance_score',
        'llm_model',
        'created_at',
    )

    list_filter = (
        'clause_type',
        'llm_model',
        'created_at',
    )

    search_fields = (
        'document__title',
        'title',
        'content',
    )

    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'content_preview',
    )

    fieldsets = (
        ('Clause Information', {
            'fields': (
                'id',
                'document',
                'clause_type',
                'title',
                'importance_score',
                'llm_model',
            )
        }),
        ('Content', {
            'fields': (
                'content',
                'content_preview',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    date_hierarchy = 'created_at'
    ordering = ('-importance_score', '-created_at')

    def content_preview(self, obj):
        """Display first 200 characters of clause content"""
        if len(obj.content) > 200:
            return f"{obj.content[:200]}..."
        return obj.content

    content_preview.short_description = 'Content Preview'


@admin.register(RiskAnalysisResult)
class RiskAnalysisResultAdmin(admin.ModelAdmin):
    """Admin interface for RiskAnalysisResult model"""

    list_display = (
        'document',
        'severity',
        'overall_risk_score',
        'risk_item_count_display',
        'llm_model',
        'created_at',
    )

    list_filter = (
        'severity',
        'llm_model',
        'created_at',
    )

    search_fields = (
        'document__title',
        'summary',
    )

    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'risk_item_count_display',
        'is_high_risk',
        'summary_preview',
    )

    fieldsets = (
        ('Risk Analysis Information', {
            'fields': (
                'id',
                'document',
                'overall_risk_score',
                'severity',
                'llm_model',
                'is_high_risk',
            )
        }),
        ('Analysis Results', {
            'fields': (
                'summary',
                'summary_preview',
                'risk_items',
                'risk_item_count_display',
                'recommendations',
            )
        }),
        ('Metadata', {
            'fields': (
                'meta',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    date_hierarchy = 'created_at'
    ordering = ('-overall_risk_score', '-created_at')

    def summary_preview(self, obj):
        """Display first 200 characters of summary"""
        if len(obj.summary) > 200:
            return f"{obj.summary[:200]}..."
        return obj.summary

    summary_preview.short_description = 'Summary Preview'

    def risk_item_count_display(self, obj):
        """Display number of risk items"""
        return obj.risk_item_count

    risk_item_count_display.short_description = 'Risk Items'


@admin.register(CaseAnalysis)
class CaseAnalysisAdmin(admin.ModelAdmin):
    """Admin interface for CaseAnalysis model"""

    list_display = (
        'suggested_case_name',
        'document',
        'party_count_display',
        'issue_count_display',
        'has_precedents_display',
        'llm_model',
        'created_at',
    )

    list_filter = (
        'llm_model',
        'created_at',
    )

    search_fields = (
        'suggested_case_name',
        'document__title',
        'parties',
        'issues',
    )

    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'party_count_display',
        'issue_count_display',
        'has_precedents_display',
    )

    fieldsets = (
        ('Basic Information', {
            'fields': (
                'id',
                'document',
                'suggested_case_name',
                'document_types',
                'llm_model',
            )
        }),
        ('Case Details', {
            'fields': (
                'parties',
                'party_count_display',
                'key_dates',
                'issues',
                'issue_count_display',
            )
        }),
        ('Analysis Results', {
            'fields': (
                'related_precedents',
                'has_precedents_display',
                'suggested_next_steps',
                'scenario',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def party_count_display(self, obj):
        """Display number of parties"""
        return obj.party_count

    party_count_display.short_description = 'Parties'

    def issue_count_display(self, obj):
        """Display number of issues"""
        return obj.issue_count

    issue_count_display.short_description = 'Issues'

    def has_precedents_display(self, obj):
        """Display whether precedents were found"""
        return "✓" if obj.has_precedents else "✗"

    has_precedents_display.short_description = 'Has Precedents'
