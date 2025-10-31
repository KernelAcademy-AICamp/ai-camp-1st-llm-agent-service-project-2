"""
Document Models
문서 관련 데이터베이스 모델
"""

from sqlalchemy import Column, String, Integer, BigInteger, Boolean, DateTime, DECIMAL, Text, ARRAY, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from app.core.database import Base


class Document(Base):
    """문서 메타데이터"""

    __tablename__ = "documents"

    # 기본 정보
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)
    mime_type = Column(String(100), default='application/pdf')

    # 분류
    document_type = Column(String(50), nullable=False)  # precedent, interpretation, law, constitution
    storage_type = Column(String(20), nullable=False, index=True)  # public, private

    # 소유권
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)
    is_public = Column(Boolean, default=False)

    # 파일 저장 경로
    storage_path = Column(String(500), nullable=False)
    is_encrypted = Column(Boolean, default=False)

    # OCR 관련
    ocr_status = Column(String(20), default='pending', index=True)  # pending, processing, completed, failed
    ocr_started_at = Column(DateTime(timezone=True))
    ocr_completed_at = Column(DateTime(timezone=True))
    ocr_confidence = Column(DECIMAL(5, 2))  # 평균 신뢰도
    page_count = Column(Integer)

    # 메타데이터
    title = Column(String(500))
    description = Column(Text)
    tags = Column(ARRAY(String))

    # 감사 로그
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), index=True)  # 소프트 삭제

    # Relationships
    pages = relationship("DocumentPage", back_populates="document", cascade="all, delete-orphan")
    structured_data = relationship("DocumentStructuredData", back_populates="document", cascade="all, delete-orphan")
    ai_labels = relationship("DocumentAILabel", back_populates="document", cascade="all, delete-orphan")
    ocr_jobs = relationship("OCRJob", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document {self.filename} ({self.document_type})>"


class DocumentPage(Base):
    """페이지별 텍스트"""

    __tablename__ = "document_pages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)
    page_number = Column(Integer, nullable=False, index=True)

    # OCR 추출 텍스트
    extracted_text = Column(Text)
    extracted_text_encrypted = Column(Text)  # 암호화된 텍스트 (사용자DB용)

    # OCR 메타데이터
    ocr_confidence = Column(DECIMAL(5, 2))
    ocr_language = Column(String(10), default='kor')
    word_count = Column(Integer)

    # 이미지 정보
    image_width = Column(Integer)
    image_height = Column(Integer)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="pages")

    def __repr__(self):
        return f"<DocumentPage {self.document_id} - Page {self.page_number}>"


class DocumentStructuredData(Base):
    """구조화 데이터 (CSV 형식)"""

    __tablename__ = "document_structured_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)

    # 문서 타입별 고유 ID
    source_id = Column(String(50), index=True)  # 법령일련번호, 해석례일련번호 등
    master_id = Column(String(50))  # MST (법령의 경우)

    # 구조화 정보
    section_type = Column(String(50), nullable=False, index=True)  # 조문, 항, 호, 질의요지, 회답 등
    sentence_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_encrypted = Column(Text)  # 암호화된 내용

    # 메타데이터
    page_number = Column(Integer)
    ocr_confidence = Column(DECIMAL(5, 2))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    document = relationship("Document", back_populates="structured_data")

    def __repr__(self):
        return f"<StructuredData {self.document_id} - {self.section_type} #{self.sentence_number}>"


class DocumentAILabel(Base):
    """AI 라벨 (JSON 형식)"""

    __tablename__ = "document_ai_labels"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)

    # 문서 정보 (info 섹션)
    law_class = Column(String(10))
    docu_type = Column(String(10), index=True)  # 01:법령, 02:판례, 03:해석례, 04:헌재
    source_identifier = Column(String(50))  # precedId, interpreId, determintId 등

    case_name = Column(Text)
    case_number = Column(String(100))
    decision_date = Column(Date)

    court_name = Column(String(100))
    court_code = Column(String(20))

    agenda = Column(Text)
    agenda_num = Column(String(50))

    ministry_code = Column(String(20))
    ministry_name = Column(String(100))

    full_text_available = Column(Boolean)
    sentence_type = Column(String(50))

    # AI 학습 라벨 (label 섹션)
    instruction = Column(Text)
    input_text = Column(Text)  # QA의 경우
    output_text = Column(Text)

    origin_word_count = Column(Integer)
    label_word_count = Column(Integer)

    # 메타데이터
    label_type = Column(String(20), index=True)  # QA, SUMMARY, CLASSIFICATION
    generated_by = Column(String(50))  # OCR, MANUAL, AI_GENERATED
    quality_score = Column(DECIMAL(5, 2))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    document = relationship("Document", back_populates="ai_labels")

    def __repr__(self):
        return f"<AILabel {self.document_id} - {self.label_type}>"


class OCRJob(Base):
    """OCR 작업 추적"""

    __tablename__ = "ocr_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id', ondelete='CASCADE'), nullable=False, index=True)

    status = Column(String(20), default='queued', index=True)  # queued, processing, completed, failed
    celery_task_id = Column(String(255), index=True)

    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    document = relationship("Document", back_populates="ocr_jobs")

    def __repr__(self):
        return f"<OCRJob {self.id} - {self.status}>"


class AuditLog(Base):
    """감사 로그"""

    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), index=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), index=True)

    action = Column(String(50), nullable=False, index=True)  # upload, view, download, delete, update
    resource_type = Column(String(50), nullable=False)  # document, user, system

    ip_address = Column(String(45))  # IPv6 지원
    user_agent = Column(Text)

    details = Column(Text)  # JSON string으로 저장 가능

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<AuditLog {self.action} by {self.user_id}>"
