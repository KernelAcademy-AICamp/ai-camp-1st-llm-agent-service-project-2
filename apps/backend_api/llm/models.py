"""
LLM Models
LLM 모델 설정 및 호출 로그
"""

import uuid
from django.db import models
from django.conf import settings


class AgentHubSession(models.Model):
    """Persistent Agent Hub chat session"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_id = models.UUIDField(unique=True, db_index=True, help_text="External session identifier")

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='agent_hub_sessions',
        verbose_name='사용자'
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_hub_sessions',
        verbose_name='조직'
    )
    project = models.ForeignKey(
        'organizations.Project',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='agent_hub_sessions',
        verbose_name='프로젝트'
    )

    title = models.CharField(max_length=255, blank=True, verbose_name='세션 제목')
    last_message_preview = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='마지막 메시지 요약'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')
    last_activity = models.DateTimeField(auto_now=True, verbose_name='마지막 활동')
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name='종료일시')

    total_messages = models.PositiveIntegerField(default=0, verbose_name='메시지 수')
    total_workflows_executed = models.PositiveIntegerField(
        default=0,
        verbose_name='워크플로우 실행 수'
    )

    metadata = models.JSONField(default=dict, blank=True, verbose_name='추가 메타데이터')

    class Meta:
        db_table = 'agent_hub_sessions'
        verbose_name = 'Agent Hub 세션'
        verbose_name_plural = 'Agent Hub 세션'
        ordering = ['-last_activity']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['user', '-last_activity']),
            models.Index(fields=['organization', '-last_activity']),
        ]

    def __str__(self):
        return f"Session {self.session_id} ({self.user.email})"


class AgentHubMessage(models.Model):
    """Persistent Agent Hub chat message"""

    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        AgentHubSession,
        to_field='session_id',
        db_column='session_id',
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='세션'
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, verbose_name='역할')
    content = models.TextField(verbose_name='내용')
    metadata = models.JSONField(default=dict, blank=True, verbose_name='메타데이터')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일시')

    class Meta:
        db_table = 'agent_hub_messages'
        verbose_name = 'Agent Hub 메시지'
        verbose_name_plural = 'Agent Hub 메시지'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.role} message ({self.created_at:%Y-%m-%d %H:%M})"


class LLMModelConfig(models.Model):
    """
    LLM 모델 설정

    다양한 LLM provider와 모델을 관리합니다.
    """

    PROVIDER_CHOICES = [
        ('openai', 'OpenAI'),
        ('anthropic', 'Anthropic Claude'),
        ('google', 'Google Gemini'),
        ('ollama', 'Ollama (Local)'),
    ]

    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deprecated', 'Deprecated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Model identification
    name = models.CharField(max_length=100, unique=True, help_text="Display name (e.g., GPT-4 Turbo)")
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, help_text="LLM provider")
    model_id = models.CharField(max_length=100, help_text="Model ID (e.g., gpt-4-turbo-preview)")

    # Configuration
    api_key_env_var = models.CharField(
        max_length=100,
        default="LLM_API_KEY",
        help_text="Environment variable name for API key"
    )
    base_url = models.URLField(blank=True, null=True, help_text="Custom API endpoint (optional)")

    # Default parameters
    default_temperature = models.FloatField(default=0.1)
    default_max_tokens = models.IntegerField(default=2000)

    # Pricing (per 1000 tokens, in USD)
    input_cost_per_1k = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)
    output_cost_per_1k = models.DecimalField(max_digits=10, decimal_places=6, default=0.0)

    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_default = models.BooleanField(default=False, help_text="Default model for comparison")

    # Metadata
    description = models.TextField(blank=True, help_text="Model description and capabilities")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'llm_model_configs'
        ordering = ['provider', 'name']
        verbose_name = 'LLM Model Config'
        verbose_name_plural = 'LLM Model Configs'

    def __str__(self):
        return f"{self.name} ({self.provider})"

    def save(self, *args, **kwargs):
        # 단 하나의 default만 허용
        if self.is_default:
            LLMModelConfig.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    @property
    def is_available(self):
        """Check if model is available (active status)"""
        return self.status == 'active'


class LLMCallLog(models.Model):
    """
    LLM 호출 로그

    각 LLM 호출의 상세 정보를 기록합니다.
    """

    TASK_TYPE_CHOICES = [
        ('summarize', 'Summarize'),
        ('clauses', 'Extract Clauses'),
        ('risk_analysis', 'Risk Analysis'),
        ('case_analysis', 'Case Analysis'),
        ('compare', 'Model Comparison'),
        ('chat', 'Chat'),
        ('other', 'Other'),
    ]

    STATUS_CHOICES = [
        ('success', 'Success'),
        ('error', 'Error'),
        ('timeout', 'Timeout'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User & Model
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='llm_call_logs'
    )
    model_config = models.ForeignKey(
        LLMModelConfig,
        on_delete=models.SET_NULL,
        null=True,
        related_name='call_logs'
    )

    # Request info
    task_type = models.CharField(max_length=20, choices=TASK_TYPE_CHOICES)
    prompt_text = models.TextField(help_text="Input prompt (truncated if too long)")
    prompt_tokens = models.IntegerField(default=0, help_text="Number of input tokens")

    # Response info
    response_text = models.TextField(blank=True, help_text="LLM response (truncated if too long)")
    response_tokens = models.IntegerField(default=0, help_text="Number of output tokens")
    total_tokens = models.IntegerField(default=0, help_text="Total tokens used")

    # Performance metrics
    latency_ms = models.IntegerField(default=0, help_text="Response time in milliseconds")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='success')
    error_message = models.TextField(blank=True)

    # Cost tracking
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=6, default=0.0, help_text="Estimated cost in USD")

    # Comparison session (for compare API)
    comparison_session_id = models.UUIDField(null=True, blank=True, help_text="Session ID for grouped comparisons")

    # Context
    document_id = models.UUIDField(null=True, blank=True, help_text="Related document ID")

    # Metadata
    meta = models.JSONField(default=dict, blank=True, help_text="Additional metadata")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'llm_call_logs'
        ordering = ['-created_at']
        verbose_name = 'LLM Call Log'
        verbose_name_plural = 'LLM Call Logs'
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['model_config', '-created_at']),
            models.Index(fields=['task_type', '-created_at']),
            models.Index(fields=['comparison_session_id']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        model_name = self.model_config.name if self.model_config else "Unknown"
        return f"{self.task_type} - {model_name} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    def calculate_cost(self):
        """Calculate estimated cost based on model pricing"""
        if not self.model_config:
            return 0.0

        input_cost = (self.prompt_tokens / 1000) * float(self.model_config.input_cost_per_1k)
        output_cost = (self.response_tokens / 1000) * float(self.model_config.output_cost_per_1k)

        return input_cost + output_cost

    def save(self, *args, **kwargs):
        # Auto-calculate cost before saving
        if self.model_config and self.estimated_cost == 0:
            self.estimated_cost = self.calculate_cost()

        # Calculate total tokens
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.response_tokens

        super().save(*args, **kwargs)


class LLMComparisonResult(models.Model):
    """
    LLM 비교 결과

    여러 모델의 비교 결과를 저장합니다.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Session
    session_id = models.UUIDField(help_text="Comparison session ID")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='llm_comparison_results'
    )

    # Request
    task_type = models.CharField(max_length=20)
    input_text = models.TextField(help_text="Original input text")

    # Results (JSON array of model results)
    results = models.JSONField(default=list, help_text="Array of results from each model")

    # Summary metrics
    total_models = models.IntegerField(default=0)
    fastest_model = models.CharField(max_length=100, blank=True)
    cheapest_model = models.CharField(max_length=100, blank=True)

    # User evaluation (optional)
    preferred_model_id = models.UUIDField(null=True, blank=True, help_text="User's preferred model")
    evaluation_notes = models.TextField(blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'llm_comparison_results'
        ordering = ['-created_at']
        verbose_name = 'LLM Comparison Result'
        verbose_name_plural = 'LLM Comparison Results'
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"Comparison {self.session_id} ({self.total_models} models)"
