"""
SQLite → PostgreSQL 데이터 마이그레이션 스크립트 (UUID 변환 지원)

⚠️ 주요 변경사항:
- SQLite의 하이픈 없는 UUID (32자) → PostgreSQL UUID (36자, 하이픈 포함) 자동 변환
- Precedent 모델의 모든 필드 지원
"""

import asyncio
import sqlite3
import uuid
import json
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
import sys
from pathlib import Path

# PYTHONPATH 설정
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from apps.backend.database import Base
from apps.backend.models.user import User
from apps.backend.models.precedent import Precedent
from apps.backend.models.precedent_feedback import PrecedentFeedback, PrecedentFeedbackStats

# PostgreSQL 연결 설정
POSTGRES_URL = "postgresql+asyncpg://myidwon:@localhost:5432/lawlaw"
SQLITE_PATH = BASE_DIR / "data" / "lawlaw.db"


def convert_uuid(uuid_str):
    """
    SQLite UUID (하이픈 없음) → PostgreSQL UUID (하이픈 있음) 변환

    Args:
        uuid_str: UUID 문자열 (32자 또는 36자)

    Returns:
        uuid.UUID 객체

    Examples:
        >>> convert_uuid("6af83a7cb62640f380605de8da4e925b")
        UUID('6af83a7c-b626-40f3-8060-5de8da4e925b')
    """
    if not uuid_str:
        return None

    uuid_str = str(uuid_str).strip()

    # 이미 하이픈이 있는 경우 (36자)
    if len(uuid_str) == 36 and '-' in uuid_str:
        return uuid.UUID(uuid_str)

    # 하이픈 없는 경우 (32자) - SQLite 형식
    if len(uuid_str) == 32:
        formatted = f"{uuid_str[:8]}-{uuid_str[8:12]}-{uuid_str[12:16]}-{uuid_str[16:20]}-{uuid_str[20:]}"
        return uuid.UUID(formatted)

    # 그 외의 경우 그대로 시도
    return uuid.UUID(uuid_str)


