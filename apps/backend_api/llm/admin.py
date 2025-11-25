"""
LLM Admin Configuration
"""

from django.contrib import admin
from .models import LLMModelConfig, LLMCallLog, LLMComparisonResult


@admin.register(LLMModelConfig)
class LLMModelConfigAdmin(admin.ModelAdmin):
    """LLM Model Config Admin"""

    list_display = [
        'name', 'provider', 'model_id', 'status', 'is_default',
        'default_temperature', 'input_cost_display', 'output_cost_display', 'created_at'
    ]
    list_filter = ['provider', 'status', 'is_default']
    search_fields = ['name', 'model_id', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    ordering = ['provider', 'name']

    fieldsets = (
        ('Model Information', {
            'fields': ('id', 'name', 'provider', 'model_id', 'description')
        }),
        ('Configuration', {
            'fields': ('api_key_env_var', 'base_url', 'default_temperature', 'default_max_tokens')
        }),
        ('Pricing (per 1K tokens)', {
            'fields': ('input_cost_per_1k', 'output_cost_per_1k')
        }),
        ('Status', {
            'fields': ('status', 'is_default')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def input_cost_display(self, obj):
        return f"${obj.input_cost_per_1k}"
    input_cost_display.short_description = "Input Cost/1K"

    def output_cost_display(self, obj):
        return f"${obj.output_cost_per_1k}"
    output_cost_display.short_description = "Output Cost/1K"


@admin.register(LLMCallLog)
class LLMCallLogAdmin(admin.ModelAdmin):
    """LLM Call Log Admin"""

    list_display = [
        'short_id', 'user_email', 'model_name', 'task_type', 'status',
        'total_tokens', 'latency_display', 'cost_display', 'created_at'
    ]
    list_filter = ['task_type', 'status', 'model_config__provider', 'created_at']
    search_fields = ['user__email', 'model_config__name', 'prompt_text']
    readonly_fields = [
        'id', 'created_at', 'total_tokens', 'estimated_cost',
        'prompt_preview', 'response_preview'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Call Information', {
            'fields': ('id', 'user', 'model_config', 'task_type', 'status')
        }),
        ('Request', {
            'fields': ('prompt_preview', 'prompt_tokens')
        }),
        ('Response', {
            'fields': ('response_preview', 'response_tokens', 'total_tokens')
        }),
        ('Performance', {
            'fields': ('latency_ms', 'estimated_cost', 'error_message')
        }),
        ('Context', {
            'fields': ('comparison_session_id', 'document_id', 'meta'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def short_id(self, obj):
        return str(obj.id)[:8]
    short_id.short_description = "ID"

    def user_email(self, obj):
        return obj.user.email if obj.user else "-"
    user_email.short_description = "User"

    def model_name(self, obj):
        return obj.model_config.name if obj.model_config else "-"
    model_name.short_description = "Model"

    def latency_display(self, obj):
        if obj.latency_ms >= 1000:
            return f"{obj.latency_ms / 1000:.2f}s"
        return f"{obj.latency_ms}ms"
    latency_display.short_description = "Latency"

    def cost_display(self, obj):
        return f"${obj.estimated_cost:.6f}"
    cost_display.short_description = "Cost"

    def prompt_preview(self, obj):
        return obj.prompt_text[:500] + "..." if len(obj.prompt_text) > 500 else obj.prompt_text
    prompt_preview.short_description = "Prompt Preview"

    def response_preview(self, obj):
        return obj.response_text[:500] + "..." if len(obj.response_text) > 500 else obj.response_text
    response_preview.short_description = "Response Preview"


@admin.register(LLMComparisonResult)
class LLMComparisonResultAdmin(admin.ModelAdmin):
    """LLM Comparison Result Admin"""

    list_display = [
        'short_session_id', 'user_email', 'task_type', 'total_models',
        'fastest_model', 'cheapest_model', 'has_preference', 'created_at'
    ]
    list_filter = ['task_type', 'created_at']
    search_fields = ['session_id', 'user__email', 'fastest_model', 'cheapest_model']
    readonly_fields = ['id', 'session_id', 'created_at', 'results_preview']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    fieldsets = (
        ('Session Information', {
            'fields': ('id', 'session_id', 'user', 'task_type')
        }),
        ('Input', {
            'fields': ('input_text',)
        }),
        ('Results', {
            'fields': ('results_preview', 'total_models', 'fastest_model', 'cheapest_model')
        }),
        ('User Evaluation', {
            'fields': ('preferred_model_id', 'evaluation_notes')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def short_session_id(self, obj):
        return str(obj.session_id)[:8]
    short_session_id.short_description = "Session"

    def user_email(self, obj):
        return obj.user.email if obj.user else "-"
    user_email.short_description = "User"

    def has_preference(self, obj):
        return obj.preferred_model_id is not None
    has_preference.boolean = True
    has_preference.short_description = "Evaluated"

    def results_preview(self, obj):
        if not obj.results:
            return "-"
        preview_lines = []
        for r in obj.results[:3]:
            model = r.get('model_name', 'Unknown')
            latency = r.get('latency_ms', 0)
            preview_lines.append(f"{model}: {latency}ms")
        if len(obj.results) > 3:
            preview_lines.append(f"... and {len(obj.results) - 3} more")
        return "\n".join(preview_lines)
    results_preview.short_description = "Results Preview"
