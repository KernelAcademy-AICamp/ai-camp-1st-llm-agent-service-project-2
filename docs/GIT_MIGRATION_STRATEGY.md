# Git 연동 마이그레이션 전체 계획

> **Last Updated**: 2025-11-19
> **Version**: 2.5 (Phase 2 Python naming convention 적용)
> **팀 협의**: ✅ 완료
>
> ⚠️ **Phase 0-1 실행은**: [QUICK_START_GUIDE.md](./QUICK_START_GUIDE.md) 참조
>
> 본 문서는 **Phase 2-6**를 다룹니다.

## ⚠️ 중요: Shell 호환성

이 가이드는 **macOS (zsh)** 및 **Linux (bash)** 모두에서 동작하도록 작성되었습니다.

### ✅ 핵심 원칙
1. **`git mv` 사용 필수**: Git history 보존을 위해 모든 파일/디렉토리 이동 시 `git mv` 사용
2. **`shopt` 사용 금지**: bash 전용 명령어로 zsh에서 동작 안 함
3. **`mv` 대신 `git mv`**: 일반 `mv`는 Git history 손실 위험

### 📚 참조 문서
- **[QUICK_START_GUIDE.md](./QUICK_START_GUIDE.md)** - 🚀 **지금 시작하기** (Phase 0-1 실행)
- [START_HERE.md](./START_HERE.md) - 상세 실행 가이드 (Phase 0-1)
- [SHELL_COMPATIBILITY_GUIDE.md](./SHELL_COMPATIBILITY_GUIDE.md) - Shell 호환성 가이드
- 본 문서 (GIT_MIGRATION_STRATEGY.md) - 전체 계획 및 Phase 2-6 가이드

---

## 📊 현재 상황 분석

### Git Repository (develop 브랜치)
```
https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2/tree/develop

Repository Structure:
├── backend/          ✅ FastAPI 백엔드 (기본 버전)
├── frontend/         ✅ React 프론트엔드
├── core/             ✅ RAG pipeline, AI logic
├── experiments/      ✅ 실험 코드
├── notebooks/        ✅ Jupyter notebooks
├── scripts/          ⚠️  빈 디렉토리 (.gitkeep만 존재)
├── tests/            ✅ 테스트
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

### 현재 로컬 프로젝트 (middle_proj_copy/)
```
/Users/myidwon/dev/middle_proj_copy/

Local Structure:
├── backend/          ✅ Git 기반 + 개선 버전 (작업 진행 중)
│                        🚀 다중 LLM 제공자 지원
│                        🚀 하이브리드 검색 (FAISS+BM25)
│                        🚀 개선된 의존성 패키지
├── frontend/         ✅ Git에서 가져온 코드 (작업 진행 중)
├── apps/             🆕 Git에 없음 (모노레포 구조)
│   ├── ai-service/   🆕 일부 파일 존재
│   ├── backend/      🔴 비어있음 (Phase 1에서 생성 예정)
│   ├── web-frontend/ 🔴 비어있음 (Phase 1에서 생성 예정)
│   └── data-pipeline/✅ ETL 파이프라인
├── libs/             🆕 Git에 없음
│   ├── rag-core/     🔴 비어있음 (Phase 2에서 구축 예정)
│   └── domain-model/ ✅ Pydantic 모델
├── data/             🆕 VectorDB, 업로드 (Git 제외)
├── configs/          🆕 설정 파일
├── docs/             🆕 마이그레이션 문서
├── scripts/          ✅ 빌드 스크립트 (Git에는 .gitkeep만 존재)
│   ├── build_vectordb.py
│   ├── build_bm25_index.py
│   ├── criminal_law_data_loader.py
│   ├── parse_criminal_law_data.py
│   └── init_db.py
└── evaluation/       🆕 평가 스크립트
```

### ⚠️ 중요: 코드 버전 차이

**Git 저장소와 로컬 코드는 완전히 동일하지 않습니다!**

| 구분 | Git develop | Local middle_proj_copy | 관계 |
|------|------------|------------------------|------|
| **구조** | 단일 레포 | 모노레포 준비 | 구조 변경 |
| **Import 경로** | `backend.*` | `apps.backend.*` | 변경됨 |
| **LLM 지원** | OpenAI 전용 | 다중 제공자 | 확장됨 |
| **검색 기능** | 기본 Semantic | Hybrid (FAISS+BM25) | 향상됨 |
| **의존성** | 기본 패키지 | +faiss-cpu, rank-bm25 | 추가됨 |
| **유사도** | 기준 (100%) | **85-90%** | 개선 버전 |

**결론**: 로컬은 Git 코드를 **복사 후 개선**한 발전 버전입니다.

**마이그레이션 전략**: 로컬의 개선사항을 Git 저장소에 반영합니다.

---

## 🎯 마이그레이션 목표 (팀 협의 완료)

### 최종 구조

```
ai-camp-1st-llm-agent-service-project-2/ (Git connected)
├── apps/
│   ├── backend/          🎯 기존 backend/ 이동 + libs 활용
│   ├── web-frontend/     🎯 기존 frontend/ 이동
│   ├── ai-service/       🎯 AI 전용 서비스 (선택)
│   └── data-pipeline/    🎯 ETL 파이프라인
│
├── libs/
│   ├── rag-core/         🎯 backend/core/ → libs/rag-core/
│   └── domain-model/     🎯 공통 Pydantic 모델
│
├── data/                 ✅ Git 제외 (.gitignore)
├── configs/              ✅ 설정 파일
├── docs/                 ✅ 문서
├── experiments/          ✅ 유지 (Git repo 기존)
├── notebooks/            ✅ 유지 (Git repo 기존)
├── scripts/              🎯 middle_proj_copy 빌드 스크립트 추가
│   ├── build_vectordb.py
│   ├── build_bm25_index.py
│   └── init_db.py
└── tests/                ✅ 유지 (Git repo 기존)
```

---

## 📋 전체 마이그레이션 계획 (7-10일)

### 타임라인 개요

| Phase | 작업 내용 | 기간 | 실행 문서 |
|-------|----------|------|----------|
| **Phase 0** | Git Repo 준비 | 0.5시간 | [QUICK_START_GUIDE.md](./QUICK_START_GUIDE.md) Step 1-2 |
| **Phase 1** | 모노레포 구조 생성 | 1-2시간 | [QUICK_START_GUIDE.md](./QUICK_START_GUIDE.md) 전체 |
| **Phase 2** | libs/rag-core 구축 | 2-3시간 | 본 문서 Phase 2 |
| **Phase 3** | apps/backend 마이그레이션 | 2-3시간 | 본 문서 Phase 3 |
| **Phase 4** | apps/web-frontend 이동 | 0.5시간 | 본 문서 Phase 4 |
| **Phase 5** | 테스트 및 검증 | 1-2시간 | 본 문서 Phase 5 |
| **Phase 6** | PR 및 머지 | 1시간 | 본 문서 Phase 6 |

---

## Phase 0: Git Repository 준비 (0.5시간)

> ⚠️ **Phase 0도 QUICK_START_GUIDE.md에 포함됨**
>
> **실행 문서**: [QUICK_START_GUIDE.md](./QUICK_START_GUIDE.md) Step 1-2
>
> Phase 0는 Phase 1의 일부로 QUICK_START_GUIDE.md에서 함께 진행합니다.

---

### Phase 0 개요 (참조용)

Phase 0에서는 다음 작업을 수행합니다:

#### 1. 백업 생성 (5분)
```bash
cd /Users/myidwon/dev
tar -czf middle_proj_copy_backup_$(date +%Y%m%d_%H%M%S).tar.gz middle_proj_copy/
```

#### 2. Git Repository 확인 (2분)
- 기존 저장소 사용 또는 새로 클론
- develop 브랜치 최신화

#### 3. Feature 브랜치 생성 (3분)
```bash
git checkout -b feature/monorepo-migration
git push -u origin feature/monorepo-migration
```

**👉 실제 실행은 QUICK_START_GUIDE.md Step 1-2를 따라하세요!**

---

## Phase 1: 모노레포 구조 생성 (1-2시간)

> ⚠️ **Phase 1은 별도 문서에서 진행합니다**
>
> **실행 문서**: [QUICK_START_GUIDE.md](./QUICK_START_GUIDE.md)
>
> **왜 별도 문서인가요?**
> - 복사 & 붙여넣기 가능한 실행 가이드
> - 단계별 검증 포함
> - 초보자 친화적
> - macOS (zsh) 호환성 완벽 보장

---

### Phase 1 개요 (참조용)

Phase 1에서는 다음 작업을 수행합니다:

#### 1. 백업 생성 (5분)
- middle_proj_copy 전체 백업
- Git repository 백업 (선택)

#### 2. Feature 브랜치 생성 (5분)
- `feature/monorepo-migration` 브랜치 생성
- Remote에 push

#### 3. apps/ 디렉토리 생성 및 이동 (10분)
```bash
# ✅ git mv 사용 (Git history 보존!)
git mv backend apps/backend
git mv frontend apps/web-frontend
```

#### 4. libs/ 디렉토리 생성 및 이동 (10분)
```bash
# ✅ git mv 사용 (Git history 보존!)
git mv core libs/rag-core
```

#### 5. 추가 디렉토리 생성 및 커밋 (10분)
- apps/ai-service/, apps/data-pipeline/ 생성
- libs/domain-model/ 생성
- .gitignore 업데이트
- 첫 번째 커밋 & push

#### 6. middle_proj_copy에서 파일 복사 (30분)
- libs/domain-model 복사
- apps/data-pipeline 복사
- configs/ 복사
- docs/ 복사
- scripts/ 복사 (build_vectordb.py, build_bm25_index.py 등)
- 로컬 backend 개선사항 복사
- 두 번째 커밋 & push

#### 7. 테스트 및 검증 (20분)
- PYTHONPATH 설정 테스트
- libs/rag-core import 테스트
- 디렉토리 구조 확인
- Git log 확인
- Git history 보존 확인

#### 8. GitHub에서 확인 (5분)
- feature/monorepo-migration 브랜치 확인
- 커밋 히스토리 확인
- 파일 구조 확인

---

### Phase 1 완료 후 상태

✅ **디렉토리 구조**:
```
ai-camp-1st-llm-agent-service-project-2/
├── apps/
│   ├── backend/          ✅ (git mv로 이동, history 보존됨)
│   ├── web-frontend/     ✅ (git mv로 이동, history 보존됨)
│   ├── ai-service/       ✅ (새로 생성)
│   └── data-pipeline/    ✅ (middle_proj_copy에서 복사)
│
├── libs/
│   ├── rag-core/         ✅ (git mv로 이동, history 보존됨)
│   └── domain-model/     ✅ (middle_proj_copy에서 복사)
│
├── configs/              ✅ (middle_proj_copy에서 복사)
├── docs/                 ✅ (마이그레이션 문서 포함)
├── data/                 ✅ (.gitignore에 추가됨)
├── experiments/          ✅ (기존 유지)
├── notebooks/            ✅ (기존 유지)
├── scripts/              ✅ (middle_proj_copy에서 빌드 스크립트 복사)
│   ├── build_vectordb.py
│   ├── build_bm25_index.py
│   ├── criminal_law_data_loader.py
│   ├── parse_criminal_law_data.py
│   └── init_db.py
└── tests/                ✅ (기존 유지)
```

✅ **Git 상태**:
- feature/monorepo-migration 브랜치 생성됨
- 2개의 커밋 완료:
  1. "feat: create monorepo structure with git mv"
  2. "feat: add files from working directory"
- Git history 완벽 보존 (git log --follow 동작)
- GitHub에 push 완료

✅ **검증 완료**:
- PYTHONPATH 설정 가능
- libs/rag-core import 가능
- 디렉토리 구조 정상
- Git history 추적 가능

---

### 👉 Phase 1 실행 방법

**지금 바로 시작하세요!**

```bash
# 1. QUICK_START_GUIDE.md 열기
cd /Users/myidwon/dev/middle_proj_copy/docs
cat QUICK_START_GUIDE.md

