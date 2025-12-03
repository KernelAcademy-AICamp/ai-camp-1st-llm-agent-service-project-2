"""SQLAlchemy models for Agent Hub persistent entities."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from .database import Base


def _utc_now():
    """UTC 타임존이 포함된 현재 시간 반환"""
    return datetime.now(timezone.utc)


class AgentHubSession(Base):
    __tablename__ = 'agent_hub_sessions'

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(PG_UUID(as_uuid=True), unique=True, nullable=False, index=True)
    user_id = Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    organization_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)
    project_id = Column(PG_UUID(as_uuid=True), nullable=True, index=True)

    title = Column(String(255), default='', nullable=False)
    last_message_preview = Column(String(500), default='', nullable=False)

    created_at = Column(DateTime(timezone=True), default=_utc_now)
    last_activity = Column(DateTime(timezone=True), default=_utc_now, index=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)

    total_messages = Column(Integer, default=0)
    total_workflows_executed = Column(Integer, default=0)
    metadata_json = Column('metadata', JSON, default=dict)

    messages = relationship('AgentHubMessage', back_populates='session', lazy='selectin')


class AgentHubMessage(Base):
    __tablename__ = 'agent_hub_messages'

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(
        PG_UUID(as_uuid=True),
        ForeignKey('agent_hub_sessions.session_id', ondelete='CASCADE'),
        nullable=False,
        index=True,
    )
    role = Column(String(20), nullable=False)
    content = Column(String, nullable=False)
    metadata_json = Column('metadata', JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_utc_now, index=True)

    session = relationship('AgentHubSession', back_populates='messages', lazy='joined')
