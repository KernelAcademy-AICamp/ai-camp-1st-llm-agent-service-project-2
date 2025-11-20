# Django 마이그레이션 보완 가이드

## ⚠️ DJANGO_MIGRATION_PLAN.md 보완 사항

### Phase 1과 Phase 2 사이에 추가해야 할 단계

---

## 📌 Phase 1.5: Django 전환 준비 (필수)

### 단계 1: 데이터베이스 마이그레이션 전략

#### 현재 상황
- **DB 종류**: SQLite (data/lawlaw.db, 124KB)
- **테이블**: users, precedents, precedent_feedback, precedent_feedback_stats
- **ORM**: SQLAlchemy (AsyncSession)

#### Django 전환 시 선택지

**Option A: SQLite 유지 (개발 환경)**
```python
# Django settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR.parent.parent / 'data' / 'lawlaw.db',
    }
}
```
- ✅ 기존 데이터 그대로 사용
- ✅ 추가 마이그레이션 불필요
- ⚠️ JSON 필드 제한적 지원

**Option B: PostgreSQL 전환 (권장, 프로덕션 대비)**
```bash
# 1. PostgreSQL 설치 및 DB 생성
createdb lawlaw

# 2. SQLite → PostgreSQL 데이터 이전
python manage.py dumpdata > backup.json  # SQLite에서
python manage.py loaddata backup.json    # PostgreSQL로

# 3. settings.py
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'lawlaw',
        'USER': 'postgres',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

---

### 단계 2: Django inspectdb 실행 (중요!)

**목적**: 기존 SQLAlchemy 테이블을 Django 모델로 변환

```bash
# Django 프로젝트 생성 후
cd apps/backend-api

# 기존 DB 스키마 분석
python manage.py inspectdb > temp_models.py

# 출력 예시 확인
cat temp_models.py
```

**예상 출력:**
```python
# temp_models.py (자동 생성)
class Users(models.Model):
    id = models.UUIDField(primary_key=True)
    email = models.CharField(unique=True, max_length=255)
    hashed_password = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    # ...

    class Meta:
        managed = False  # ← 중요!
        db_table = 'users'
```

**수정 사항:**
1. `managed = False` → `managed = True` (Django가 관리)
2. 클래스명 변경 (`Users` → `User`)
3. 필드 타입 정제 (`CharField` → `EmailField` 등)

---

### 단계 3: Fake Initial Migration

**목적**: 기존 테이블을 Django migrations로 관리하도록 설정 (테이블 재생성 방지)

```bash
# 1. Django 모델 작성 완료 후
python manage.py makemigrations

# 2. Fake migration 실행 (테이블 생성 건너뛰기)
python manage.py migrate --fake-initial

# 이제 Django가 스키마 관리
```

**주의:**
- `--fake-initial` 없이 `migrate` 실행하면 "테이블이 이미 존재합니다" 에러 발생
- 이 단계가 **DJANGO_MIGRATION_PLAN.md에 누락**되어 있음!

---

### 단계 4: AI Service DB 모델 간소화

**문제**: AI Service의 SQLAlchemy 모델과 Django 모델 중복

**현재 계획 (문서):**
```python
# apps/ai-service/models/precedent_feedback.py
class PrecedentFeedbackStats(Base):  # SQLAlchemy
    precedent_id = Column(String(200), primary_key=True)
    total_likes = Column(Integer, default=0)
    # ...
```

**개선 방안 (권장):**

**Option 1: Raw SQL 사용 (가장 안전)**
```python
# apps/ai-service/services/feedback_adapter.py
from sqlalchemy import text

async def get_excluded_ids(db: AsyncSession) -> Set[str]:
    """Raw SQL로 조회 (스키마 변경에 덜 민감)"""
    result = await db.execute(text(
        "SELECT precedent_id FROM precedent_feedback_stats "
        "WHERE should_exclude = true"
    ))
    return {row[0] for row in result}
