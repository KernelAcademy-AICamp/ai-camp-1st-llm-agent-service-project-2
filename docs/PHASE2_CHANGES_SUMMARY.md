# Phase 2 변경사항 요약

> **작성일**: 2025-11-19
> **버전**: GIT_MIGRATION_STRATEGY.md v2.4
> **목적**: Phase 2 실행 전 주요 변경사항 설명

---

## 📋 변경 이유

**실제 사용 현황 분석 결과**를 바탕으로 GIT_MIGRATION_STRATEGY.md의 Phase 2를 수정했습니다.

### 발견 사항

#### 1. feedback_filter.py 사용 현황
```python
# 실제 사용되는 코드 (apps/backend/routers/chat.py)
from apps.backend.core.retrieval.feedback_filter import get_excluded_precedent_ids

excluded_ids = await get_excluded_precedent_ids(db)
```

**분석 결과**:
- ✅ `get_excluded_precedent_ids()` 함수 **사용 중** (AsyncSession 의존)
- ❌ `FeedbackFilter` 클래스 **미사용**
- ❌ `apply_feedback_filter()` 함수 **미사용**

#### 2. DB 의존성
```python
# get_excluded_precedent_ids() 함수 내부
async def get_excluded_precedent_ids(db: AsyncSession) -> Set[str]:
    result = await db.execute(
        select(PrecedentFeedbackStats.precedent_id)
        .where(PrecedentFeedbackStats.should_exclude == True)
    )
    return set(result.scalars().all())
```

**결론**:
- DB 세션 (`AsyncSession`) 필요
- DB 모델 (`PrecedentFeedbackStats`) 의존
- **libs/rag-core로 이동 불가능**

---

## 🔄 주요 변경사항

### 변경 전 (v2.3)

**Step 2.4**: filters.py 생성
```bash
# 순수 로직을 libs/rag-core/retrieval/filters.py로 분리
cat > libs/rag-core/retrieval/filters.py << 'EOF'
def filter_results(...):  # 순수 로직
    ...
EOF
```

**문제점**:
1. ❌ 미사용 코드(`apply_feedback_filter`)를 위한 파일 생성
2. ❌ 불필요한 파일 관리 복잡도 증가
3. ❌ 실제 사용되는 코드는 여전히 DB 의존적

---

### 변경 후 (v2.4) ✅

**Step 2.4**: feedback_filter.py 유지
```bash
# feedback_filter.py는 복사하지 않음 (apps/backend에 유지)
cp apps/backend/core/retrieval/retriever.py libs/rag-core/retrieval/
cp apps/backend/core/retrieval/bm25_index.py libs/rag-core/retrieval/
cp apps/backend/core/retrieval/hybrid_retriever.py libs/rag-core/retrieval/

# filters.py는 생성하지 않음
```

**장점**:
1. ✅ 실제 사용 현황 반영
2. ✅ 코드 복잡도 감소
3. ✅ DB 의존성 명확히 유지

---

## 📝 수정된 Step 목록

### Step 2.4: Retrieval 모듈 이동
**변경 전**:
- retriever.py, bm25_index.py, hybrid_retriever.py 복사
- **filters.py 생성** (순수 로직 추출)

**변경 후**:
- retriever.py, bm25_index.py, hybrid_retriever.py 복사
- **filters.py 생성 제거**
- feedback_filter.py는 apps/backend에 유지

---

### Step 2.6: libs/rag-core/__init__.py
**변경 전**:
```python
from .retrieval import (
    LegalDocumentRetriever,
    BM25Index,
    HybridRetriever,
    filter_results,           # ❌ 제거됨
    apply_quality_threshold,  # ❌ 제거됨
    deduplicate_results       # ❌ 제거됨
)
```

**변경 후**:
```python
from .retrieval import (
    LegalDocumentRetriever,
    BM25Index,
    HybridRetriever
)

# Note: feedback_filter는 apps.backend.core.retrieval.feedback_filter에서 import
```

---

### Step 2.7: libs/rag-core 테스트
**변경 전**:
```python
from libs.rag_core import (
    KoreanLegalEmbedder,
    ChromaVectorDB,
    create_llm_client,
    HybridRetriever,
    filter_results  # ❌ 제거됨
)
```

**변경 후**:
```python
from libs.rag_core import (
    KoreanLegalEmbedder,
    ChromaVectorDB,
    create_llm_client,
    HybridRetriever
)
```

---

### Step 3.3: apps/backend/core/ 정리
**변경 전**:
```bash
rm -rf core/embeddings
rm -rf core/llm
rm -rf core/retrieval  # ❌ 전체 삭제
```

**변경 후**:
```bash
rm -rf core/embeddings
rm -rf core/llm

# core/retrieval에서 libs로 이동한 파일만 삭제
rm -f core/retrieval/retriever.py
rm -f core/retrieval/bm25_index.py
rm -f core/retrieval/hybrid_retriever.py

# feedback_filter.py는 유지됨! ✅
```

**최종 상태**:
```
apps/backend/core/
├── auth/                    ✅ 유지
│   ├── __init__.py
│   ├── dependencies.py
│   └── jwt.py
└── retrieval/
    └── feedback_filter.py   ✅ 유지 (DB 의존적)
```

---

## ✅ 실행 시 주의사항

### 1. Phase 2 실행 시
- GIT_MIGRATION_STRATEGY.md **v2.4**를 따라 진행
- Step 2.4에서 **filters.py를 생성하지 않음**
- feedback_filter.py는 **복사하지 않음**

### 2. Phase 3 실행 시
- `apps/backend/routers/chat.py`의 import는 **수정하지 않음**
  ```python
  # 이 import는 그대로 유지 (apps/backend에 남아있음)
  from apps.backend.core.retrieval.feedback_filter import get_excluded_precedent_ids
  ```

### 3. 최종 검증
```bash
# apps/backend/core/retrieval/feedback_filter.py가 존재해야 함
ls -la apps/backend/core/retrieval/
# feedback_filter.py ✅

# libs/rag-core/retrieval/filters.py는 존재하지 않아야 함
ls -la libs/rag-core/retrieval/
# retriever.py, bm25_index.py, hybrid_retriever.py, __init__.py만 존재 ✅
```

---

## 🎯 결론

**변경 사유**:
1. 실제 사용되는 코드는 모두 DB 의존적
2. 미사용 코드를 위한 파일 분리는 불필요한 복잡도 증가
3. 피드백 필터링은 비즈니스 로직 (libs/rag-core에 부적합)

**효과**:
- ✅ 코드 복잡도 감소
- ✅ 명확한 의존성 관리
- ✅ 실제 사용 현황 반영

**다음 단계**:
- GIT_MIGRATION_STRATEGY.md의 Phase 2 Step 2.1부터 시작
- 수정된 내용을 따라 진행
- 각 Step 완료 후 검증

---

**작성**: Claude (AI Assistant)
**검증**: 실제 코드 분석 기반
**문서 버전**: v2.4
