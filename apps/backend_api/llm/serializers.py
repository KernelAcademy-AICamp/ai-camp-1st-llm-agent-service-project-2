"""
LLM Serializers
"""

from rest_framework import serializers
from .models import LLMModelConfig, LLMCallLog, LLMComparisonResult


class LLMModelConfigSerializer(serializers.ModelSerializer):
    """LLM Model Config Serializer"""

    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = LLMModelConfig
        fields = [
            'id', 'name', 'provider', 'provider_display', 'model_id',
            'api_key_env_var', 'base_url',
            'default_temperature', 'default_max_tokens',
            'input_cost_per_1k', 'output_cost_per_1k',
            'status', 'status_display', 'is_default', 'is_available',
            'description', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class LLMModelConfigListSerializer(serializers.ModelSerializer):
    """LLM Model Config List Serializer (compact)"""

    provider_display = serializers.CharField(source='get_provider_display', read_only=True)
    is_available = serializers.BooleanField(read_only=True)

    class Meta:
        model = LLMModelConfig
        fields = [
            'id', 'name', 'provider', 'provider_display', 'model_id',
            'status', 'is_default', 'is_available'
        ]


class LLMCallLogSerializer(serializers.ModelSerializer):
    """LLM Call Log Serializer"""

    user_email = serializers.CharField(source='user.email', read_only=True)
    model_name = serializers.CharField(source='model_config.name', read_only=True)
    model_provider = serializers.CharField(source='model_config.provider', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = LLMCallLog
        fields = [
            'id', 'user', 'user_email', 'model_config', 'model_name', 'model_provider',
            'task_type', 'task_type_display',
            'prompt_text', 'prompt_tokens',
            'response_text', 'response_tokens', 'total_tokens',
            'latency_ms', 'status', 'status_display', 'error_message',
            'estimated_cost', 'comparison_session_id', 'document_id',
            'meta', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'total_tokens', 'estimated_cost']


class LLMCallLogListSerializer(serializers.ModelSerializer):
    """LLM Call Log List Serializer (compact)"""

    model_name = serializers.CharField(source='model_config.name', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)

    class Meta:
        model = LLMCallLog
        fields = [
            'id', 'model_name', 'task_type', 'task_type_display',
            'total_tokens', 'latency_ms', 'status', 'estimated_cost', 'created_at'
        ]


class LLMComparisonResultSerializer(serializers.ModelSerializer):
    """LLM Comparison Result Serializer"""

    user_email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = LLMComparisonResult
        fields = [
            'id', 'session_id', 'user', 'user_email',
            'task_type', 'input_text', 'results',
            'total_models', 'fastest_model', 'cheapest_model',
            'preferred_model_id', 'evaluation_notes', 'created_at'
        ]
        read_only_fields = ['id', 'session_id', 'created_at']


class CompareRequestSerializer(serializers.Serializer):
    """Request serializer for LLM comparison"""

    text = serializers.CharField(help_text="Input text to process")
    task_type = serializers.ChoiceField(
        choices=['summarize', 'clauses', 'risk_analysis', 'case_analysis', 'chat'],
        help_text="Type of task to perform"
    )
    model_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        help_text="List of model config IDs to compare. If empty, uses all active models."
    )
    document_id = serializers.UUIDField(required=False, allow_null=True)
    options = serializers.DictField(required=False, default=dict)


class ModelResultSerializer(serializers.Serializer):
    """Single model result in comparison"""

    model_id = serializers.UUIDField()
    model_name = serializers.CharField()
    provider = serializers.CharField()
    response_text = serializers.CharField()
    prompt_tokens = serializers.IntegerField()
    response_tokens = serializers.IntegerField()
    total_tokens = serializers.IntegerField()
    latency_ms = serializers.IntegerField()
    estimated_cost = serializers.DecimalField(max_digits=10, decimal_places=6)
    status = serializers.CharField()
    error_message = serializers.CharField(allow_blank=True)


class CompareResponseSerializer(serializers.Serializer):
    """Response serializer for LLM comparison"""

    session_id = serializers.UUIDField()
    task_type = serializers.CharField()
    input_text = serializers.CharField()
    results = ModelResultSerializer(many=True)
    total_models = serializers.IntegerField()
    fastest_model = serializers.CharField()
    cheapest_model = serializers.CharField()
    summary = serializers.DictField()


class EvaluateComparisonSerializer(serializers.Serializer):
    """Request serializer for evaluating a comparison"""

    session_id = serializers.UUIDField()
    preferred_model_id = serializers.UUIDField()
    evaluation_notes = serializers.CharField(required=False, allow_blank=True)
