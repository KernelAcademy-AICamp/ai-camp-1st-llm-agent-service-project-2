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


class CriminalCase(models.Model):
    """형사 사건 모델"""

    class Stage(models.TextChoices):
        COMPLAINT = 'COMPLAINT', '고소/고발/인지'
        INVESTIGATION = 'INVESTIGATION', '수사 진행'
        PROSECUTION = 'PROSECUTION', '기소'
        TRIAL = 'TRIAL', '공판'
        JUDGMENT = 'JUDGMENT', '판결'
        CLOSED = 'CLOSED', '종결'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='criminal_cases',
        verbose_name='사용자'
    )

    case_name = models.CharField(
        max_length=255,
        verbose_name='사건명'
    )

    summary = models.TextField(
        blank=True,
        verbose_name='사건 요약'
    )

    # 형사 분석 결과
    crime_type = models.CharField(
        max_length=100,
        verbose_name='범죄 유형'
    )

    crime_elements = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='구성요건 분석 결과'
    )

    sentencing_factors = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='양형인자'
    )

    expected_sentence = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='예상 양형'
    )

    defense_strategies = models.JSONField(
        default=list,
        blank=True,
        verbose_name='변호 전략'
    )

    related_precedents = models.JSONField(
        default=list,
        blank=True,
        verbose_name='관련 판례'
    )

    # 사건 진행 상태
    stage = models.CharField(
        max_length=20,
        choices=Stage.choices,
        default=Stage.COMPLAINT,
        verbose_name='진행 단계'
    )

    # 일정 정보 (JSON으로 저장)
    schedules = models.JSONField(
        default=list,
        blank=True,
        verbose_name='일정 목록'
    )

    # 조건 태그 (유사 사건 검색용)
    conditions = models.JSONField(
        default=list,
        blank=True,
        verbose_name='조건 태그'
    )

    # 업로드된 파일 정보
    uploaded_files = models.JSONField(
        default=list,
        blank=True,
        verbose_name='업로드 파일'
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
        db_table = 'criminal_cases'
        verbose_name = '형사 사건'
        verbose_name_plural = '형사 사건'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.case_name} ({self.crime_type})"


class CriminalCaseSchedule(models.Model):
    """형사 사건 일정 (정규화된 별도 테이블)"""

    class ScheduleType(models.TextChoices):
        HEARING = 'HEARING', '공판 기일'
        SUBMISSION = 'SUBMISSION', '서류 제출'
        MEETING = 'MEETING', '상담/회의'
        DEADLINE = 'DEADLINE', '기한'
        POLICE = 'POLICE', '경찰 출석'
        PROSECUTOR = 'PROSECUTOR', '검찰 출석'

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    case = models.ForeignKey(
        CriminalCase,
        on_delete=models.CASCADE,
        related_name='schedule_items',
        verbose_name='사건'
    )

    date = models.DateField(
        verbose_name='일정 날짜'
    )

    title = models.CharField(
        max_length=255,
        verbose_name='일정 제목'
    )

    schedule_type = models.CharField(
        max_length=20,
        choices=ScheduleType.choices,
        verbose_name='일정 유형'
    )

    description = models.TextField(
        blank=True,
        verbose_name='상세 설명'
    )

    is_completed = models.BooleanField(
        default=False,
        verbose_name='완료 여부'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    class Meta:
        db_table = 'criminal_case_schedules'
        verbose_name = '형사 사건 일정'
        verbose_name_plural = '형사 사건 일정'
        ordering = ['date']

    def __str__(self):
        return f"{self.case.case_name} - {self.title} ({self.date})"
