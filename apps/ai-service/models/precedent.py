"""
Precedent Model (SQLAlchemy)
Django의 precedents 테이블 매핑 (Read/Write)
"""

from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

from .database import Base


class Precedent(Base):
    """
    판례 모델 (SQLAlchemy)

    Django의 precedents.Precedent 모델과 동일한 테이블 매핑
    크롤러 파이프라인에서 쓰기 가능
    """
    __tablename__ = "precedents"

    # Primary Key (UUID)
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Case Information
    case_number = Column(
        String(100),
        unique=True,
        index=True,
        nullable=False
    )

    title = Column(
        String(500),
        nullable=False
    )

    summary = Column(Text, nullable=True)
    full_text = Column(Text, nullable=True)
    judgment_summary = Column(Text, nullable=True)

    # JSON fields stored as text (matching Django model)
    reference_statutes = Column(Text, default='[]')
    reference_precedents = Column(Text, default='[]')

    precedent_id = Column(
        String(100),
        index=True,
        nullable=True
    )

    # Court and Date
    court = Column(String(100), default='대법원')
    decision_date = Column(DateTime, index=True, nullable=False)

    # Classification
    case_type = Column(String(50), default='형사')
    specialization_tags = Column(Text, default='[]')

    # References
    citation = Column(String(200), nullable=True)
    case_link = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes (matching Django model)
    __table_args__ = (
        Index('idx_decision_date_desc', decision_date.desc()),
        Index('idx_case_type_date', case_type, decision_date.desc()),
    )

    def __repr__(self):
        return f"<Precedent {self.case_number} - {self.title[:30]}>"
