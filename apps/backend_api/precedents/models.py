"""
Precedent Models
판례 모델 (SQLAlchemy → Django ORM 마이그레이션)
"""

from django.db import models
import uuid

class Precedent(models.Model):
    """
    대법원 판례 모델

    기존 apps.backend.models.precedent.Precedent (SQLAlchemy)를
    Django ORM으로 마이그레이션
    """

    # Primary Key (UUID)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Case Information
    case_number = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
        verbose_name='사건번호'
    )

    title = models.CharField(
        max_length=500,
        verbose_name='판례 제목'
    )

    summary = models.TextField(
        blank=True,
        null=True,
        verbose_name='판례 요약'
    )

    full_text = models.TextField(
        blank=True,
        null=True,
        verbose_name='판례 전문'
    )

    # Additional Details from Supreme Court Portal
    judgment_summary = models.TextField(
        blank=True,
        null=True,
        verbose_name='판시사항'
    )

    # ⚠️ 주의: PostgreSQL에는 character varying으로 JSON 문자열 저장됨 (SQLAlchemy 방식)
    # Django에서는 TextField로 매핑하고 애플리케이션 레벨에서 JSON 처리
    reference_statutes = models.TextField(
        default='[]',
        blank=True,
        verbose_name='참조조문 (JSON 문자열)'
    )

    reference_precedents = models.TextField(
        default='[]',
        blank=True,
        verbose_name='참조판례 (JSON 문자열)'
    )

    precedent_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='대법원 포털 판례 ID'
    )

    # Court and Date
    court = models.CharField(
        max_length=100,
        default='대법원',
        verbose_name='법원명'
    )

    decision_date = models.DateTimeField(
        db_index=True,
        verbose_name='선고일자'
    )

    # Classification
    case_type = models.CharField(
        max_length=50,
        default='형사',
        verbose_name='사건종류'
    )

    # ⚠️ 주의: PostgreSQL에는 character varying으로 JSON 문자열 저장됨
    specialization_tags = models.TextField(
        default='[]',
        blank=True,
        verbose_name='전문분야 태그 (JSON 문자열)'
    )

    # References
    citation = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name='판례 인용 정보'
    )

    case_link = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='원본 링크'
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'precedents'
        verbose_name = '판례'
        verbose_name_plural = '판례'
        ordering = ['-decision_date']
        indexes = [
            models.Index(fields=['-decision_date'], name='idx_decision_date_desc'),
            models.Index(fields=['case_type', '-decision_date'], name='idx_case_type_date'),
        ]

    def __str__(self):
        return f"{self.case_number} - {self.title[:30]}"


class PrecedentFeedback(models.Model):
    """
    판례 피드백 모델

    사용자가 RAG 검색 결과로 받은 판례에 대한 피드백

    ⚠️ 주의: DB 스키마에 맞춰 is_helpful, relevance_score, session_id 필드 포함
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    user = models.ForeignKey(
        'users.User',
        on_delete=models.SET_NULL,  # CASCADE → SET_NULL (DB 스키마 반영)
        related_name='precedent_feedbacks',
        null=True,  # DB에서 nullable
        blank=True,
        verbose_name='사용자'
    )

    precedent_id = models.CharField(
        max_length=200,  # DB: character varying(200)
        db_index=True,
        verbose_name='판례 ID'
    )

    query = models.CharField(  # TextField → CharField(1000)
        max_length=1000,  # DB: character varying(1000)
        verbose_name='사용자 질의'
    )

    feedback_type = models.CharField(
        max_length=20,
        choices=[
            ('like', '좋아요'),
            ('dislike', '싫어요'),
        ],
        verbose_name='피드백 유형'
    )

    # ⚠️ DB 스키마에 존재하는 필드 추가
    is_helpful = models.BooleanField(
        default=True,
        verbose_name='도움 여부'
    )

    relevance_score = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='관련성 점수'
    )

    comment = models.CharField(  # TextField → CharField(500)
        max_length=500,  # DB: character varying(500)
        blank=True,
        null=True,
        verbose_name='추가 의견'
    )

    session_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        verbose_name='세션 ID'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='생성일시'
    )

    class Meta:
        db_table = 'precedent_feedback'
        verbose_name = '판례 피드백'
        verbose_name_plural = '판례 피드백'
        ordering = ['-created_at']
        # unique_together 제거 (DB에 해당 제약조건 없음)

    def __str__(self):
        user_email = self.user.email if self.user else 'Anonymous'
        return f"{user_email} - {self.precedent_id} ({self.feedback_type})"


class PrecedentFeedbackStats(models.Model):
    """
    판례 피드백 통계

    집계된 피드백 통계 (AI Service에서 읽기 전용으로 사용)

    ⚠️ 주의: DB 스키마와 완전히 일치하도록 필드명 수정
    - like_count → total_likes
    - dislike_count → total_dislikes
    - total_count → total_feedback_count
    - like_ratio: FloatField (DB는 double precision)
    - avg_relevance_score, exclusion_threshold, last_updated 추가
    """

    precedent_id = models.CharField(
        max_length=200,  # DB 스키마 반영
        primary_key=True,
        verbose_name='판례 ID'
    )

    # ⚠️ DB 필드명과 일치시킴
    total_likes = models.IntegerField(
        default=0,
        verbose_name='좋아요 수'
    )

    total_dislikes = models.IntegerField(
        default=0,
        verbose_name='싫어요 수'
    )

    total_feedback_count = models.IntegerField(
        default=0,
        verbose_name='총 피드백 수'
    )

    like_ratio = models.FloatField(  # IntegerField → FloatField (DB: double precision)
        default=0.0,
        verbose_name='좋아요 비율'
    )

    avg_relevance_score = models.FloatField(  # DB 스키마에 존재
        null=True,
        blank=True,
        verbose_name='평균 관련성 점수'
    )

    should_exclude = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name='검색 결과 제외 여부'
    )

    exclusion_threshold = models.FloatField(  # DB 스키마에 존재
        default=0.3,
        verbose_name='제외 임계값'
    )

    # created_at 제거 (DB 스키마에 없음)
    # updated_at → last_updated로 변경
    last_updated = models.DateTimeField(
        auto_now=True,
        verbose_name='최종 업데이트 시각'
    )

    class Meta:
        db_table = 'precedent_feedback_stats'
        verbose_name = '판례 피드백 통계'
        verbose_name_plural = '판례 피드백 통계'

    def __str__(self):
        return f"{self.precedent_id} (👍 {self.total_likes} / 👎 {self.total_dislikes})"

    def update_stats(self):
        """피드백 통계 업데이트 (필드명 변경 반영)"""
        feedbacks = PrecedentFeedback.objects.filter(precedent_id=self.precedent_id)

        self.total_likes = feedbacks.filter(feedback_type='like').count()
        self.total_dislikes = feedbacks.filter(feedback_type='dislike').count()
        self.total_feedback_count = feedbacks.count()

        if self.total_feedback_count > 0:
            self.like_ratio = (self.total_likes / self.total_feedback_count)
        else:
            self.like_ratio = 0.0

        # 평균 관련성 점수 계산
        scores = feedbacks.filter(relevance_score__isnull=False).values_list('relevance_score', flat=True)
        if scores:
            self.avg_relevance_score = sum(scores) / len(scores)

        # 제외 기준: 총 피드백 5개 이상 + 좋아요 비율이 exclusion_threshold 미만
        self.should_exclude = (
            self.total_feedback_count >= 5 and self.like_ratio < self.exclusion_threshold
        )

        self.save()
