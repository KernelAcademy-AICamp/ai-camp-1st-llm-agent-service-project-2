"""
Response Cache 테스트

Phase 5: Adaptive Agent - 캐싱 테스트
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from apps.ai_service.agents.cache.response_cache import (
    ResponseCache,
    generate_cache_key,
    CacheConfig,
)


class TestCacheKeyGeneration:
    """캐시 키 생성 테스트"""

    def test_same_message_same_key(self):
        """동일 메시지는 동일 키"""
        key1 = generate_cache_key("절도죄 형량은?", "org1")
        key2 = generate_cache_key("절도죄 형량은?", "org1")
        assert key1 == key2

    def test_different_org_different_key(self):
        """다른 조직은 다른 키"""
        key1 = generate_cache_key("절도죄 형량은?", "org1")
        key2 = generate_cache_key("절도죄 형량은?", "org2")
        assert key1 != key2

    def test_case_insensitive(self):
        """대소문자 무시"""
        key1 = generate_cache_key("HELLO", "org1")
        key2 = generate_cache_key("hello", "org1")
        assert key1 == key2

    def test_attachments_affect_key(self):
        """첨부 파일이 키에 영향"""
        key1 = generate_cache_key("분석해줘", "org1", [{"filename": "a.pdf"}])
        key2 = generate_cache_key("분석해줘", "org1", [{"filename": "b.pdf"}])
        assert key1 != key2

    def test_no_org_uses_default(self):
        """조직 ID 없으면 default 사용"""
        key = generate_cache_key("테스트", None)
        assert "default" in key

    def test_key_format(self):
        """키 형식 확인"""
        key = generate_cache_key("테스트", "org1")
        assert key.startswith(CacheConfig.KEY_PREFIX)
        assert "org1" in key

    def test_whitespace_normalized(self):
        """공백 정규화"""
        key1 = generate_cache_key("  테스트  ", "org1")
        key2 = generate_cache_key("테스트", "org1")
        assert key1 == key2

    def test_multiple_attachments_sorted(self):
        """여러 첨부 파일은 정렬됨"""
        key1 = generate_cache_key("분석해줘", "org1", [
            {"filename": "b.pdf"},
            {"filename": "a.pdf"}
        ])
        key2 = generate_cache_key("분석해줘", "org1", [
            {"filename": "a.pdf"},
            {"filename": "b.pdf"}
        ])
        assert key1 == key2


class TestResponseCache:
    """ResponseCache 테스트"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis fixture"""
        mock = MagicMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=True)
        mock.scan_iter = MagicMock(return_value=iter([]))
        mock.close = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_cache_miss(self, mock_redis):
        """캐시 미스"""
        cache = ResponseCache()
        cache._redis = mock_redis
        cache._connected = True

        result = await cache.get("test_key")

        assert result is None
        assert cache._misses == 1
        assert cache._hits == 0

    @pytest.mark.asyncio
    async def test_cache_hit(self, mock_redis):
        """캐시 히트"""
        cache = ResponseCache()
        cache._redis = mock_redis
        cache._connected = True

        mock_redis.get = AsyncMock(return_value='{"response": "cached", "path": "fast"}')

        result = await cache.get("test_key")

        assert result is not None
        assert result["response"] == "cached"
        assert cache._hits == 1
        assert cache._misses == 0

    @pytest.mark.asyncio
    async def test_set_cache(self, mock_redis):
        """캐시 저장"""
        cache = ResponseCache()
        cache._redis = mock_redis
        cache._connected = True

        success = await cache.set(
            cache_key="test_key",
            response="test response",
            path="fast",
        )

        assert success is True
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_ttl_by_path(self, mock_redis):
        """경로별 TTL"""
        cache = ResponseCache()
        cache._redis = mock_redis
        cache._connected = True

        # Fast path
        await cache.set("key1", "response", path="fast")
        call_args = mock_redis.set.call_args
        assert call_args.kwargs.get("ex") == CacheConfig.TTL_FAST_PATH

        mock_redis.set.reset_mock()

        # Medium path
        await cache.set("key2", "response", path="medium")
        call_args = mock_redis.set.call_args
        assert call_args.kwargs.get("ex") == CacheConfig.TTL_MEDIUM_PATH

        mock_redis.set.reset_mock()

        # Deep path
        await cache.set("key3", "response", path="deep")
        call_args = mock_redis.set.call_args
        assert call_args.kwargs.get("ex") == CacheConfig.TTL_DEEP_PATH

    @pytest.mark.asyncio
    async def test_max_response_size(self, mock_redis):
        """최대 응답 크기 제한"""
        cache = ResponseCache()
        cache._redis = mock_redis
        cache._connected = True

        # 너무 큰 응답
        large_response = "x" * (CacheConfig.MAX_RESPONSE_SIZE + 1)
        success = await cache.set("key", large_response, path="fast")

        assert success is False
        mock_redis.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_cache(self, mock_redis):
        """캐시 삭제"""
        cache = ResponseCache()
        cache._redis = mock_redis
        cache._connected = True

        success = await cache.delete("test_key")

        assert success is True
        mock_redis.delete.assert_called_once_with("test_key")

    def test_hit_rate_calculation(self):
        """히트율 계산"""
        cache = ResponseCache()
        cache._hits = 3
        cache._misses = 7

        assert cache.hit_rate == 0.3

    def test_hit_rate_zero_total(self):
        """총 요청 0일 때 히트율"""
        cache = ResponseCache()
        cache._hits = 0
        cache._misses = 0

        assert cache.hit_rate == 0.0

    def test_get_stats(self):
        """통계 조회"""
        cache = ResponseCache()
        cache._hits = 5
        cache._misses = 10
        cache._connected = True

        stats = cache.get_stats()

        assert stats["hits"] == 5
        assert stats["misses"] == 10
        assert stats["hit_rate"] == pytest.approx(0.333, rel=0.01)
        assert stats["connected"] is True

    @pytest.mark.asyncio
    async def test_cache_with_metadata(self, mock_redis):
        """메타데이터 포함 캐싱"""
        cache = ResponseCache()
        cache._redis = mock_redis
        cache._connected = True

        metadata = {"intent": "QUERY", "workflow": "rag_workflow"}
        success = await cache.set(
            cache_key="test_key",
            response="test response",
            path="medium",
            metadata=metadata,
        )

        assert success is True

        # 저장된 데이터 확인
        call_args = mock_redis.set.call_args
        import json
        saved_data = json.loads(call_args.args[1])
        assert saved_data["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_no_redis_connection(self):
        """Redis 연결 없을 때 - get은 None 반환"""
        cache = ResponseCache()
        cache._connected = False
        cache._redis = None

        # _ensure_connection이 호출되지 않도록 패치
        with patch.object(cache, '_ensure_connection', new_callable=AsyncMock):
            result = await cache.get("test_key")
            assert result is None


class TestCacheIntegration:
    """통합 테스트"""

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis fixture for integration tests"""
        mock = MagicMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=True)
        mock.scan_iter = MagicMock(return_value=iter([]))
        mock.close = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_cache_flow(self, mock_redis):
        """캐시 저장 → 조회 흐름"""
        cache = ResponseCache()
        cache._redis = mock_redis
        cache._connected = True

        # 저장
        await cache.set("key1", "response1", "fast")

        # Mock 반환값 설정
        mock_redis.get = AsyncMock(return_value='{"response": "response1", "path": "fast", "cached_at": "2024-01-01"}')

        # 조회
        result = await cache.get("key1")

        assert result is not None
        assert result["response"] == "response1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
