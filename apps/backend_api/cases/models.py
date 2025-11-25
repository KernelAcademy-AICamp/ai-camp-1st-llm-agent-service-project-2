"""
Case Models
사건 모델
"""

from django.db import models
import uuid


class Case(models.Model):
    """사건 모델"""

    STATUS_CHOICES = [
        ('draft', '작성중'),
        ('analyzing', '분석중'),
        ('analyzed', '분석완료'),
        ('completed', '완료'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='cases',
        verbose_name='사용자'
    )

    title = models.CharField(
        max_length=255,
        verbose_name='사건명'
    )

    content = models.TextField(
        verbose_name='사건 내용'
    )

    analysis = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='AI 분석 결과'
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name='상태'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'cases'
        verbose_name = '사건'
        verbose_name_plural = '사건'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.user.email})"


class ChatHistory(models.Model):
    """채팅 히스토리"""

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='chat_histories',
        verbose_name='사용자'
    )

    case = models.ForeignKey(
        Case,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_histories',
        verbose_name='관련 사건 (deprecated)'
    )

    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='chat_histories',
        verbose_name='관련 문서'
    )

    query = models.TextField(
        verbose_name='사용자 질문'
    )

    answer = models.TextField(
        verbose_name='AI 답변'
    )

    sources = models.JSONField(
        default=list,
        blank=True,
        verbose_name='출처 판례'
    )

    model = models.CharField(
        max_length=100,
        default='',
        verbose_name='사용 모델'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    class Meta:
        db_table = 'chat_history'
        verbose_name = '채팅 히스토리'
        verbose_name_plural = '채팅 히스토리'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} - {self.query[:30]}"
