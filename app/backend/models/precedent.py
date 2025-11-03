"""
Precedent model for storing Korean Supreme Court precedents
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator, String as SQLString
import uuid
import json
from datetime import datetime
from app.backend.database import Base


class JSONList(TypeDecorator):
    """
    SQLite-compatible JSON list type for storing arrays
    """
    impl = SQLString
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert Python list to JSON string for storage"""
        if value is None:
            return '[]'
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        """Convert JSON string back to Python list"""
        if value is None:
            return []
        return json.loads(value)


class Precedent(Base):
    """
    대법원 판례 모델

    Attributes:
        id: Unique precedent identifier (UUID)
        case_number: 사건번호 (e.g., "2023도1234")
        title: 판례 제목
        summary: 판례 요약
        full_text: 판례 전문
        court: 법원명 (대법원)
        decision_date: 선고일자
        case_type: 사건종류 (형사, 민사, etc.)
        specialization_tags: 전문분야 태그 (형사일반, 성범죄, 교통사고, etc.)
        citation: 판례 인용 정보
        case_link: 원본 링크
        created_at: DB 저장 시각
        updated_at: DB 수정 시각
    """

    __tablename__ = "precedents"

    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)

    # Case information
    case_number = Column(String(100), unique=True, index=True, nullable=False)
    title = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    full_text = Column(Text, nullable=True)

    # Court and date
    court = Column(String(100), default="대법원", nullable=False)
    decision_date = Column(DateTime, index=True, nullable=False)

    # Classification
    case_type = Column(String(50), default="형사", nullable=False)  # 형사, 민사, 행정 등
    specialization_tags = Column(JSONList, default=list, nullable=False)

    # References
    citation = Column(String(200), nullable=True)
    case_link = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Indexes for efficient querying
    __table_args__ = (
        Index('idx_decision_date_desc', decision_date.desc()),
        Index('idx_case_type_date', case_type, decision_date.desc()),
    )

    def __repr__(self):
        return f"<Precedent(case_number='{self.case_number}', title='{self.title[:30]}...')>"

    def to_dict(self):
        """Convert precedent to dictionary"""
        return {
            "id": str(self.id),
            "case_number": self.case_number,
            "title": self.title,
            "summary": self.summary,
            "full_text": self.full_text,
            "court": self.court,
            "decision_date": self.decision_date.isoformat() if self.decision_date else None,
            "case_type": self.case_type,
            "specialization_tags": self.specialization_tags,
            "citation": self.citation,
            "case_link": self.case_link,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
