"""
Database Connection (Read-Only)
Django와 동일한 PostgreSQL 공유, 읽기 전용
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os
import logging

logger = logging.getLogger(__name__)

# 환경변수에서 DATABASE_URL 가져오기
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://myidwon:@localhost:5432/lawlaw"
)

# Read-Only 엔진 생성
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # SQL 로그 비활성화 (프로덕션)
    pool_pre_ping=True,  # 연결 상태 확인
    pool_size=5,  # 읽기 전용이므로 작게
    max_overflow=10,
    # Read-Only 트랜잭션 격리 수준
    isolation_level="READ COMMITTED"
)

# AsyncSession factory
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# SQLAlchemy Base
Base = declarative_base()

async def get_db():
    """
    DB 세션 의존성

    Usage:
        @router.get("/example")
        async def example(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """
    DB 초기화 (테스트용)
    실제 테이블 생성은 Django migrations에서 수행
    """
    async with engine.begin() as conn:
        # 테이블은 생성하지 않음 (Read-Only)
        logger.info("✅ Database connection initialized (Read-Only PostgreSQL)")

async def close_db():
    """DB 연결 종료"""
    await engine.dispose()
    logger.info("👋 Database connection closed")
