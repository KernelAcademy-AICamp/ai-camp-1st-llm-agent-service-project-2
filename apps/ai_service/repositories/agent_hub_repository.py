"""Persistence helpers for Agent Hub sessions and messages."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


def _utc_now():
    """UTC 타임존이 포함된 현재 시간 반환"""
    return datetime.now(timezone.utc)

from sqlalchemy import Select, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from apps.ai_service.models.agent_hub import AgentHubMessage, AgentHubSession
from apps.ai_service.models.database import async_session, write_async_session
from loguru import logger


def _to_uuid(value: Optional[str]) -> Optional[uuid.UUID]:
    if not value:
        return None
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        logger.warning(f"Invalid UUID value: {value}")
        return None


async def ensure_session_record(
    session_id: str,
    user_id: str,
    organization_id: Optional[str] = None,
    project_id: Optional[str] = None,
    title: str | None = None,
) -> None:
    session_uuid = _to_uuid(session_id)
    user_uuid = _to_uuid(user_id)
    if not session_uuid or not user_uuid:
        return

    values = {
        'session_id': session_uuid,
        'user_id': user_uuid,
        'organization_id': _to_uuid(organization_id),
        'project_id': _to_uuid(project_id),
        'title': title or '',
        'last_activity': _utc_now(),
    }

    async with write_async_session() as db:
        stmt = (
            insert(AgentHubSession)
            .values(**values)
            .on_conflict_do_update(
                index_elements=[AgentHubSession.session_id],
                set_={
                    'organization_id': values['organization_id'],
                    'project_id': values['project_id'],
                    'last_activity': values['last_activity'],
                    'title': func.coalesce(AgentHubSession.title, values['title']),
                }
            )
        )
        try:
            await db.execute(stmt)
            await db.commit()
        except SQLAlchemyError as exc:
            logger.warning(f"Failed to upsert agent hub session: {exc}")
            await db.rollback()


async def update_session_metadata(session_id: str, updates: Dict[str, Any]) -> None:
    session_uuid = _to_uuid(session_id)
    if not session_uuid or not updates:
        return

    normalized: Dict[str, Any] = {}
    for key, value in updates.items():
        if key in {"organization_id", "project_id", "user_id"}:
            normalized[key] = _to_uuid(value) if value else None
        else:
            normalized[key] = value

    async with write_async_session() as db:
        stmt = (
            update(AgentHubSession)
            .where(AgentHubSession.session_id == session_uuid)
            .values(**normalized)
        )
        try:
            await db.execute(stmt)
            await db.commit()
        except SQLAlchemyError as exc:
            logger.warning(f"Failed to update session metadata: {exc}")
            await db.rollback()


async def record_message(
    session_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None,
    title_hint: Optional[str] = None,
) -> None:
    session_uuid = _to_uuid(session_id)
    if not session_uuid:
        return

    now = _utc_now()
    async with write_async_session() as db:
        message = AgentHubMessage(
            session_id=session_uuid,
            role=role,
            content=content,
            metadata_json=metadata or {},
            created_at=now,
        )
        db.add(message)
        stmt = (
            update(AgentHubSession)
            .where(AgentHubSession.session_id == session_uuid)
            .values(
                total_messages=AgentHubSession.total_messages + 1,
                last_activity=now,
                last_message_preview=content[:500],
            )
        )
        try:
            await db.execute(stmt)
            if title_hint:
                await db.execute(
                    update(AgentHubSession)
                    .where(AgentHubSession.session_id == session_uuid, AgentHubSession.title == '')
                    .values(title=title_hint[:255])
                )
            await db.commit()
        except SQLAlchemyError as exc:
            logger.warning(f"Failed to record message: {exc}")
            await db.rollback()


async def fetch_session_history(
    session_id: str,
    limit: int = 50,
) -> Tuple[List[Dict[str, Any]], int]:
    session_uuid = _to_uuid(session_id)
    if not session_uuid:
        return [], 0

    async with async_session() as db:
        stmt: Select = (
            select(AgentHubMessage)
            .where(AgentHubMessage.session_id == session_uuid)
            .order_by(AgentHubMessage.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        messages = list(result.scalars())

        count_stmt = select(func.count()).select_from(AgentHubMessage).where(
            AgentHubMessage.session_id == session_uuid
        )
        total = (await db.execute(count_stmt)).scalar_one()

    messages.reverse()
    serialized = [
        {
            'role': msg.role,
            'content': msg.content,
            'timestamp': msg.created_at.isoformat(),
            'metadata': msg.metadata_json or {},
        }
        for msg in messages
    ]
    return serialized, total


async def list_user_sessions(
    user_id: str,
    page: int = 1,
    page_size: int = 20,
    project_id: Optional[str] = None,
) -> Tuple[List[AgentHubSession], int]:
    user_uuid = _to_uuid(user_id)
    if not user_uuid:
        return [], 0

    offset = max(page - 1, 0) * page_size

    async with async_session() as db:
        stmt = (
            select(AgentHubSession)
            .where(AgentHubSession.user_id == user_uuid)
            .order_by(AgentHubSession.last_activity.desc())
            .offset(offset)
            .limit(page_size)
        )
        if project_id:
            stmt = stmt.where(AgentHubSession.project_id == _to_uuid(project_id))
        result = await db.execute(stmt)
        sessions = list(result.scalars())

        total_stmt = select(func.count()).select_from(AgentHubSession).where(
            AgentHubSession.user_id == user_uuid
        )
        if project_id:
            total_stmt = total_stmt.where(AgentHubSession.project_id == _to_uuid(project_id))
        total = (await db.execute(total_stmt)).scalar_one()

    return sessions, total


async def delete_session_record(session_id: str) -> None:
    session_uuid = _to_uuid(session_id)
    if not session_uuid:
        return

    async with write_async_session() as db:
        stmt = AgentHubSession.__table__.delete().where(AgentHubSession.session_id == session_uuid)
        try:
            await db.execute(stmt)
            await db.commit()
        except SQLAlchemyError as exc:
            logger.warning(f"Failed to delete session record: {exc}")
            await db.rollback()


async def get_session_record(session_id: str) -> Optional[AgentHubSession]:
    session_uuid = _to_uuid(session_id)
    if not session_uuid:
        return None

    async with async_session() as db:
        stmt = select(AgentHubSession).where(AgentHubSession.session_id == session_uuid)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
