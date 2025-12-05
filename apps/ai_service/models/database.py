"""
Database Connection
Django와 동일한 PostgreSQL 공유 (또는 SQLite for development)
- 기본: 읽기 전용
- 크롤러: 쓰기 가능
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

# SQLite 사용 여부 (개발 환경용)
USE_SQLITE = os.getenv("USE_SQLITE", "True") == "True"

if USE_SQLITE:
    # SQLite for development
    BASE_DIR = Path(__file__).resolve().parent.parent
    SQLITE_PATH = BASE_DIR / "db.sqlite3"
    DATABASE_URL = f"sqlite+aiosqlite:///{SQLITE_PATH}"

    # SQLite 엔진 (Read/Write 모두 동일)
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )
    write_engine = engine  # SQLite에서는 동일 엔진 사용
else:
    # PostgreSQL for production
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://myidwon:@localhost:5432/lawlaw"
    )

    # Read-Only 엔진 생성 (기본)
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,  # SQL 로그 비활성화 (프로덕션)
        pool_pre_ping=True,  # 연결 상태 확인
        pool_size=5,  # 읽기 전용이므로 작게
        max_overflow=10,
        # Read-Only 트랜잭션 격리 수준
        isolation_level="READ COMMITTED"
    )

    # Write 가능 엔진 (크롤러용)
    write_engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=3,  # 크롤러용 작은 풀
        max_overflow=5,
        isolation_level="READ COMMITTED"
    )

# AsyncSession factory (Read-Only)
async_session = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# AsyncSession factory (Write)
write_async_session = sessionmaker(
    write_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# SQLAlchemy Base
Base = declarative_base()

async def get_db():
    """
    DB 세션 의존성 (Read-Only)

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


async def get_write_db():
    """
    DB 세션 의존성 (Write 가능 - 크롤러용)

    Usage:
        @router.post("/crawler/...")
        async def crawler_endpoint(db: AsyncSession = Depends(get_write_db)):
            ...
    """
    async with write_async_session() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database write session error: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()

async def init_db():
    """
    DB 초기화
    - SQLite (개발 환경): 테이블 자동 생성
    - PostgreSQL (프로덕션): Django migrations에서 수행
    """
    async with engine.begin() as conn:
        if USE_SQLITE:
            # SQLite에서는 테이블 자동 생성
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Database initialized (SQLite) - tables created")
        else:
            # PostgreSQL에서는 Read-Only (Django migrations 사용)
            logger.info("✅ Database connection initialized (Read-Only PostgreSQL)")

async def close_db():
    """DB 연결 종료"""
    await engine.dispose()
    await write_engine.dispose()
    logger.info("👋 Database connections closed")
