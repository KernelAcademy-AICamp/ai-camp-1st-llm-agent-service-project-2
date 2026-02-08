"""
Conversation Service - Redis 기반 대화 기록 관리

Agent Hub의 세션별 대화 기록을 관리하는 서비스입니다.
설계 문서: docs/AGENT_HUB_BACKEND_INTEGRATION.md - 6.2 대화 기록 서비스

주요 기능:
- 메시지 추가 (user/assistant)
- 대화 기록 조회 (최근 N개)
- 대화 기록 삭제
- 최대 50개 메시지 유지 (LTRIM)
- 24시간 TTL
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List

import redis
from loguru import logger

from apps.ai_service.config.settings import settings
from apps.ai_service.repositories.agent_hub_repository import record_message as persist_message


class ConversationService:
    """
    Redis 기반 대화 기록 관리 서비스

    Redis Key 패턴:
    - conversation:{session_id} : 대화 메시지 리스트 (LPUSH/LRANGE)

    메시지 구조:
    {
        "role": "user" | "assistant",
        "content": "메시지 내용",
        "timestamp": "ISO 8601 datetime",
        "metadata": {
            "intent": {...},
            "workflows_used": [...],
            "execution_time": float,
            ...
        }
    }
    """

    # 상수 정의
    MAX_CONVERSATION_LENGTH = 50  # 최대 50개 메시지 유지
    CONVERSATION_TTL_SECONDS = 24 * 60 * 60  # 24시간 TTL

    def __init__(self):
        """Redis 클라이언트 초기화"""
        self._redis_client: Optional[redis.Redis] = None

    @property
    def redis_client(self) -> redis.Redis:
        """지연 초기화된 Redis 클라이언트 반환"""
        if self._redis_client is None:
            try:
                self._redis_client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    db=settings.REDIS_DB,
                    password=settings.REDIS_PASSWORD or None,
                    decode_responses=True,  # 문자열로 자동 디코딩
                    socket_timeout=5,
                    socket_connect_timeout=5,
                )
                # 연결 테스트
                self._redis_client.ping()
                logger.info(
                    f"ConversationService Redis 연결 성공: "
                    f"{settings.REDIS_HOST}:{settings.REDIS_PORT}"
                )
            except redis.ConnectionError as e:
                logger.error(f"ConversationService Redis 연결 실패: {e}")
                raise
        return self._redis_client

    def _get_conversation_key(self, session_id: str) -> str:
        """대화 Redis 키 생성"""
        return f"conversation:{session_id}"

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        대화 메시지 추가

        Args:
            session_id: 세션 UUID
            role: 메시지 역할 ("user" 또는 "assistant")
            content: 메시지 내용
            metadata: 추가 메타데이터 (워크플로우 정보 등)

        Returns:
            성공 여부

        Raises:
            ValueError: role이 유효하지 않은 경우
        """
        # role 검증
        if role not in ("user", "assistant"):
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'")

        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        try:
            key = self._get_conversation_key(session_id)

            # 리스트 끝에 메시지 추가 (RPUSH)
            self.redis_client.rpush(key, json.dumps(message, ensure_ascii=False))

            # 최대 길이 제한 (최근 50개만 유지)
            # LTRIM key start stop: start부터 stop까지만 유지
            # -50부터 -1까지 = 마지막 50개만 유지
            self.redis_client.ltrim(key, -self.MAX_CONVERSATION_LENGTH, -1)

            # TTL 설정 (24시간) - 메시지 추가 시마다 TTL 갱신
            self.redis_client.expire(key, self.CONVERSATION_TTL_SECONDS)

            logger.debug(
                f"메시지 추가: session_id={session_id}, role={role}, "
                f"content_length={len(content)}"
            )
            return True

        except redis.RedisError as e:
            logger.error(
                f"메시지 추가 실패: session_id={session_id}, role={role}, error={e}"
            )
            return False

    async def get_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        대화 기록 조회

        Args:
            session_id: 세션 UUID
            limit: 조회할 메시지 수 (기본: 10, 최대: MAX_CONVERSATION_LENGTH)

        Returns:
            메시지 리스트 (시간순 - 오래된 것부터)
        """
        try:
            key = self._get_conversation_key(session_id)

            # limit 값 검증
            limit = min(limit, self.MAX_CONVERSATION_LENGTH)

            # 최근 N개 메시지 조회
            # LRANGE key -limit -1: 마지막 limit개 조회
            messages_json = self.redis_client.lrange(key, -limit, -1)

            messages = []
            for msg_json in messages_json:
                try:
                    messages.append(json.loads(msg_json))
                except json.JSONDecodeError as e:
                    logger.warning(f"메시지 파싱 실패: {e}")
                    continue

            logger.debug(
                f"대화 기록 조회: session_id={session_id}, "
                f"limit={limit}, returned={len(messages)}"
            )
            return messages

        except redis.RedisError as e:
            logger.error(
                f"대화 기록 조회 실패: session_id={session_id}, error={e}"
            )
            return []

    async def get_full_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        전체 대화 기록 조회

        Args:
            session_id: 세션 UUID

        Returns:
            전체 메시지 리스트 (시간순)
        """
        return await self.get_history(session_id, limit=self.MAX_CONVERSATION_LENGTH)

    async def clear_history(self, session_id: str) -> bool:
        """
        대화 기록 삭제

        Args:
            session_id: 세션 UUID

        Returns:
            성공 여부
        """
        try:
            key = self._get_conversation_key(session_id)
            result = self.redis_client.delete(key)

            logger.info(f"대화 기록 삭제: session_id={session_id}, deleted={result > 0}")
            return result > 0

        except redis.RedisError as e:
            logger.error(
                f"대화 기록 삭제 실패: session_id={session_id}, error={e}"
            )
            return False

    async def get_message_count(self, session_id: str) -> int:
        """
        대화 메시지 수 조회

        Args:
            session_id: 세션 UUID

        Returns:
            메시지 수
        """
        try:
            key = self._get_conversation_key(session_id)
            return self.redis_client.llen(key)

        except redis.RedisError as e:
            logger.error(
                f"메시지 수 조회 실패: session_id={session_id}, error={e}"
            )
            return 0

    async def get_last_message(
        self,
        session_id: str,
        role: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        마지막 메시지 조회

        Args:
            session_id: 세션 UUID
            role: 특정 역할의 마지막 메시지만 조회 (선택)

        Returns:
            마지막 메시지 또는 None
        """
        try:
            if role is None:
                # 역할 무관 마지막 메시지
                history = await self.get_history(session_id, limit=1)
                return history[-1] if history else None

            # 특정 역할의 마지막 메시지 찾기
            history = await self.get_history(session_id, limit=self.MAX_CONVERSATION_LENGTH)
            for msg in reversed(history):
                if msg.get("role") == role:
                    return msg

            return None

        except Exception as e:
            logger.error(
                f"마지막 메시지 조회 실패: session_id={session_id}, error={e}"
            )
            return None

    async def get_conversation_summary(self, session_id: str) -> Dict[str, Any]:
        """
        대화 요약 정보 조회

        Args:
            session_id: 세션 UUID

        Returns:
            요약 정보 딕셔너리
        """
        try:
            history = await self.get_full_history(session_id)

            user_messages = [m for m in history if m.get("role") == "user"]
            assistant_messages = [m for m in history if m.get("role") == "assistant"]

            # 첫 번째와 마지막 메시지 시간
            first_timestamp = history[0].get("timestamp") if history else None
            last_timestamp = history[-1].get("timestamp") if history else None

            # 사용된 워크플로우 수집
            workflows_used = set()
            total_execution_time = 0.0

            for msg in assistant_messages:
                metadata = msg.get("metadata", {})
                if "workflows_used" in metadata:
                    workflows_used.update(metadata["workflows_used"])
                if "execution_time" in metadata:
                    total_execution_time += metadata["execution_time"]

            return {
                "session_id": session_id,
                "total_messages": len(history),
                "user_messages": len(user_messages),
                "assistant_messages": len(assistant_messages),
                "first_message_at": first_timestamp,
                "last_message_at": last_timestamp,
                "workflows_used": list(workflows_used),
                "total_execution_time": round(total_execution_time, 2)
            }

        except Exception as e:
            logger.error(
                f"대화 요약 조회 실패: session_id={session_id}, error={e}"
            )
            return {
                "session_id": session_id,
                "total_messages": 0,
                "error": str(e)
            }

    def is_connected(self) -> bool:
        """Redis 연결 상태 확인"""
        try:
            self.redis_client.ping()
            return True
        except (redis.ConnectionError, redis.RedisError):
            return False

    def close(self):
        """Redis 연결 종료"""
        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None
            logger.info("ConversationService Redis 연결 종료")


# 싱글톤 인스턴스
_conversation_service: Optional[ConversationService] = None


def get_conversation_service() -> ConversationService:
    """
    ConversationService 싱글톤 인스턴스 반환

    Usage:
        conversation_service = get_conversation_service()
        await conversation_service.add_message(
            session_id="...",
            role="user",
            content="안녕하세요"
        )
    """
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service


async def add_user_message(
    session_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    헬퍼 함수: 사용자 메시지 추가

    Args:
        session_id: 세션 UUID
        content: 메시지 내용
        metadata: 추가 메타데이터

    Returns:
        성공 여부
    """
    service = get_conversation_service()
    result = await service.add_message(
        session_id=session_id,
        role="user",
        content=content,
        metadata=metadata
    )
    await persist_message(
        session_id=session_id,
        role="user",
        content=content,
        metadata=metadata,
        title_hint=content,
    )
    return result


async def add_assistant_message(
    session_id: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    헬퍼 함수: 어시스턴트 메시지 추가

    Args:
        session_id: 세션 UUID
        content: 메시지 내용
        metadata: 추가 메타데이터 (워크플로우 정보, 실행 시간 등)

    Returns:
        성공 여부
    """
    service = get_conversation_service()
    result = await service.add_message(
        session_id=session_id,
        role="assistant",
        content=content,
        metadata=metadata
    )
    await persist_message(
        session_id=session_id,
        role="assistant",
        content=content,
        metadata=metadata,
    )
    return result


async def get_conversation_history(
    session_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    헬퍼 함수: 대화 기록 조회

    Args:
        session_id: 세션 UUID
        limit: 조회할 메시지 수

    Returns:
        메시지 리스트
    """
    service = get_conversation_service()
    return await service.get_history(session_id, limit=limit)
