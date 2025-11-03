#!/usr/bin/env python3
"""
Database Table Creation Script for Precedents

이 스크립트는 판례(Precedent) 및 사용자(User) 테이블을 생성합니다.
애플리케이션 시작 시 자동으로 생성되지만, 수동 실행이 필요한 경우 사용하세요.

Usage:
    python scripts/create_precedent_tables.py
"""

import asyncio
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.backend.database import engine, Base
from app.backend.models.precedent import Precedent
from app.backend.models.user import User

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    """
    데이터베이스 테이블 생성

    Creates tables for:
    - precedents: 판례 데이터
    - users: 사용자 데이터
    """
    try:
        logger.info("Creating database tables...")

        async with engine.begin() as conn:
            # Drop all tables (주의: 기존 데이터가 삭제됩니다)
            # await conn.run_sync(Base.metadata.drop_all)
            # logger.info("Existing tables dropped")

            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            logger.info("✅ Tables created successfully!")

        logger.info("\nCreated tables:")
        logger.info("  - precedents (판례)")
        logger.info("  - users (사용자)")

    except Exception as e:
        logger.error(f"❌ Failed to create tables: {e}")
        raise
    finally:
        # Close engine
        await engine.dispose()


async def check_tables():
    """
    테이블 존재 여부 확인
    """
    try:
        from sqlalchemy import inspect

        async with engine.connect() as conn:
            # Inspect tables
            inspector = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn)
            )

            table_names = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_table_names()
            )

            logger.info("\nExisting tables in database:")
            if table_names:
                for table in table_names:
                    logger.info(f"  - {table}")
            else:
                logger.info("  (No tables found)")

            return table_names

    except Exception as e:
        logger.error(f"Failed to check tables: {e}")
        return []


async def main():
    """
    메인 실행 함수
    """
    logger.info("=" * 60)
    logger.info("LawLaw Database Table Creation Script")
    logger.info("=" * 60)
    logger.info("")

    # 기존 테이블 확인
    logger.info("Step 1: Checking existing tables...")
    existing_tables = await check_tables()
    logger.info("")

    # 테이블 생성
    logger.info("Step 2: Creating tables...")
    await create_tables()
    logger.info("")

    # 생성 결과 확인
    logger.info("Step 3: Verifying created tables...")
    await check_tables()
    logger.info("")

    logger.info("=" * 60)
    logger.info("✅ Database setup completed successfully!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Add your OPENLAW_API_KEY to .env file")
    logger.info("2. Start the backend server: cd app/backend && uvicorn main:app --reload")
    logger.info("3. Access the API at http://localhost:8000")
    logger.info("4. Start the frontend: cd app/frontend && npm start")
    logger.info("")


if __name__ == "__main__":
    asyncio.run(main())
