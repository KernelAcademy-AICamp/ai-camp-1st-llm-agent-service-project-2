from django.contrib import admin
from .models import Document, DocumentChunk


class DocumentChunkInline(admin.TabularInline):
    """Inline admin for DocumentChunk"""
    model = DocumentChunk
    extra = 0
    readonly_fields = ('id', 'chunk_index', 'is_embedded', 'created_at')
    fields = ('chunk_index', 'text', 'embedding_id', 'token_count', 'page_number', 'is_embedded', 'created_at')
    can_delete = True
    show_change_link = True
    max_num = 10  # Only show first 10 chunks in inline


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

    inlines = [DocumentChunkInline]

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
