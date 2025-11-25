"""
Crawler Models

크롤링/데이터 수집 시스템을 위한 모델 정의
- DataSource: 데이터 소스 (대법원 API, 법령 API, 웹 크롤링 등)
- CrawlJob: 크롤링 작업
- CrawlLog: 크롤링 로그
"""
import uuid
from django.db import models
from django.utils import timezone


class DataSource(models.Model):
    """데이터 소스 모델"""

    class SourceType(models.TextChoices):
        COURT_API = 'COURT_API', '대법원 판례 API'
        STATUTE_API = 'STATUTE_API', '법령 API'
        WEB_CRAWL = 'WEB_CRAWL', '웹 크롤링'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, verbose_name='소스 이름')
    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        verbose_name='소스 유형'
    )
    base_url = models.URLField(max_length=500, verbose_name='기본 URL')
    api_key_required = models.BooleanField(default=False, verbose_name='API 키 필요 여부')
    is_active = models.BooleanField(default=True, verbose_name='활성화 여부')
    config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='크롤링 설정',
        help_text='크롤링 관련 추가 설정 (예: 헤더, 쿠키, 페이지네이션 등)'
    )
    description = models.TextField(blank=True, verbose_name='설명')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        db_table = 'data_sources'
        verbose_name = '데이터 소스'
        verbose_name_plural = '데이터 소스 목록'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_source_type_display()})"

    @property
    def total_jobs(self):
        """전체 크롤링 작업 수"""
        return self.crawl_jobs.count()

    @property
    def successful_jobs(self):
        """성공한 크롤링 작업 수"""
        return self.crawl_jobs.filter(status=CrawlJob.Status.COMPLETED).count()

    @property
    def total_documents_collected(self):
        """수집된 전체 문서 수"""
        return self.crawl_jobs.aggregate(
            total=models.Sum('documents_collected')
        )['total'] or 0


class CrawlJob(models.Model):
    """크롤링 작업 모델"""

    class Status(models.TextChoices):
        PENDING = 'PENDING', '대기중'
        RUNNING = 'RUNNING', '실행중'
        COMPLETED = 'COMPLETED', '완료'
        FAILED = 'FAILED', '실패'
        CANCELLED = 'CANCELLED', '취소됨'

    class ScheduleType(models.TextChoices):
        MANUAL = 'MANUAL', '수동'
        DAILY = 'DAILY', '매일'
        WEEKLY = 'WEEKLY', '매주'
        MONTHLY = 'MONTHLY', '매월'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    data_source = models.ForeignKey(
        DataSource,
        on_delete=models.CASCADE,
        related_name='crawl_jobs',
        verbose_name='데이터 소스'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='상태'
    )
    schedule_type = models.CharField(
        max_length=20,
        choices=ScheduleType.choices,
        default=ScheduleType.MANUAL,
        verbose_name='스케줄 유형'
    )

    # 실행 정보
    started_at = models.DateTimeField(null=True, blank=True, verbose_name='시작 시간')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='종료 시간')
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name='마지막 실행 시간')
    next_run_at = models.DateTimeField(null=True, blank=True, verbose_name='다음 실행 시간')

    # 결과 정보
    documents_collected = models.IntegerField(default=0, verbose_name='수집된 문서 수')
    errors = models.JSONField(
        default=list,
        blank=True,
        verbose_name='에러 목록'
    )

    # 필터 및 파라미터
    filters = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='필터 조건',
        help_text='크롤링 필터 (예: start_date, end_date, case_type 등)'
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='수정일')

    class Meta:
        db_table = 'crawl_jobs'
        verbose_name = '크롤링 작업'
        verbose_name_plural = '크롤링 작업 목록'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['data_source', 'status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.data_source.name} - {self.get_status_display()} ({self.created_at.strftime('%Y-%m-%d %H:%M')})"

    @property
    def duration_seconds(self):
        """실행 시간 (초)"""
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def log_count(self):
        """로그 개수"""
        return self.crawl_logs.count()

    @property
    def error_count(self):
        """에러 로그 개수"""
        return self.crawl_logs.filter(status='ERROR').count()

    def start(self):
        """작업 시작"""
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save()

    def complete(self, documents_count=0):
        """작업 완료"""
        self.status = self.Status.COMPLETED
        self.finished_at = timezone.now()
        self.last_run_at = self.finished_at
        self.documents_collected = documents_count
        self.save()

    def fail(self, error_message=None):
        """작업 실패"""
        self.status = self.Status.FAILED
        self.finished_at = timezone.now()
        if error_message:
            self.errors.append({
                'message': error_message,
                'timestamp': timezone.now().isoformat()
            })
        self.save()


class CrawlLog(models.Model):
    """크롤링 로그 모델"""

    class LogStatus(models.TextChoices):
        INFO = 'INFO', '정보'
        SUCCESS = 'SUCCESS', '성공'
        WARNING = 'WARNING', '경고'
        ERROR = 'ERROR', '에러'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    crawl_job = models.ForeignKey(
        CrawlJob,
        on_delete=models.CASCADE,
        related_name='crawl_logs',
        verbose_name='크롤링 작업'
    )
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='crawl_logs',
        verbose_name='관련 문서'
    )
    status = models.CharField(
        max_length=20,
        choices=LogStatus.choices,
        default=LogStatus.INFO,
        verbose_name='상태'
    )
    message = models.TextField(blank=True, verbose_name='메시지')
    error_message = models.TextField(blank=True, verbose_name='에러 메시지')
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='메타데이터',
        help_text='추가 로그 정보 (예: URL, 응답 코드, 처리 시간 등)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='생성일')

    class Meta:
        db_table = 'crawl_logs'
        verbose_name = '크롤링 로그'
        verbose_name_plural = '크롤링 로그 목록'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['crawl_job', 'status']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"[{self.get_status_display()}] {self.message[:50]}..."

    @classmethod
    def log_info(cls, crawl_job, message, document=None, metadata=None):
        """정보 로그 생성"""
        return cls.objects.create(
            crawl_job=crawl_job,
            document=document,
            status=cls.LogStatus.INFO,
            message=message,
            metadata=metadata or {}
        )

    @classmethod
    def log_success(cls, crawl_job, message, document=None, metadata=None):
        """성공 로그 생성"""
        return cls.objects.create(
            crawl_job=crawl_job,
            document=document,
            status=cls.LogStatus.SUCCESS,
            message=message,
            metadata=metadata or {}
        )

    @classmethod
    def log_warning(cls, crawl_job, message, document=None, metadata=None):
        """경고 로그 생성"""
        return cls.objects.create(
            crawl_job=crawl_job,
            document=document,
            status=cls.LogStatus.WARNING,
            message=message,
            metadata=metadata or {}
        )

    @classmethod
    def log_error(cls, crawl_job, message, error_message=None, document=None, metadata=None):
        """에러 로그 생성"""
        return cls.objects.create(
            crawl_job=crawl_job,
            document=document,
            status=cls.LogStatus.ERROR,
            message=message,
            error_message=error_message or '',
            metadata=metadata or {}
        )