```

**Option 2: 최소 모델 (필요한 컬럼만)**
```python
class PrecedentFeedbackStats(Base):
    __tablename__ = "precedent_feedback_stats"
    precedent_id = Column(String(200), primary_key=True)
    should_exclude = Column(Boolean)  # 필요한 것만

    # Django에서 추가한 새 컬럼은 무시됨 (에러는 안 남)
```

---

## 📝 수정된 Phase 2 타임라인

### Week 1-2: Django 프로젝트 생성 및 모델 변환

**Day 1-2: Django 프로젝트 초기화**
```bash
cd apps/
django-admin startproject backend_api

cd backend_api
python manage.py startapp users
python manage.py startapp cases
python manage.py startapp precedents
python manage.py startapp documents
```

**Day 3: inspectdb 실행**
```bash
# SQLite DB 경로 설정
export DATABASE_URL="sqlite:///../../data/lawlaw.db"

# 기존 스키마 분석
python manage.py inspectdb > schema_reference.py

# 모델 작성 참고용으로 사용
```

**Day 4-5: Django 모델 작성**
```python
# users/models.py
from django.contrib.auth.models import AbstractBaseUser
import uuid

class User(AbstractBaseUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    # ... (기존 컬럼 매핑)

    class Meta:
        db_table = 'users'  # 기존 테이블명 유지
```

**Day 6: Fake Migration**
```bash
python manage.py makemigrations
python manage.py migrate --fake-initial

# 검증
python manage.py shell
>>> from users.models import User
>>> User.objects.count()  # 기존 데이터 확인
```

**Day 7: AI Service 모델 간소화**
```python
# apps/ai-service/services/feedback_adapter.py
# SQLAlchemy 모델 대신 Raw SQL 사용
```

---

## ✅ 검증 체크리스트 (Phase 1.5)

- [ ] inspectdb 실행하여 스키마 확인
- [ ] Django 모델과 기존 테이블 매핑 확인
- [ ] 컬럼 타입 일치 (UUID, JSON, DATETIME)
- [ ] --fake-initial migration 성공
- [ ] Django shell에서 데이터 조회 성공
- [ ] AI Service Raw SQL로 변경
- [ ] 통합 테스트 통과

---

## 🎯 최종 마이그레이션 Flow

```
[Phase 1] AI Service 분리 (2주)
    ↓
[Phase 1.5] Django 전환 준비 (3일) ← 문서에 누락!
    - inspectdb 실행
    - Django 모델 작성
    - Fake migration
    ↓
[Phase 2] Django 전환 (3주)
    - API 재작성 (DRF)
    - 인증 전환
    - Frontend 연동
    ↓
[완료] apps/backend 삭제
```

---

## 🚨 주의사항

### 1. UUID vs Integer Primary Key

**현재 DB:**
```sql
id UUID NOT NULL
```

**Django에서:**
```python
id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
```

- ✅ 타입 일치
- ⚠️ `default=uuid.uuid4`는 새 데이터에만 적용
- ⚠️ 기존 데이터는 이미 UUID 있으므로 문제없음

### 2. JSON 필드

**SQLite:**
```sql
specializations JSON NOT NULL
```

**Django (SQLite):**
```python
specializations = models.JSONField(default=list)
```

- ⚠️ SQLite의 JSON 지원은 제한적 (Django 3.1+)
- ✅ PostgreSQL 전환 시 완전 지원

### 3. DATETIME vs DateTimeField

**SQLAlchemy:**
```python
created_at = Column(DateTime, default=datetime.utcnow)  # naive datetime
```

**Django:**
```python
created_at = models.DateTimeField(auto_now_add=True)  # timezone-aware if USE_TZ=True
```

**해결책:**
```python
# settings.py
USE_TZ = False  # 또는 기존 데이터를 UTC로 변환
```

---

## 📚 추가 리소스

- Django Migrations: https://docs.djangoproject.com/en/4.2/topics/migrations/
- inspectdb: https://docs.djangoproject.com/en/4.2/howto/legacy-databases/
- SQLite → PostgreSQL: https://docs.djangoproject.com/en/4.2/ref/databases/

---

**작성일**: 2025-11-20
**버전**: 1.0 (DJANGO_MIGRATION_PLAN.md 보완)