# 2. Step 1부터 차례대로 복사 & 붙여넣기
# (각 Step의 bash 명령어를 Terminal에 복사해서 실행)

# 또는 START_HERE.md 사용 (더 자세한 설명)
cat START_HERE.md
```

**Phase 1 완료 후 이 문서로 돌아와서 Phase 2를 진행하세요!**

---

## Phase 2: libs/rag-core 구축 (2-3일)

### 목표
- `apps/backend/core/`의 RAG 핵심 로직을 `libs/rag-core/`로 추출
- DB 비의존적 모듈만 분리
- apps/backend와 apps/ai-service에서 공유 가능하도록
- **🚀 로컬의 개선사항 반영**: 다중 LLM 제공자, 하이브리드 검색 지원

### ⚠️ 주의: 로컬 backend는 개선 버전
Phase 1에서 이미 로컬 backend의 개선 코드를 apps/backend/로 복사했습니다.
따라서 다음 개선사항이 포함되어 있습니다:
- ✅ 다중 LLM 제공자 지원 (OpenAI/Ollama/Anthropic/Custom)
- ✅ `base_url` 파라미터 (로컬 LLM 서버 지원)
- ✅ 하이브리드 검색 (FAISS + BM25)
- ✅ 개선된 의존성 (faiss-cpu, rank-bm25)

### Step 2.1: libs 디렉토리명 변경 및 구조 생성

> ⚠️ **중요**: Python에서는 하이픈(-)을 모듈명에 사용할 수 없으므로 언더스코어(_)로 변경해야 합니다.

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# 0. 디렉토리명 변경 (Python naming convention)
git mv libs/rag-core libs/rag_core
git mv libs/domain-model libs/domain_model

# 1. libs/rag_core 서브 디렉토리 생성
cd libs/rag_core
mkdir -p embeddings llm retrieval utils

# 2. __init__.py 파일 생성
touch __init__.py
touch embeddings/__init__.py
touch llm/__init__.py
touch retrieval/__init__.py
touch utils/__init__.py

# 3. 확인
ls -la
# embeddings/, llm/, retrieval/, utils/, __init__.py가 보여야 함
```

### Step 2.2: Embeddings 모듈 이동

