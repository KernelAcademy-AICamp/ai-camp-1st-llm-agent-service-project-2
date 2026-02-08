"""
Crawler Serializers

크롤링 시스템 API Serializers
"""
from rest_framework import serializers
from .models import DataSource, CrawlJob, CrawlLog


class DataSourceSerializer(serializers.ModelSerializer):
    """DataSource Serializer"""
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    total_jobs = serializers.IntegerField(read_only=True)
    successful_jobs = serializers.IntegerField(read_only=True)
    total_documents_collected = serializers.IntegerField(read_only=True)

    class Meta:
        model = DataSource
        fields = [
            'id', 'name', 'source_type', 'source_type_display',
            'base_url', 'api_key_required', 'is_active', 'config', 'description',
            'total_jobs', 'successful_jobs', 'total_documents_collected',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_name(self, value):
        """이름 유효성 검사"""
        if len(value.strip()) < 2:
            raise serializers.ValidationError("이름은 2자 이상이어야 합니다.")
        return value.strip()


class DataSourceListSerializer(serializers.ModelSerializer):
    """DataSource List Serializer (간략 버전)"""
    source_type_display = serializers.CharField(source='get_source_type_display', read_only=True)
    total_jobs = serializers.IntegerField(read_only=True)
    total_documents_collected = serializers.IntegerField(read_only=True)

    class Meta:
        model = DataSource
        fields = [
            'id', 'name', 'source_type', 'source_type_display',
            'is_active', 'total_jobs', 'total_documents_collected', 'created_at'
        ]


class CrawlLogSerializer(serializers.ModelSerializer):
    """CrawlLog Serializer"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    document_title = serializers.CharField(source='document.title', read_only=True)

    class Meta:
        model = CrawlLog
        fields = [
            'id', 'crawl_job', 'document', 'document_title',
            'status', 'status_display', 'message', 'error_message',
            'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CrawlLogListSerializer(serializers.ModelSerializer):
    """CrawlLog List Serializer (간략 버전)"""
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = CrawlLog
        fields = ['id', 'status', 'status_display', 'message', 'created_at']


class CrawlJobSerializer(serializers.ModelSerializer):
    """CrawlJob Serializer"""
    data_source_name = serializers.CharField(source='data_source.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    schedule_type_display = serializers.CharField(source='get_schedule_type_display', read_only=True)
    duration_seconds = serializers.FloatField(read_only=True)
    log_count = serializers.IntegerField(read_only=True)
    error_count = serializers.IntegerField(read_only=True)
    logs = CrawlLogListSerializer(source='crawl_logs', many=True, read_only=True)

    class Meta:
        model = CrawlJob
        fields = [
            'id', 'data_source', 'data_source_name',
            'status', 'status_display', 'schedule_type', 'schedule_type_display',
            'started_at', 'finished_at', 'last_run_at', 'next_run_at',
            'documents_collected', 'errors', 'filters',
            'duration_seconds', 'log_count', 'error_count',
            'logs', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'status', 'started_at', 'finished_at', 'last_run_at',
            'documents_collected', 'errors', 'created_at', 'updated_at'
        ]


class CrawlJobListSerializer(serializers.ModelSerializer):
    """CrawlJob List Serializer (간략 버전)"""
    data_source_name = serializers.CharField(source='data_source.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    schedule_type_display = serializers.CharField(source='get_schedule_type_display', read_only=True)
    duration_seconds = serializers.FloatField(read_only=True)
    error_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = CrawlJob
        fields = [
            'id', 'data_source', 'data_source_name',
            'status', 'status_display', 'schedule_type', 'schedule_type_display',
            'documents_collected', 'duration_seconds', 'error_count',
            'started_at', 'finished_at', 'created_at'
        ]


class TriggerCrawlSerializer(serializers.Serializer):
    """크롤링 트리거 요청 Serializer"""
    schedule_type = serializers.ChoiceField(
        choices=CrawlJob.ScheduleType.choices,
        default=CrawlJob.ScheduleType.MANUAL
    )
    filters = serializers.JSONField(required=False, default=dict)

    # 필터 세부 필드 (선택적)
    start_date = serializers.DateField(required=False, help_text="시작 날짜 (YYYY-MM-DD)")
    end_date = serializers.DateField(required=False, help_text="종료 날짜 (YYYY-MM-DD)")
    case_type = serializers.CharField(required=False, max_length=50, help_text="사건 유형 (예: 민사, 형사)")

    def validate(self, data):
        """유효성 검사"""
        # filters가 비어있고 개별 필터 필드가 있으면 filters에 추가
        if not data.get('filters'):
            data['filters'] = {}

        if 'start_date' in data and data['start_date']:
            data['filters']['start_date'] = data['start_date'].isoformat()
        if 'end_date' in data and data['end_date']:
            data['filters']['end_date'] = data['end_date'].isoformat()
        if 'case_type' in data and data['case_type']:
            data['filters']['case_type'] = data['case_type']

        return data


class CrawlJobStatusSerializer(serializers.Serializer):
    """크롤링 작업 상태 응답 Serializer"""
    job_id = serializers.UUIDField()
    status = serializers.CharField()
    status_display = serializers.CharField()
    documents_collected = serializers.IntegerField()
    errors = serializers.ListField()
    started_at = serializers.DateTimeField()
    finished_at = serializers.DateTimeField(allow_null=True)
    duration_seconds = serializers.FloatField(allow_null=True)