async def create_tables():
    """PostgreSQL에 테이블 생성"""
    print("📋 Creating tables in PostgreSQL...")

    engine = create_async_engine(POSTGRES_URL, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await engine.dispose()
    print("✅ Tables created successfully")


def load_sqlite_data():
    """SQLite에서 데이터 로드"""
    print(f"📂 Loading data from SQLite: {SQLITE_PATH}")

    if not SQLITE_PATH.exists():
        print(f"❌ SQLite database not found: {SQLITE_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(SQLITE_PATH)
    conn.row_factory = sqlite3.Row

    data = {
        'users': [],
        'precedents': [],
        'precedent_feedback': [],
        'precedent_feedback_stats': []
    }

    # Users
    cursor = conn.execute("SELECT * FROM users")
    for row in cursor.fetchall():
        data['users'].append(dict(row))

    # Precedents
    cursor = conn.execute("SELECT * FROM precedents")
    for row in cursor.fetchall():
        data['precedents'].append(dict(row))

    # Precedent Feedback
    try:
        cursor = conn.execute("SELECT * FROM precedent_feedback")
        for row in cursor.fetchall():
            data['precedent_feedback'].append(dict(row))
    except:
        pass

    # Precedent Feedback Stats
    try:
        cursor = conn.execute("SELECT * FROM precedent_feedback_stats")
        for row in cursor.fetchall():
            data['precedent_feedback_stats'].append(dict(row))
    except:
        pass

    conn.close()

    print(f"✅ Loaded {len(data['users'])} users")
    print(f"✅ Loaded {len(data['precedents'])} precedents")
    print(f"✅ Loaded {len(data['precedent_feedback'])} precedent_feedback")
    print(f"✅ Loaded {len(data['precedent_feedback_stats'])} precedent_feedback_stats")

    return data


async def migrate_data(data):
    """PostgreSQL에 데이터 삽입"""
    print("📤 Migrating data to PostgreSQL...")

    engine = create_async_engine(POSTGRES_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Users 마이그레이션
            for user_data in data['users']:
                user = User(
                    id=convert_uuid(user_data['id']),  # ✅ UUID 변환 함수 사용
                    email=user_data['email'],
                    hashed_password=user_data['hashed_password'],
                    full_name=user_data['full_name'],
                    lawyer_registration_number=user_data.get('lawyer_registration_number'),
                    specializations=user_data.get('specializations', []),
                    is_active=bool(user_data['is_active']),
                    created_at=datetime.fromisoformat(user_data['created_at']) if isinstance(user_data['created_at'], str) else user_data['created_at'],
                    updated_at=datetime.fromisoformat(user_data['updated_at']) if isinstance(user_data['updated_at'], str) else user_data['updated_at']
                )
                session.add(user)

            # Precedents 마이그레이션
            for prec_data in data['precedents']:
                # ✅ JSON 필드 파싱 (SQLite는 문자열로 저장, PostgreSQL JSONList는 list 필요)
                def parse_json_field(value, default=[]):
                    if isinstance(value, str):
                        try:
                            return json.loads(value)
                        except:
                            return default
                    return value if value is not None else default

                precedent = Precedent(
                    id=convert_uuid(prec_data['id']),  # ✅ UUID 변환 함수 사용
                    case_number=prec_data.get('case_number'),
                    title=prec_data.get('title', ''),  # ✅ title 필드 추가
                    summary=prec_data.get('summary'),
                    full_text=prec_data.get('full_text'),
                    judgment_summary=prec_data.get('judgment_summary'),  # ✅ 추가 필드
                    reference_statutes=parse_json_field(prec_data.get('reference_statutes', '[]')),  # ✅ JSON 파싱
                    reference_precedents=parse_json_field(prec_data.get('reference_precedents', '[]')),  # ✅ JSON 파싱
                    precedent_id=prec_data.get('precedent_id'),  # ✅ 추가 필드
                    court=prec_data.get('court', '대법원'),
                    decision_date=datetime.fromisoformat(prec_data['decision_date']) if prec_data.get('decision_date') and isinstance(prec_data['decision_date'], str) else prec_data.get('decision_date'),  # ✅ decision_date로 수정
                    case_type=prec_data.get('case_type', '형사'),
                    specialization_tags=parse_json_field(prec_data.get('specialization_tags', '[]')),  # ✅ JSON 파싱
                    citation=prec_data.get('citation'),  # ✅ 추가 필드
                    case_link=prec_data.get('case_link'),  # ✅ 추가 필드
                    created_at=datetime.fromisoformat(prec_data['created_at']) if isinstance(prec_data['created_at'], str) else prec_data['created_at'],
                    updated_at=datetime.fromisoformat(prec_data['updated_at']) if isinstance(prec_data['updated_at'], str) else prec_data.get('updated_at', datetime.utcnow())  # ✅ 기본값 추가
                )
                session.add(precedent)

            # Commit
            await session.commit()
            print("✅ Data migration completed successfully")

        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()  # ✅ 상세 에러 출력
            await session.rollback()
            raise
        finally:
            await session.close()

    await engine.dispose()


async def verify_migration():
    """마이그레이션 검증"""
    print("\n🔍 Verifying migration...")

    engine = create_async_engine(POSTGRES_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"  Users: {len(users)}")

        # ✅ UUID 샘플 확인
        if users:
            print(f"    Sample UUID: {users[0].id} (type: {type(users[0].id)})")

        result = await session.execute(select(Precedent))
        precedents = result.scalars().all()
        print(f"  Precedents: {len(precedents)}")

        # ✅ UUID 샘플 확인
        if precedents:
            print(f"    Sample UUID: {precedents[0].id} (type: {type(precedents[0].id)})")

        print("\n✅ Migration verification completed")

    await engine.dispose()


async def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("SQLite → PostgreSQL Migration Script")
    print("=" * 60)
    print()

    try:
        await create_tables()
        sqlite_data = load_sqlite_data()
        await migrate_data(sqlite_data)
        await verify_migration()

        print()
        print("=" * 60)
        print("✅ Migration completed successfully!")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Update .env file with PostgreSQL DATABASE_URL")
        print("2. Test apps/backend with PostgreSQL")
        print("3. Proceed to Phase 1")

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Migration failed: {e}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
