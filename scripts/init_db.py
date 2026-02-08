#!/usr/bin/env python3
"""
Database initialization script
Creates all tables defined in SQLAlchemy models
"""

import asyncio
import sys
from pathlib import Path
import time
import json
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from apps.backend.database import engine, Base
from apps.backend.models.user import User
from apps.backend.models.precedent import Precedent
from apps.backend.models.precedent_feedback import PrecedentFeedback


async def init_db():
    """Initialize database tables"""
    start_time = time.time()
    timing_metrics = {}

    print("🔧 Initializing database...")
    print(f"📁 Database location: {project_root}/data/lawlaw.db")

    create_start = time.time()
    async with engine.begin() as conn:
        # Drop all tables (optional - comment out for production)
        # await conn.run_sync(Base.metadata.drop_all)
        # print("🗑️  Dropped existing tables")

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Created tables:")
        for table in Base.metadata.tables:
            print(f"   - {table}")

    timing_metrics['table_creation_time'] = time.time() - create_start
    timing_metrics['total_time'] = time.time() - start_time
    timing_metrics['timestamp'] = datetime.now().isoformat()
    timing_metrics['tables_created'] = list(Base.metadata.tables.keys())

    print(f"✨ Database initialization complete in {timing_metrics['total_time']:.2f}s!")

    return timing_metrics


async def create_test_user():
    """Create a test user for development"""
    from apps.backend.database import async_session
    from apps.backend.core.auth.jwt import hash_password

    async with async_session() as session:
        # Check if test user already exists
        from sqlalchemy import select

        result = await session.execute(select(User).where(User.email == "test@lawlaw.com"))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            print("ℹ️  Test user already exists")
            return

        # Create test user
        test_user = User(
            email="test@lawlaw.com",
            hashed_password=hash_password("test1234"),
            full_name="김변호사",
            lawyer_registration_number="12345",
            specializations=["형사 일반", "교통사고"],
            is_active=True,
        )

        session.add(test_user)
        await session.commit()
        print("👤 Created test user:")
        print("   Email: test@lawlaw.com")
        print("   Password: test1234")
        print("   Specializations: 형사 일반, 교통사고")


if __name__ == "__main__":
    # Run initialization
    metrics = asyncio.run(init_db())

    # Optionally create test user
    import os

    user_start = time.time()
    if os.getenv("CREATE_TEST_USER", "true").lower() == "true":
        asyncio.run(create_test_user())
    metrics['test_user_creation_time'] = time.time() - user_start

    # Save metrics
    metrics_path = project_root / "data" / "pipeline_metrics" / "init_db_metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)

    with open(metrics_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)

    print(f"\n📊 Metrics saved to: {metrics_path}")