```bash
# 1. apps/backend/core/embeddings/ → libs/rag_core/embeddings/
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# 파일 복사 (이동 전 백업 개념)
cp apps/backend/core/embeddings/embedder.py libs/rag_core/embeddings/
cp apps/backend/core/embeddings/vectordb.py libs/rag_core/embeddings/

# 2. embeddings/__init__.py 작성
cat > libs/rag_core/embeddings/__init__.py << 'EOF'
"""
RAG Core Embeddings Module
임베딩 모델 및 VectorDB 인터페이스 (DB 비의존)
"""

from .embedder import KoreanLegalEmbedder
from .vectordb import (
    VectorDB,
    ChromaVectorDB,
    FAISSVectorDB,
    create_vector_db
)

__all__ = [
    'KoreanLegalEmbedder',
    'VectorDB',
    'ChromaVectorDB',
    'FAISSVectorDB',
    'create_vector_db'
]
EOF

# 3. 확인
ls -la libs/rag_core/embeddings/
```

### Step 2.3: LLM 모듈 이동

```bash
# 1. LLM 파일 복사
cp apps/backend/core/llm/llm_client.py libs/rag_core/llm/
cp apps/backend/core/llm/rag_chatbot.py libs/rag_core/llm/
cp apps/backend/core/llm/constitutional_chatbot.py libs/rag_core/llm/
cp apps/backend/core/llm/constitutional_prompts.py libs/rag_core/llm/
cp apps/backend/core/llm/adapter_chatbot.py libs/rag_core/llm/

# 2. llm/__init__.py 작성
cat > libs/rag_core/llm/__init__.py << 'EOF'
"""
RAG Core LLM Module
LLM 클라이언트 및 챗봇 인터페이스
"""

from .llm_client import (
    LLMClient,
    OpenAIClient,
    OllamaClient,
    AnthropicClient,
    create_llm_client
)
from .rag_chatbot import RAGChatbot, AdvancedRAGChatbot
from .constitutional_chatbot import ConstitutionalLawChatbot
from .adapter_chatbot import AdapterChatbot
from .constitutional_prompts import ConstitutionalPrinciples

__all__ = [
    'LLMClient',
    'OpenAIClient',
    'OllamaClient',
    'AnthropicClient',
    'create_llm_client',
    'RAGChatbot',
    'AdvancedRAGChatbot',
    'ConstitutionalLawChatbot',
    'AdapterChatbot',
    'ConstitutionalPrinciples'
]
EOF

# 3. 확인
ls -la libs/rag_core/llm/
```

### Step 2.4: Retrieval 모듈 이동

> ⚠️ **중요**: `feedback_filter.py`는 DB 의존적이므로 이동하지 않습니다.
> - `feedback_filter.py`는 `apps/backend/core/retrieval/`에 유지
> - `AsyncSession` 및 DB 모델 의존성 때문에 libs로 이동 불가능
> - 실제 사용처: `apps/backend/routers/chat.py`

```bash
# 1. Retrieval 파일 복사 (feedback_filter.py 제외)
cp apps/backend/core/retrieval/retriever.py libs/rag_core/retrieval/
cp apps/backend/core/retrieval/bm25_index.py libs/rag_core/retrieval/
cp apps/backend/core/retrieval/hybrid_retriever.py libs/rag_core/retrieval/

# 2. retrieval/__init__.py 작성 (filters 제외)
cat > libs/rag_core/retrieval/__init__.py << 'EOF'
"""
RAG Core Retrieval Module
검색 로직 (DB 비의존)

Note: feedback_filter.py는 DB 의존적이므로 apps/backend/core/retrieval/에 유지됨
"""

from .retriever import LegalDocumentRetriever
from .bm25_index import BM25Index
from .hybrid_retriever import HybridRetriever

__all__ = [
    'LegalDocumentRetriever',
    'BM25Index',
    'HybridRetriever'
]
EOF

# 3. 확인
ls -la libs/rag_core/retrieval/
# retriever.py, bm25_index.py, hybrid_retriever.py, __init__.py만 있어야 함
```

### Step 2.5: libs/rag_core 내부 import 경로 수정

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/libs/rag_core

# 1. apps.backend.core → libs.rag_core 변경
find . -name "*.py" -type f -exec sed -i.bak \
  's/from apps\.backend\.core\./from libs.rag_core./g' {} \;

find . -name "*.py" -type f -exec sed -i.bak \
  's/import apps\.backend\.core\./import libs.rag_core./g' {} \;

# 2. backend.core → libs.rag_core 변경
find . -name "*.py" -type f -exec sed -i.bak \
  's/from backend\.core\./from libs.rag_core./g' {} \;

find . -name "*.py" -type f -exec sed -i.bak \
  's/import backend\.core\./import libs.rag_core./g' {} \;

# 3. core. → libs.rag_core. 변경
find . -name "*.py" -type f -exec sed -i.bak \
  's/from core\./from libs.rag_core./g' {} \;

find . -name "*.py" -type f -exec sed -i.bak \
  's/import core\./import libs.rag_core./g' {} \;

# 4. 백업 파일 삭제
find . -name "*.bak" -delete

# 5. 확인
grep -r "from apps.backend" . || echo "✅ No apps.backend imports found"
grep -r "from backend.core" . || echo "✅ No backend.core imports found"
```

### Step 2.6: libs/rag_core/__init__.py 작성

```python
# libs/rag_core/__init__.py
cat > /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/libs/rag_core/__init__.py << 'EOF'
"""
RAG Core Library
공통 RAG 로직: 임베딩, LLM, 검색 (DB 비의존)

이 라이브러리는 apps/backend, apps/ai-service, apps/data-pipeline에서
공통으로 사용하는 RAG 핵심 로직을 포함합니다.

Note:
    - feedback_filter.py는 DB 의존적이므로 apps/backend/core/retrieval/에 유지됨
    - 피드백 필터링은 apps.backend.core.retrieval.feedback_filter에서 import

Usage:
    from libs.rag_core import (
        KoreanLegalEmbedder,
        ChromaVectorDB,
        create_llm_client,
        HybridRetriever
    )
"""

# Embeddings
from .embeddings import (
    KoreanLegalEmbedder,
    VectorDB,
    ChromaVectorDB,
    FAISSVectorDB,
    create_vector_db
)

# LLM
from .llm import (
    LLMClient,
    OpenAIClient,
    OllamaClient,
    AnthropicClient,
    create_llm_client,
    RAGChatbot,
    AdvancedRAGChatbot,
    ConstitutionalLawChatbot,
    AdapterChatbot,
    ConstitutionalPrinciples
)

# Retrieval
from .retrieval import (
    LegalDocumentRetriever,
    BM25Index,
    HybridRetriever
)

__version__ = '1.0.0'

__all__ = [
    # Embeddings
    'KoreanLegalEmbedder',
    'VectorDB',
    'ChromaVectorDB',
    'FAISSVectorDB',
    'create_vector_db',

    # LLM
    'LLMClient',
    'OpenAIClient',
    'OllamaClient',
    'AnthropicClient',
    'create_llm_client',
    'RAGChatbot',
    'AdvancedRAGChatbot',
    'ConstitutionalLawChatbot',
    'AdapterChatbot',
    'ConstitutionalPrinciples',

    # Retrieval
    'LegalDocumentRetriever',
    'BM25Index',
    'HybridRetriever'
]
EOF
```

### Step 2.7: libs/rag_core 테스트

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# PYTHONPATH 설정 및 테스트
export PYTHONPATH=$(pwd):$PYTHONPATH

python3 << 'EOF'
import sys
print("✅ Python path:", sys.path[:3])

# libs/rag_core import 테스트
try:
    from libs.rag_core import (
        KoreanLegalEmbedder,
        ChromaVectorDB,
        create_llm_client,
        HybridRetriever
    )
    print("✅ All imports successful!")
    print(f"  - KoreanLegalEmbedder: {KoreanLegalEmbedder}")
    print(f"  - ChromaVectorDB: {ChromaVectorDB}")
    print(f"  - create_llm_client: {create_llm_client}")
    print(f"  - HybridRetriever: {HybridRetriever}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
EOF
```

