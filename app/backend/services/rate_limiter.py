"""
Rate Limiter for API requests
요청 간 최소 시간 간격을 보장하는 Rate Limiter
"""

import time
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter to prevent excessive requests

    Features:
    - Enforces minimum interval between requests
    - Thread-safe with asyncio
    - Prevents infinite loops
    """

    def __init__(self, min_interval: float = 1.0):
        """
        Initialize rate limiter

        Args:
            min_interval: Minimum time interval between requests (seconds)
        """
        self.min_interval = min_interval
        self.last_request_time: float = 0
        self._lock = asyncio.Lock()

    async def wait(self) -> None:
        """
        Wait until enough time has passed since last request
        Thread-safe with async lock
        """
        async with self._lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time

            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)

            self.last_request_time = time.time()
            logger.debug(f"Rate limiter: request allowed at {self.last_request_time}")

    def sync_wait(self) -> None:
        """
        Synchronous version of wait() for non-async contexts
        """
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        if elapsed < self.min_interval:
            wait_time = self.min_interval - elapsed
            logger.debug(f"Rate limiting (sync): waiting {wait_time:.2f}s")
            time.sleep(wait_time)

        self.last_request_time = time.time()
        logger.debug(f"Rate limiter (sync): request allowed at {self.last_request_time}")


class RequestCounter:
    """
    Counter to prevent excessive consecutive requests
    """

    def __init__(self, max_requests: int = 10):
        """
        Initialize request counter

        Args:
            max_requests: Maximum number of consecutive requests allowed
        """
        self.max_requests = max_requests
        self.request_count = 0
        self._lock = asyncio.Lock()

    async def increment(self) -> bool:
        """
        Increment request counter

        Returns:
            True if request is allowed, False if limit exceeded
        """
        async with self._lock:
            if self.request_count >= self.max_requests:
                logger.warning(f"Request limit exceeded: {self.request_count}/{self.max_requests}")
                return False

            self.request_count += 1
            logger.debug(f"Request count: {self.request_count}/{self.max_requests}")
            return True

    async def reset(self) -> None:
        """Reset the counter"""
        async with self._lock:
            logger.debug(f"Resetting request counter (was {self.request_count})")
            self.request_count = 0

    def get_count(self) -> int:
        """Get current request count"""
        return self.request_count
