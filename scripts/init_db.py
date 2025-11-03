#!/usr/bin/env python3
"""
Database initialization script
Creates all tables defined in SQLAlchemy models
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.backend.database import engine, Base
from app.backend.models.user import User  # Import all models here


async def init_db():
    """Initialize database tables"""
    print("🔧 Initializing database...")
    print(f"📁 Database location: {project_root}/data/lawlaw.db")

    async with engine.begin() as conn:
        # Drop all tables (optional - comment out for production)
        # await conn.run_sync(Base.metadata.drop_all)
        # print("🗑️  Dropped existing tables")

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Created tables:")
        for table in Base.metadata.tables:
            print(f"   - {table}")

    print("✨ Database initialization complete!")


async def create_test_user():
    """Create a test user for development"""
    from app.backend.database import async_session
    from app.backend.core.auth.jwt import hash_password

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
    asyncio.run(init_db())

    # Optionally create test user
    import os

    if os.getenv("CREATE_TEST_USER", "true").lower() == "true":
        asyncio.run(create_test_user())