### Step 2.8: Commit (libs/rag_core 완성)

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# Stage changes
git add libs/rag_core/ libs/domain_model/

# Commit
git commit -m "feat: implement libs/rag_core library

- Rename libs/rag-core → libs/rag_core (Python naming convention)
- Rename libs/domain-model → libs/domain_model (Python naming convention)
- Extract RAG core logic from apps/backend/core/
- Create DB-independent modules:
  - embeddings/ (KoreanLegalEmbedder, VectorDB, ChromaVectorDB, FAISSVectorDB)
  - llm/ (LLM clients, chatbots, ConstitutionalPrinciples)
  - retrieval/ (LegalDocumentRetriever, BM25Index, HybridRetriever)
  - utils/ (placeholder for future utilities)
- Update import paths to libs.rag_core
- Add comprehensive __init__.py exports
- Exclude feedback_filter.py (DB-dependent, kept in apps/backend/core/retrieval/)

This library can be shared across:
- apps/backend
- apps/ai-service
- apps/data-pipeline

BREAKING CHANGE: Directory naming changed from hyphen to underscore for Python compatibility
Tested: All imports successful via PYTHONPATH"

# Push
git push origin feature/monorepo-migration
```

---

## Phase 3: apps/backend 마이그레이션 (2-3일)

### 목표
- `apps/backend`를 `libs/rag-core` import로 변경
- `apps/backend/core/` 정리 (auth만 남김)
- **로컬의 개선 기능 유지**: 다중 LLM 제공자, 하이브리드 검색
- 기존 기능 유지하면서 코드 정리

### ⚠️ 주의: 개선된 코드 유지
apps/backend는 이미 로컬의 개선 버전을 포함하고 있습니다:
- ✅ main.py: 다중 LLM 제공자 설정 (`LLM_PROVIDER`, `LLM_BASE_URL`)
- ✅ core/llm/llm_client.py: `base_url` 파라미터 지원
- ✅ requirements.txt: faiss-cpu, rank-bm25 포함

이 개선사항들을 libs/rag-core 이동 시 **반드시 유지**해야 합니다.

### Step 3.1: apps/backend/main.py Import 경로 변경

```python
# apps/backend/main.py 수정
cat > /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/apps/backend/main.py << 'EOF'
"""
LawLaw Backend Server
FastAPI 기반 백엔드 서버 - Monorepo 구조
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import logging
import sys
from pathlib import Path

# ==========================================
# PYTHONPATH 설정 (Monorepo 구조)
# ==========================================
BASE_DIR = Path(__file__).parent.parent.parent  # ai-camp-1st-llm-agent-service-project-2/
sys.path.insert(0, str(BASE_DIR))

# ==========================================
# libs/rag-core Import
# ==========================================
from libs.rag_core import (
    create_llm_client,
    KoreanLegalEmbedder,
    ChromaVectorDB,
    BM25Index,
    LegalDocumentRetriever,
    HybridRetriever,
    AdapterChatbot,
    filter_results
)

# ==========================================
# apps/backend Import
# ==========================================
from apps.backend.services.file_parser import FileParser
from apps.backend.services.case_analyzer import CaseAnalyzer
from apps.backend.services.scenario_detector import ScenarioDetector
from apps.backend.services.document_generator import DocumentGenerator
from apps.backend.services.scourt_scraper import SCourtScraper
from apps.backend.services.precedent_crawler import PrecedentCrawler
from apps.backend.services.scheduler import PrecedentScheduler
from apps.backend.services.openlaw_client import OpenLawAPIClient

# Routers
from apps.backend.routers.chat import setup_chat_routes
from apps.backend.routers.cases import setup_case_routes
from apps.backend.routers.documents import setup_document_routes
from apps.backend.routers.adapters import setup_adapter_routes
from apps.backend.routers.auth import setup_auth_routes
from apps.backend.routers.precedents import setup_precedent_routes
from apps.backend.routers.precedent_scraping import router as scraping_router
from apps.backend.routers.precedent_search import router as search_router
from apps.backend.routers.feedback import setup_feedback_routes

# Database
from apps.backend.database import engine, Base
from apps.backend.models.precedent import Precedent
from apps.backend.models.precedent_feedback import PrecedentFeedback, PrecedentFeedbackStats
from apps.backend.models.user import User

# Config
from configs.config import config
import os
import asyncio

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 앱 생성
app = FastAPI(
    title="LawLaw Backend API",
    description="형사법 전문 AI 어시스턴트 백엔드 API (Monorepo)",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "file://"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# RAG 시스템 초기화 (libs/rag-core 활용)
# ==========================================

embedder = None
vectordb = None
bm25_index = None
hybrid_retriever = None
constitutional_chatbot = None

try:
    # 임베딩 모델 초기화
    embedder = KoreanLegalEmbedder()
    logger.info("✅ Embedder initialized (from libs/rag-core)")

    # 벡터 DB 초기화
    vectordb = ChromaVectorDB(
        persist_directory=str(BASE_DIR / "data" / "vectordb" / "chroma_criminal_law"),
        collection_name="criminal_law_docs"
    )
    logger.info(f"✅ Vector DB loaded: {vectordb.get_count()} documents")

    # BM25 인덱스 초기화
    bm25_index_path = BASE_DIR / "data" / "vectordb" / "bm25"
    if bm25_index_path.exists():
        bm25_index = BM25Index()
        bm25_index.load(str(bm25_index_path))
        logger.info(f"✅ BM25 index loaded: {bm25_index.get_count()} documents")

    # Semantic Retriever 초기화
    semantic_retriever = LegalDocumentRetriever(
        embedder=embedder,
        vectordb=vectordb
    )

    # Hybrid Retriever 초기화
    if bm25_index:
        hybrid_retriever = HybridRetriever(
            semantic_retriever=semantic_retriever,
            bm25_index=bm25_index,
            fusion_method='rrf',
            semantic_weight=0.5,
            enable_adaptive_weighting=True
        )
        logger.info("✅ Hybrid Retriever initialized")
    else:
        hybrid_retriever = semantic_retriever
        logger.info("⚠️  Using Semantic Retriever only (BM25 not found)")

except Exception as e:
    logger.error(f"❌ Failed to initialize RAG system: {e}")
    logger.info("Will use fallback mode without RAG")

# LLM 클라이언트 초기화
llm_client = None
try:
    llm_client = create_llm_client(
        provider=config.llm.provider,
        api_key=config.llm.api_key,
        model=config.llm.model,
        base_url=config.llm.base_url,
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens
    )
    logger.info(f"✅ LLM client initialized (provider={config.llm.provider})")

    if hybrid_retriever and llm_client:
        constitutional_chatbot = AdapterChatbot(
            retriever=hybrid_retriever,
            llm_client=llm_client,
            enable_self_critique=True,
            critique_threshold=0.5
        )
        logger.info("✅ Constitutional AI Chatbot initialized")

except Exception as e:
    logger.warning(f"⚠️  Failed to initialize LLM: {e}")
    logger.info("API will run without LLM support")

# 업로드 디렉토리
UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Services 초기화
file_parser = FileParser()
scenario_detector = ScenarioDetector()

case_analyzer = None
if llm_client:
    case_analyzer = CaseAnalyzer(llm_client=llm_client, retriever=hybrid_retriever)
    logger.info("✅ CaseAnalyzer initialized")

document_generator = None
if llm_client:
    document_generator = DocumentGenerator(llm_client=llm_client)
    logger.info("✅ DocumentGenerator initialized")

# Precedent Crawler & Scheduler 초기화
scourt_scraper = None
precedent_crawler = None
precedent_scheduler = None
openlaw_client = None

try:
    openlaw_client = OpenLawAPIClient(api_key=os.getenv("OPENLAW_API_KEY", "fox_racer"))
    scourt_scraper = SCourtScraper()
    precedent_crawler = PrecedentCrawler(scraper=scourt_scraper)
    precedent_scheduler = PrecedentScheduler(crawler=precedent_crawler)
    logger.info("✅ Precedent crawling system initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize precedent system: {e}")

# ==========================================
# Database Tables
# ==========================================

async def create_db_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database tables created")

# ==========================================
# Startup & Shutdown
# ==========================================

@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting LawLaw Backend (Monorepo)...")
    await create_db_tables()

    if precedent_scheduler:
        precedent_scheduler.start()
        asyncio.create_task(precedent_scheduler.run_initial_crawl())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("👋 Shutting down LawLaw Backend...")
    if precedent_scheduler:
        precedent_scheduler.shutdown()

# ==========================================
# Health Check
# ==========================================

class HealthResponse(BaseModel):
    status: str
    model_status: str
    rag_status: str
    timestamp: str

@app.get("/")
async def root():
    return {
        "name": "LawLaw Backend API (Monorepo)",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy" if llm_client else "degraded",
        model_status="available" if llm_client else "not_configured",
        rag_status="available" if hybrid_retriever else "not_configured",
        timestamp=datetime.now().isoformat()
    )

# ==========================================
# Router Registration
# ==========================================

chat_router = setup_chat_routes(
    constitutional_chatbot=constitutional_chatbot,
    llm_client=llm_client,
    hybrid_retriever=hybrid_retriever,
    openlaw_client=openlaw_client
)
app.include_router(chat_router)

cases_router = setup_case_routes(
    case_analyzer=case_analyzer,
    scenario_detector=scenario_detector,
    file_parser=file_parser,
    upload_dir=UPLOAD_DIR
)
app.include_router(cases_router)

documents_router = setup_document_routes(
    document_generator=document_generator,
    scenario_detector=scenario_detector,
    upload_dir=UPLOAD_DIR
)
app.include_router(documents_router)

adapters_router = setup_adapter_routes(
    constitutional_chatbot=constitutional_chatbot
)
app.include_router(adapters_router)

auth_router = setup_auth_routes()
app.include_router(auth_router)

precedents_router = setup_precedent_routes(
    crawler=precedent_crawler,
    openlaw_client=openlaw_client
)
app.include_router(precedents_router)

app.include_router(scraping_router)
app.include_router(search_router)

feedback_router = setup_feedback_routes()
app.include_router(feedback_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
EOF
```

### Step 3.2: apps/backend 전체 Import 경로 자동 변경

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# 1. apps.backend.core → libs.rag_core 변경
find apps/backend -name "*.py" -type f -exec sed -i.bak \
  's/from apps\.backend\.core\.embeddings/from libs.rag_core/g' {} \;

find apps/backend -name "*.py" -type f -exec sed -i.bak \
  's/from apps\.backend\.core\.llm/from libs.rag_core/g' {} \;

find apps/backend -name "*.py" -type f -exec sed -i.bak \
  's/from apps\.backend\.core\.retrieval/from libs.rag_core/g' {} \;

# 2. import 구문 변경
find apps/backend -name "*.py" -type f -exec sed -i.bak \
  's/import apps\.backend\.core\.embeddings/import libs.rag_core/g' {} \;

find apps/backend -name "*.py" -type f -exec sed -i.bak \
  's/import apps\.backend\.core\.llm/import libs.rag_core/g' {} \;

find apps/backend -name "*.py" -type f -exec sed -i.bak \
  's/import apps\.backend\.core\.retrieval/import libs.rag_core/g' {} \;

# 3. 백업 파일 삭제
find apps/backend -name "*.bak" -delete

# 4. 확인
grep -r "from apps.backend.core" apps/backend/ || echo "✅ No old imports found"
```

### Step 3.3: apps/backend/core/ 정리

> ⚠️ **중요**: `core/retrieval/feedback_filter.py`는 삭제하지 않습니다!
> - DB 의존적 모듈이므로 apps/backend에 유지
> - `routers/chat.py`에서 사용 중

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/apps/backend

# 1. 백업 (혹시 모를 경우 대비)
mkdir -p ../../backups
tar -czf ../../backups/backend_core_$(date +%Y%m%d).tar.gz core/

# 2. libs/로 이동한 모듈만 삭제
rm -rf core/embeddings
rm -rf core/llm

# 3. core/retrieval에서 libs로 이동한 파일만 삭제
rm -f core/retrieval/retriever.py
rm -f core/retrieval/bm25_index.py
rm -f core/retrieval/hybrid_retriever.py

# feedback_filter.py는 유지됨 (삭제하지 않음!)

# 4. core/__init__.py 제거 (있는 경우)
rm -f core/__init__.py
rm -f core/retrieval/__init__.py

# 5. 최종 상태 확인
echo "=== core/ 최종 구조 ==="
ls -la core/
# auth/, retrieval/ 두 디렉토리만 남아있어야 함

echo -e "\n=== core/auth/ ==="
ls -la core/auth/
# __init__.py, dependencies.py, jwt.py

echo -e "\n=== core/retrieval/ ==="
ls -la core/retrieval/
# feedback_filter.py만 남아있어야 함 (__init__.py 제거됨)
```

### Step 3.4: apps/backend 실행 테스트

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# PYTHONPATH 설정
export PYTHONPATH=$(pwd):$PYTHONPATH

# Backend 실행
cd apps/backend
python main.py

# 다른 터미널에서 테스트
curl http://localhost:8000/health
curl http://localhost:8000/
```

### Step 3.5: Commit (apps/backend 마이그레이션 완료)

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# Stage changes
git add apps/backend/

# Commit
git commit -m "refactor: migrate apps/backend to use libs/rag-core

- Update import paths from apps.backend.core to libs.rag_core
- Refactor main.py to use libs/rag-core modules
- Remove apps/backend/core/{embeddings,llm}
- Remove apps/backend/core/retrieval/{retriever,bm25_index,hybrid_retriever}.py
- Keep apps/backend/core/auth (FastAPI-specific)
- Keep apps/backend/core/retrieval/feedback_filter.py (DB-dependent)
- Update PYTHONPATH to monorepo root
- Tested: Backend runs successfully on port 8000

Note: feedback_filter.py kept in apps/backend due to AsyncSession dependency

Co-dependent with: libs/rag-core"

# Push
git push origin feature/monorepo-migration
```

---

## Phase 4: apps/web-frontend 이동 (0.5일)

### Step 4.1: Frontend 환경변수 업데이트

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/apps/web-frontend

# .env 또는 .env.local 확인/생성
cat > .env << 'EOF'
REACT_APP_API_URL=http://localhost:8000
REACT_APP_NAME=LawLaw
REACT_APP_VERSION=1.0.0
EOF

# package.json scripts 확인 (이미 설정되어 있을 것)
cat package.json | grep -A 5 "scripts"
```

### Step 4.2: Frontend 테스트

```bash
# 의존성 설치 (필요시)
npm install

# 실행
npm start

# 브라우저에서 http://localhost:3000 확인
```

### Step 4.3: Commit

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

git add apps/web-frontend/
git commit -m "chore: configure apps/web-frontend for monorepo

- Update environment variables
- Verify npm scripts
- Tested: Frontend runs on port 3000"

git push origin feature/monorepo-migration
```

---

## Phase 5: 테스트 및 검증 (1-2일)

### Step 5.1: 통합 테스트 체크리스트

```bash
# 테스트 스크립트 작성
cat > /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/scripts/test_integration.sh << 'EOF'
#!/bin/bash

echo "======================================"
echo "LawLaw Monorepo Integration Test"
echo "======================================"

# PYTHONPATH 설정
export PYTHONPATH=$(pwd):$PYTHONPATH

# 1. libs/rag-core import 테스트
echo -e "\n[1/5] Testing libs/rag-core imports..."
python3 << 'PYTHON_EOF'
from libs.rag_core import (
    KoreanLegalEmbedder,
    ChromaVectorDB,
    create_llm_client,
    HybridRetriever
)
print("✅ libs/rag-core imports successful")
PYTHON_EOF

if [ $? -ne 0 ]; then
    echo "❌ libs/rag-core import test failed"
    exit 1
fi

# 2. apps/backend import 테스트
echo -e "\n[2/5] Testing apps/backend imports..."
python3 << 'PYTHON_EOF'
from apps.backend.models.user import User
from apps.backend.services.file_parser import FileParser
print("✅ apps/backend imports successful")
PYTHON_EOF

if [ $? -ne 0 ]; then
    echo "❌ apps/backend import test failed"
    exit 1
fi

# 3. Backend 실행 가능 여부 확인
echo -e "\n[3/5] Checking backend startup..."
cd apps/backend
timeout 10 python main.py > /dev/null 2>&1 &
BACKEND_PID=$!
sleep 5

if kill -0 $BACKEND_PID 2>/dev/null; then
    echo "✅ Backend starts successfully"
    kill $BACKEND_PID
else
    echo "❌ Backend failed to start"
    exit 1
fi

cd ../..

# 4. Frontend 의존성 확인
echo -e "\n[4/5] Checking frontend dependencies..."
cd apps/web-frontend
if [ -d "node_modules" ]; then
    echo "✅ Frontend node_modules exist"
else
    echo "⚠️  Frontend dependencies not installed, running npm install..."
    npm install
fi
cd ../..

# 5. 디렉토리 구조 검증
echo -e "\n[5/5] Verifying directory structure..."
REQUIRED_DIRS=(
    "apps/backend"
    "apps/web-frontend"
    "libs/rag-core"
    "libs/domain-model"
    "data"
    "configs"
    "docs"
)

for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  ✅ $dir"
    else
        echo "  ❌ $dir (missing)"
        exit 1
    fi
done

echo -e "\n======================================"
echo "✅ All integration tests passed!"
echo "======================================"
EOF

chmod +x scripts/test_integration.sh

# 실행
./scripts/test_integration.sh
```

### Step 5.2: E2E 테스트 (수동)

```bash
# Terminal 1: Backend 실행
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
export PYTHONPATH=$(pwd):$PYTHONPATH
cd apps/backend
python main.py

# Terminal 2: Frontend 실행
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/apps/web-frontend
npm start

# Terminal 3: API 테스트
curl http://localhost:8000/health
curl http://localhost:8000/

# 브라우저: http://localhost:3000
# - 로그인 테스트
# - RAG 챗봇 테스트
# - 사건 분석 테스트
```

### Step 5.3: 문제 발견 시 수정

문제 발생 시:
1. 로그 확인
2. Import 경로 재확인
3. PYTHONPATH 설정 확인
4. 수정 후 재테스트

### Step 5.4: Commit (테스트 스크립트)

```bash
git add scripts/test_integration.sh
git commit -m "test: add integration test script

- Test libs/rag-core imports
- Test apps/backend imports
- Verify backend startup
- Check frontend dependencies
- Validate directory structure"

git push origin feature/monorepo-migration
```

---

## Phase 6: PR 생성 및 머지 (1일)

### Step 6.1: README.md 업데이트

```bash
cat > /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2/README.md << 'EOF'
# LawLaw - 형사법 전문 AI 어시스턴트

> 법률 전문가를 위한 AI 기반 법률 서비스 플랫폼

## 🏗️ 프로젝트 구조 (Monorepo)

```
lawlaw/
├── apps/                 # 실행 가능한 애플리케이션
│   ├── backend/          # FastAPI 백엔드 (포트 8000)
│   ├── web-frontend/     # React 프론트엔드 (포트 3000)
│   ├── ai-service/       # AI 전용 서비스 (선택, 포트 8001)
│   └── data-pipeline/    # ETL 파이프라인
│
├── libs/                 # 공통 라이브러리
│   ├── rag-core/         # RAG 핵심 로직 (DB 비의존)
│   └── domain-model/     # 공통 Pydantic 모델
│
├── data/                 # 데이터 (Git 제외)
│   ├── vectordb/         # ChromaDB, BM25 인덱스
│   └── uploads/          # 업로드 파일
│
├── configs/              # 설정 파일
├── docs/                 # 문서
├── experiments/          # 실험 코드
├── notebooks/            # Jupyter notebooks
├── scripts/              # 유틸리티 스크립트
└── tests/                # 테스트
```

## 🚀 빠른 시작

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+

### 1. 환경 설정

```bash
# Repository 클론
git clone https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2.git
cd ai-camp-1st-llm-agent-service-project-2

# PYTHONPATH 설정 (중요!)
export PYTHONPATH=$(pwd):$PYTHONPATH

# 환경변수 설정
cp .env.example .env
# .env 파일 편집 (LLM API 키 등)
```

### 2. 백엔드 실행

```bash
cd apps/backend

# Python 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 실행
python main.py
```

백엔드 접속: http://localhost:8000

### 3. 프론트엔드 실행

```bash
cd apps/web-frontend

# 의존성 설치
npm install

# 실행
npm start
```

프론트엔드 접속: http://localhost:3000

## 📚 주요 기능

- ✅ **RAG 기반 챗봇**: 형사법 판례 기반 질의응답
- ✅ **사건 분석**: 사건 문서 자동 분석 및 관련 판례 검색
- ✅ **문서 생성**: AI 기반 법률 문서 자동 생성
- ✅ **판례 검색**: 38만+ 형사법 판례 하이브리드 검색
- ✅ **Constitutional AI**: 헌법적 원칙 기반 AI 응답

## 🧪 테스트

```bash
# 통합 테스트
./scripts/test_integration.sh

# Backend 단위 테스트
cd apps/backend
pytest

# Frontend 테스트
cd apps/web-frontend
npm test
```

## 📖 문서

- [마이그레이션 가이드](docs/GIT_MIGRATION_STRATEGY.md)
- [마이그레이션 계획](docs/MIGRATION_PLAN_REVISED.md)
- [API 문서](http://localhost:8000/docs) (백엔드 실행 후)

## 🤝 기여

1. Feature 브랜치 생성: `git checkout -b feature/amazing-feature`
2. 변경사항 커밋: `git commit -m 'feat: add amazing feature'`
3. Push: `git push origin feature/amazing-feature`
4. Pull Request 생성

## 📝 라이선스

MIT License

## 👥 팀

Team 2 - KernelAcademy AI Camp 1st
EOF

git add README.md
git commit -m "docs: update README for monorepo structure"
git push origin feature/monorepo-migration
```

### Step 6.2: PR 생성

```bash
# GitHub에서 PR 생성
# https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2/compare/develop...feature/monorepo-migration
```

**PR Template:**

```markdown
## 📋 변경 사항

### 🏗️ 모노레포 구조 전환

#### 디렉토리 변경
- ✅ `backend/` → `apps/backend/`
- ✅ `frontend/` → `apps/web-frontend/`
- ✅ `backend/core/` → `libs/rag-core/` (RAG 핵심 로직)
- ✅ 신규 추가: `apps/ai-service/`, `apps/data-pipeline/`
- ✅ 신규 추가: `libs/domain-model/`

#### libs/rag-core 구축
- ✅ DB 비의존 RAG 핵심 로직 추출
- ✅ `embeddings/`: KoreanLegalEmbedder, VectorDB
- ✅ `llm/`: LLM clients, Chatbots
- ✅ `retrieval/`: Retriever, BM25, Filters
- ✅ apps/backend, apps/ai-service에서 공유 가능

#### apps/backend 마이그레이션
- ✅ Import 경로 `libs.rag_core`로 변경
- ✅ `apps/backend/core/` 정리 (auth만 유지)
- ✅ PYTHONPATH 설정 (monorepo root)
- ✅ 모든 기능 정상 작동 확인

## 🎯 변경 이유

### 문제점
1. **관심사 미분리**: 모든 기능이 단일 backend에 혼재
2. **코드 중복**: RAG 로직이 여러 곳에 중복
3. **확장성 부족**: 마이크로서비스 전환 어려움
4. **의존성 복잡**: 명확한 의존성 관계 부재

### 해결책
1. **Monorepo 구조**: apps/, libs/ 명확히 분리
2. **libs/rag-core**: 공통 RAG 로직 중앙화
3. **독립 배포**: 각 앱 독립 실행 가능
4. **명확한 의존성**: apps → libs (단방향)

## 🧪 테스트

### 테스트 완료 항목
- [x] libs/rag-core import 테스트
- [x] apps/backend import 테스트
- [x] Backend 실행 (포트 8000)
- [x] Frontend 실행 (포트 3000)
- [x] API 엔드포인트 동작 확인
- [x] RAG 챗봇 기능 테스트
- [x] 통합 테스트 스크립트

### 테스트 방법

```bash
# 1. 통합 테스트
./scripts/test_integration.sh

# 2. 수동 E2E 테스트
# Terminal 1
export PYTHONPATH=$(pwd):$PYTHONPATH
cd apps/backend && python main.py

# Terminal 2
cd apps/web-frontend && npm start

# Terminal 3
curl http://localhost:8000/health
```

## ⚠️ Breaking Changes

### 필수 변경사항

#### 1. PYTHONPATH 설정
```bash
# 기존
export PYTHONPATH=/path/to/backend:$PYTHONPATH

# 변경 후 (Monorepo root)
export PYTHONPATH=/path/to/ai-camp-1st-llm-agent-service-project-2:$PYTHONPATH
```

#### 2. 실행 경로 변경
```bash
# 기존
cd backend && python main.py
cd frontend && npm start

# 변경 후
cd apps/backend && python main.py
cd apps/web-frontend && npm start
```

#### 3. Import 경로 변경
```python
# 기존
from backend.core.embeddings import KoreanLegalEmbedder

# 변경 후
from libs.rag_core import KoreanLegalEmbedder
```

## 📝 마이그레이션 가이드

자세한 내용: [GIT_MIGRATION_STRATEGY.md](docs/GIT_MIGRATION_STRATEGY.md)

## 👥 리뷰어

@팀원1 @팀원2 @팀원3

## 📚 관련 이슈

Closes #XX (모노레포 전환 이슈 번호)
```

### Step 6.3: 팀 리뷰 및 머지

1. **팀원 리뷰 요청**
2. **피드백 반영**
3. **CI/CD 확인** (GitHub Actions)
4. **승인 후 머지**

```bash
# 머지 후
git checkout develop
git pull origin develop

# 로컬 정리
git branch -d feature/monorepo-migration
```

---

## ✅ 최종 체크리스트

### Phase 0-1: 기본 구조 생성 (QUICK_START_GUIDE.md)
- [ ] 백업 생성 완료 (Step 1)
- [ ] Feature 브랜치 생성 (Step 2)
- [ ] apps/ 디렉토리 생성 및 이동 (Step 3)
  - [ ] git mv backend apps/backend
  - [ ] git mv frontend apps/web-frontend
- [ ] libs/ 디렉토리 생성 및 이동 (Step 4)
  - [ ] git mv core libs/rag-core
- [ ] 추가 디렉토리 생성 및 첫 번째 커밋 (Step 5)
- [ ] middle_proj_copy 파일 복사 및 두 번째 커밋 (Step 6)
- [ ] 테스트 및 검증 (Step 7)
- [ ] GitHub 확인 (Step 8)
- [ ] **Git history 보존 확인** (중요!)

### Phase 2: libs/rag-core 구축
- [ ] embeddings/ 모듈 작성
- [ ] llm/ 모듈 작성
- [ ] retrieval/ 모듈 작성
- [ ] filters.py 순수 로직 작성
- [ ] __init__.py 작성
- [ ] Import 경로 수정
- [ ] libs/rag-core 테스트 성공
- [ ] Commit

### Phase 3: apps/backend 마이그레이션
- [ ] main.py Import 경로 변경
- [ ] 전체 Import 경로 자동 변경
- [ ] apps/backend/core/ 정리
- [ ] Backend 실행 테스트
- [ ] API 동작 확인
- [ ] Commit

### Phase 4: apps/web-frontend 이동
- [ ] 환경변수 설정
- [ ] Frontend 실행 테스트
- [ ] Commit

### Phase 5: 테스트 및 검증
- [ ] 통합 테스트 스크립트 작성
- [ ] 통합 테스트 통과
- [ ] E2E 수동 테스트 완료
- [ ] 모든 기능 정상 작동 확인
- [ ] Commit

### Phase 6: PR 및 머지
- [ ] README.md 업데이트
- [ ] PR 생성
- [ ] 팀원 리뷰
- [ ] 피드백 반영
- [ ] CI/CD 통과
- [ ] develop 브랜치 머지
- [ ] 팀원 동기화 안내

---

## 📅 예상 일정

| Phase | 작업 | 기간 | 누적 |
|-------|------|------|------|
| Phase 0 | Git 준비 | 0.5일 | 0.5일 |
| Phase 1 | 구조 생성 | 1-2일 | 2.5일 |
| Phase 2 | libs/rag-core | 2-3일 | 5.5일 |
| Phase 3 | apps/backend | 2-3일 | 8.5일 |
| Phase 4 | apps/web-frontend | 0.5일 | 9일 |
| Phase 5 | 테스트 | 1-2일 | 11일 |
| Phase 6 | PR/머지 | 1일 | 12일 |

**총 예상 기간**: 10-12일 (2주)

---

## 🚨 주의사항

### 1. Shell 호환성 (중요!)
**macOS (zsh) 사용자는 반드시 `git mv` 사용:**
```bash
# ✅ 올바른 방법 (zsh/bash 모두 동작, Git history 보존)
git mv backend apps/backend

# ❌ 잘못된 방법 (zsh에서 동작 안 함)
shopt -s dotglob  # bash 전용 명령어
mv backend/* apps/backend/
```

### 2. PYTHONPATH 설정 필수
모든 Python 실행 시 Monorepo root를 PYTHONPATH에 추가:
```bash
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### 3. Git History 보존
모든 파일/디렉토리 이동 시 **반드시 `git mv` 사용**:
- ✅ `git mv backend apps/backend` (history 보존)
- ❌ `mv backend apps/backend` (history 손실 위험)

### 4. 점진적 진행
한 Phase 완료 후 테스트 → 다음 Phase 진행

### 5. 백업 필수
각 Phase 전 백업 생성

### 6. 팀 커뮤니케이션
구조 변경은 팀 전체에 영향, 지속적인 공유 필요

---

**작성일**: 2025-11-19
**작성자**: Claude (AI Assistant)
**문서 버전**: 2.3 (코드 버전 차이 분석 반영)
**팀 협의**: ✅ 완료

---

## 📋 부록: Git vs Local 코드 비교 분석

### 비교 분석 결과 요약

#### 파일 구조
- **Python 파일 개수**: 44개 (동일 ✅)
- **디렉토리 구조**: 100% 일치 ✅
- **파일 목록**: 100% 일치 ✅

#### 주요 차이점

| 파일 | Git develop | Local middle_proj_copy | 차이점 |
|------|------------|------------------------|--------|
| **main.py** | 10,938 bytes | 11,482 bytes | +544 bytes (다중 LLM 설정) |
| **requirements.txt** | 기본 패키지 | + faiss-cpu, rank-bm25, bcrypt | 하이브리드 검색 지원 |
| **core/llm/llm_client.py** | MD5: fbbfb... | MD5: e9ec1... | `base_url` 파라미터 추가 |
| **core/embeddings/embedder.py** | MD5: 71500... | MD5: 0b70e... | 기능 개선 |
| **database.py** | MD5: 00278... | MD5: 00278... | ✅ 완전 일치 |

#### 개선사항 세부 내역

**1. main.py**
```python
# Git 버전
OPENAI_API_KEY = config.llm.openai_api_key
MODEL_NAME = "gpt-4-turbo-preview"
llm_client = create_llm_client(provider="openai", ...)

# Local 버전 (개선)
LLM_API_KEY = config.llm.api_key
LLM_BASE_URL = config.llm.base_url  # Custom endpoint 지원
LLM_MODEL = config.llm.model
LLM_PROVIDER = config.llm.provider  # 다중 제공자
llm_client = create_llm_client(
    provider=LLM_PROVIDER,
    base_url=LLM_BASE_URL,  # 로컬 LLM 서버 지원
    ...
)
```

**2. core/llm/llm_client.py**
```python
# Git 버전
class OpenAIClient(LLMClient):
    def __init__(self, api_key, model, temperature, max_tokens):
        self.client = OpenAI(api_key=api_key)

# Local 버전 (개선)
class OpenAIClient(LLMClient):
    def __init__(self, api_key, model, temperature, max_tokens,
                 base_url=None):  # Custom endpoint 지원
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url  # 로컬/Custom LLM 서버
        )
```

**3. requirements.txt**
```ini
# Git 버전
chromadb>=0.4.18
langchain>=0.0.340
# (FAISS, BM25 없음)

# Local 버전 (개선)
chromadb>=0.4.18
langchain>=0.0.340
faiss-cpu>=1.7.4      # FAISS 벡터 검색 추가
rank-bm25>=0.2.2      # BM25 검색 알고리즘 추가
bcrypt==4.0.1         # 버전 고정 (호환성 이슈 해결)
```

#### 유사도 매트릭스

| 레이어 | 유사도 | 비고 |
|--------|--------|------|
| **파일 구조** | 100% | 완전 일치 |
| **핵심 로직** | 95% | 거의 동일 (같은 코드 베이스) |
| **설정/환경** | 70% | 다중 LLM 제공자 추가 |
| **의존성** | 85% | FAISS, BM25 추가 |
| **전체** | **85-90%** | 구조 동일, 기능 확장 |

#### 관계 정의
```
Git develop (원본 - 2025-11-13)
    ↓
  Clone & 개발 (2025-11-13 ~ 2025-11-19)
    ↓
Local middle_proj_copy (발전 버전 - 2025-11-19)
    개선 사항:
    1. 모노레포 구조 적용 (apps/backend/)
    2. 다중 LLM 제공자 지원
    3. 하이브리드 검색 (FAISS + BM25)
    4. Custom endpoint 지원 (base_url)
    5. 의존성 패키지 확장
```

#### 마이그레이션 전략 권장사항

1. **Phase 1**: Git 저장소에 모노레포 구조 생성
   - ✅ `git mv backend apps/backend` (Git history 보존)
   - ✅ 로컬의 **개선된 코드** 복사

2. **Phase 2**: libs/rag-core 구축
   - ✅ 로컬의 개선된 core 모듈 사용
   - ✅ 다중 LLM 지원 유지
   - ✅ 하이브리드 검색 기능 유지

3. **Phase 3**: apps/backend 마이그레이션
   - ✅ 개선된 main.py 유지
   - ✅ LLM_PROVIDER, LLM_BASE_URL 설정 유지
   - ✅ faiss-cpu, rank-bm25 의존성 유지

**결론**: 로컬 버전의 개선사항을 적극 활용하여 마이그레이션!

---

### 📚 변경 이력
- **v2.5** (2025-11-19): Phase 2 수정 - Python naming convention 적용
  - 디렉토리명 변경: `rag-core` → `rag_core`, `domain-model` → `domain_model`
  - Import 수정: `CONSTITUTIONAL_PRINCIPLES` → `ConstitutionalPrinciples`
  - Step 2.1에 디렉토리 이름 변경 단계 추가 (git mv 사용)
  - Step 2.3, 2.6 `ConstitutionalPrinciples` import 수정
  - 모든 경로를 `libs/rag_core`로 수정
  - 실제 실행 중 발견된 오류 수정 반영
- **v2.4** (2025-11-19): Phase 2 수정 - feedback_filter.py 처리 방식 변경
  - `feedback_filter.py`를 apps/backend/core/retrieval/에 유지 (DB 의존성)
  - `filters.py` 생성 제거 (불필요)
  - Step 2.4, 2.6, 2.7, 3.3 수정
  - 실제 사용 현황 분석 결과 반영
- **v2.3** (2025-11-19): Git vs Local 코드 비교 분석 추가, 개선사항 반영
- **v2.2** (2025-11-19): Phase 0-1을 QUICK_START_GUIDE.md로 분리, 문서 구조 개선
- **v2.1** (2025-11-19): Shell 호환성 개선 (`shopt` 제거, `git mv` 사용)
- **v2.0** (2025-11-19): 전체 마이그레이션 포함
- **v1.0** (2025-11-18): 초안 작성
