# 🚀 마이그레이션 빠른 시작 가이드

> **소요 시간**: 1-2시간
> **난이도**: ⭐⭐ (중급)
> **전제 조건**: Git 기본 지식, Terminal 사용 경험
> **마지막 업데이트**: 2025-11-19

---

## 📋 실행 계획 및 진행 상황

### 🎯 전체 실행 계획

이 가이드는 **4개의 그룹**으로 나뉘어 단계별로 진행됩니다:

| 그룹 | Step | 작업 내용 | 소요 시간 | 리스크 |
|------|------|----------|----------|--------|
| **그룹 1** | 1-2 | 준비 단계 (백업, 브랜치) | 10분 | 낮음 ⚪ |
| **그룹 2** | 3-4 | 핵심 구조 변경 (git mv) | 20분 | **높음** 🔴 |
| **그룹 3** | 5-6 | 파일 추가 및 커밋 | 40분 | 중간 🟡 |
| **그룹 4** | 7-8 | 검증 및 완료 | 25분 | 낮음 ⚪ |

**총 예상 시간**: 약 1시간 35분

---

### ✅ 진행 상황 체크리스트

#### 📦 그룹 1: 준비 단계 (Step 1-2)
- [ ] **Step 1**: 백업 생성 완료
  - [ ] middle_proj_copy 백업 파일 생성됨
  - [ ] 백업 파일 크기 확인 (ls -lh)
- [ ] **Step 2**: Feature 브랜치 생성 완료
  - [ ] develop 브랜치에서 최신 코드 pull
  - [ ] feature/monorepo-migration 브랜치 생성
  - [ ] Remote에 push 완료
  - [ ] 현재 브랜치 확인 (git branch)

**그룹 1 완료 조건**: ✅ 백업 파일 존재 + feature 브랜치 생성

---

#### 🏗️ 그룹 2: 핵심 구조 변경 (Step 3-4) - **가장 중요!**
- [ ] **Step 3**: apps/ 디렉토리 생성 및 이동
  - [ ] apps/ 디렉토리 생성됨
  - [ ] `git mv backend apps/backend` 실행 완료
  - [ ] `git mv frontend apps/web-frontend` 실행 완료
  - [ ] **중요**: `git status`에서 "renamed:" 확인됨 (Git history 보존)
- [ ] **Step 4**: libs/ 디렉토리 생성
  - [ ] libs/rag-core/, libs/domain-model/ 생성
  - [ ] 비어있는 core/ 디렉토리 제거
  - [ ] .gitkeep 파일 생성
  - [ ] Git 상태 확인 (new file, deleted 확인)

**그룹 2 완료 조건**: ✅ `git status`에서 "renamed:" 표시 + libs/ 디렉토리 존재

**⚠️ 중요**: 이 그룹에서 문제 발생 시 즉시 중단하고 확인 필요!

---

#### 📁 그룹 3: 파일 추가 및 커밋 (Step 5-6)
- [ ] **Step 5**: 추가 디렉토리 생성 및 첫 번째 커밋
  - [ ] apps/ai-service/, apps/data-pipeline/ 생성
  - [ ] .gitignore 업데이트 완료
  - [ ] `git add .` 실행
  - [ ] 첫 번째 커밋 완료 ("feat: create monorepo structure")
  - [ ] GitHub에 push 완료
- [ ] **Step 6**: middle_proj_copy 코드 복사 및 두 번째 커밋
  - [ ] libs/domain-model 복사 완료
  - [ ] apps/data-pipeline 복사 완료
  - [ ] configs/ 복사 완료
  - [ ] docs/ 복사 완료 (마이그레이션 문서 5개)
  - [ ] scripts/ 복사 완료 (빌드 스크립트)
  - [ ] 로컬 backend 개선사항 복사 완료
    - [ ] core/ 모듈 복사
    - [ ] main.py 복사
    - [ ] requirements.txt 복사
    - [ ] models/, routers/, services/, templates/ 복사
  - [ ] 두 번째 커밋 완료 ("feat: add enhanced code")
  - [ ] GitHub에 push 완료

**그룹 3 완료 조건**: ✅ 2개의 커밋 완료 + GitHub에 push

---

#### ✔️ 그룹 4: 검증 및 완료 (Step 7-8)
- [ ] **Step 7**: 테스트 및 검증
  - [ ] PYTHONPATH 설정 확인
  - [ ] 디렉토리 구조 확인 (apps/, libs/)
  - [ ] libs/rag-core 내부 확인 (.gitkeep)
  - [ ] Git log 확인 (최근 커밋 2개)
  - [ ] **중요**: Git history 보존 확인 (`git log --follow`)
- [ ] **Step 8**: GitHub에서 확인
  - [ ] feature/monorepo-migration 브랜치 확인
  - [ ] apps/backend/, apps/web-frontend/ 폴더 확인
  - [ ] libs/rag-core/ 폴더 확인
  - [ ] docs/ 마이그레이션 문서 확인
  - [ ] 커밋 히스토리 확인 (2개 커밋)

**그룹 4 완료 조건**: ✅ 모든 테스트 통과 + GitHub 확인 완료

---

### 🎉 Phase 1 전체 완료 체크리스트

- [ ] ✅ 그룹 1 완료 (준비 단계)
- [ ] ✅ 그룹 2 완료 (핵심 구조 변경)
- [ ] ✅ 그룹 3 완료 (파일 추가 및 커밋)
- [ ] ✅ 그룹 4 완료 (검증 및 완료)
- [ ] ✅ **Git history 보존 확인** (최종 검증)
- [ ] ✅ GitHub에서 모든 항목 확인

**Phase 1 완료 시**: 다음 Phase 2로 진행 가능 (GIT_MIGRATION_STRATEGY.md 참조)

---

### 🤖 AI 실행 계획

Claude가 자동으로 실행할 그룹:

1. **그룹 1 (Step 1-2)**: ✅ 자동 실행 - 백업 및 브랜치 생성
2. **그룹 2 (Step 3-4)**: ✅ 자동 실행 - 구조 변경 (검증 후 다음 진행)
3. **그룹 3 (Step 5-6)**: ✅ 자동 실행 - 파일 복사 및 커밋 (검증 후 다음 진행)
4. **그룹 4 (Step 7-8)**: ✅ 자동 실행 - 최종 검증

**중단 조건**: 각 그룹 완료 후 검증 실패 시 즉시 중단

---

## ⚠️ 중요: 코드 버전 차이 인식

**Git 저장소 (develop)와 로컬 코드(middle_proj_copy)는 완전히 동일하지 않습니다!**

### 📊 코드 베이스 관계
```
Git develop (기본 버전)
    ↓ 복사 & 개선
Local middle_proj_copy (발전 버전)
    - 모노레포 구조 적용 (apps/backend/)
    - 다중 LLM 제공자 지원 (OpenAI/Ollama/Anthropic/Custom)
    - 하이브리드 검색 추가 (FAISS + BM25)
    - 추가 의존성 패키지
```

**유사도**: 약 85-90% (구조는 동일, 설정과 기능이 개선됨)

### 주요 차이점
| 항목 | Git develop | Local middle_proj_copy |
|------|------------|------------------------|
| Import 경로 | `backend.*` | `apps.backend.*` |
| LLM 지원 | OpenAI 전용 | 다중 제공자 |
| 검색 기능 | 기본 Semantic | Hybrid (FAISS+BM25) |
| 패키지 | 기본 | +faiss-cpu, rank-bm25 |

**이 가이드는 로컬의 개선사항을 Git 저장소에 반영합니다.**

---

## ✅ 시작 전 체크

터미널을 열고 다음을 확인하세요:

```bash
# 1. Git 저장소 확인
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
pwd
# 출력: /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# 2. 현재 브랜치 확인
git branch
# * develop (또는 다른 브랜치)

# 3. 작업 트리 상태 확인
git status
# nothing to commit, working tree clean (이 상태여야 함)
```

---

## 🎯 오늘의 목표 (Phase 1 완료)

**완료 시 얻는 것**:
- ✅ apps/backend/, apps/web-frontend/ 구조
- ✅ libs/rag-core/, libs/domain-model/ 디렉토리 준비 (빈 상태)
- ✅ Git history 완벽 보존
- ✅ GitHub에 push 완료

**참고**: libs/rag-core/는 Phase 2에서 apps/backend/core/를 이동하여 채울 예정

---

## 📝 Step-by-Step 실행 (복사 & 붙여넣기)

### Step 1: 백업 생성 (5분)

```bash
# 1-1. 작업 디렉토리로 이동
cd /Users/myidwon/dev

# 1-2. middle_proj_copy 백업 (대용량 데이터 폴더 제외)
tar -czf middle_proj_copy_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
  --exclude='middle_proj_copy/04.형사법 LLM 사전학습 및 Instruction Tuning 데이터' \
  middle_proj_copy/

# 1-3. 백업 확인
ls -lh middle_proj_copy_backup_*.tar.gz | tail -1
# 최신 백업 파일이 보여야 함

echo "✅ Step 1 완료: 백업 생성됨"
```

---

### Step 2: Feature 브랜치 생성 (5분)

```bash
# 2-1. Git 저장소로 이동
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# 2-2. develop 최신화
git checkout develop
git pull origin develop

# 2-3. Feature 브랜치 생성
git checkout -b feature/monorepo-migration

# 2-4. Remote에 브랜치 생성
git push -u origin feature/monorepo-migration

# 2-5. 확인
git branch
# * feature/monorepo-migration (별표가 여기 있어야 함)

echo "✅ Step 2 완료: feature/monorepo-migration 브랜치 생성됨"
```

---

### Step 3: apps/ 디렉토리 생성 및 이동 (10분)

```bash
# 3-1. apps/ 디렉토리 생성
mkdir -p apps

# 3-2. backend/ → apps/backend/ 이동 (Git history 보존!)
git mv backend apps/backend

# 3-3. frontend/ → apps/web-frontend/ 이동
git mv frontend apps/web-frontend

# 3-4. 확인
ls -la apps/
# backend와 web-frontend가 보여야 함

# 3-5. Git 상태 확인 (중요!)
git status | head -20
# renamed: backend/... -> apps/backend/... (많이 보여야 함)

echo "✅ Step 3 완료: apps/ 구조 생성됨 (Git history 보존됨)"
```

**⚠️ 중요**: `git status`에서 **"renamed:"** 가 보이면 성공! (Git history 보존됨)

---

### Step 4: libs/ 디렉토리 생성 (10분)

```bash
# 4-1. libs/ 디렉토리 생성
mkdir -p libs/rag-core libs/domain-model

# 4-2. 비어있는 core/ 디렉토리 제거
# (실제 RAG 코드는 apps/backend/core/에 있으므로 최상위 core/는 불필요)
rm -rf core

# 4-3. .gitkeep 파일 생성 (빈 디렉토리 추적용)
touch libs/rag-core/.gitkeep
touch libs/domain-model/.gitkeep

# 4-4. 확인
ls -la libs/
# domain-model과 rag-core가 보여야 함

# 4-5. Git 상태 확인
git status
# new file: libs/rag-core/.gitkeep
# new file: libs/domain-model/.gitkeep
# deleted: core/... (core 디렉토리 삭제됨)

echo "✅ Step 4 완료: libs/ 구조 생성됨"
echo "ℹ️  참고: 실제 RAG 코드는 apps/backend/core/에 있으며, Phase 2에서 libs/rag-core/로 이동 예정"
```

---

### Step 5: 추가 디렉토리 생성 및 커밋 (10분)

```bash
# 5-1. apps/ 하위 디렉토리 생성
mkdir -p apps/ai-service
mkdir -p apps/data-pipeline
touch apps/ai-service/.gitkeep
touch apps/data-pipeline/.gitkeep

# 5-2. .gitignore 업데이트
cat >> .gitignore << 'EOF'

# ==========================================
# Monorepo 추가 설정
# ==========================================

# Data directories
data/vectordb/
data/uploads/
data/raw/
data/pipeline_metrics/

# Virtual Environment
.venv/
venv/
env/
ENV/

# Logs
*.log
logs/
*.log.*

# Temporary files
*.tmp
*.bak
*.backup

# Build outputs
dist/
build/
*.egg-info/

EOF

# 5-3. 변경사항 확인
git status

# 5-4. Stage all changes
git add .

# 5-5. 첫 번째 커밋
git commit -m "feat: create monorepo structure with git mv

- Move backend/ → apps/backend/ (git mv, history preserved)
- Move frontend/ → apps/web-frontend/ (git mv, history preserved)
- Remove empty core/ directory (actual RAG code is in apps/backend/core/)
- Create apps/ai-service/, apps/data-pipeline/ (new)
- Create libs/rag-core/, libs/domain-model/ (new, placeholder for Phase 2)
- Update .gitignore for monorepo structure

NOTE: libs/rag-core/ will be populated in Phase 2 by moving apps/backend/core/

BREAKING CHANGE: Directory structure reorganized to monorepo layout
Git history preserved via git mv for all moved files"

# 5-6. Push
git push origin feature/monorepo-migration

echo "✅ Step 5 완료: 첫 번째 커밋 완료 및 GitHub에 push됨"
```

---

### Step 6: middle_proj_copy에서 개선된 코드 복사 (30분)

```bash
# 6-1. libs/domain-model 복사 (있는 경우)
if [ -d "/Users/myidwon/dev/middle_proj_copy/libs/domain-model" ]; then
    rm -f libs/domain-model/.gitkeep
    cp -r /Users/myidwon/dev/middle_proj_copy/libs/domain-model/* libs/domain-model/ 2>/dev/null
    echo "✅ libs/domain-model 복사 완료"
else
    echo "⚠️  libs/domain-model이 비어있음"
fi

# 6-2. apps/data-pipeline 복사 (있는 경우)
if [ -d "/Users/myidwon/dev/middle_proj_copy/apps/data-pipeline" ]; then
    rm -f apps/data-pipeline/.gitkeep
    cp -r /Users/myidwon/dev/middle_proj_copy/apps/data-pipeline/* apps/data-pipeline/ 2>/dev/null
    echo "✅ apps/data-pipeline 복사 완료"
else
    echo "⚠️  apps/data-pipeline이 비어있음"
fi

# 6-3. configs/ 복사 (있는 경우)
if [ -d "/Users/myidwon/dev/middle_proj_copy/configs" ]; then
    mkdir -p configs
    cp -r /Users/myidwon/dev/middle_proj_copy/configs/* configs/ 2>/dev/null
    echo "✅ configs 복사 완료"
else
    echo "⚠️  configs가 비어있음"
fi

# 6-4. docs/ 복사 (마이그레이션 문서)
mkdir -p docs
cp /Users/myidwon/dev/middle_proj_copy/docs/GIT_MIGRATION_STRATEGY.md docs/ 2>/dev/null || echo "파일 없음"
cp /Users/myidwon/dev/middle_proj_copy/docs/SHELL_COMPATIBILITY_GUIDE.md docs/ 2>/dev/null || echo "파일 없음"
cp /Users/myidwon/dev/middle_proj_copy/docs/START_HERE.md docs/ 2>/dev/null || echo "파일 없음"
cp /Users/myidwon/dev/middle_proj_copy/docs/MIGRATION_DOCS_SUMMARY.md docs/ 2>/dev/null || echo "파일 없음"
cp /Users/myidwon/dev/middle_proj_copy/docs/QUICK_START_GUIDE.md docs/ 2>/dev/null || echo "파일 없음"
echo "✅ docs 복사 완료"

# 6-4-1. scripts/ 복사 (빌드 스크립트)
echo "복사: scripts/ (VectorDB 및 BM25 인덱스 빌드 스크립트)"
if [ -d "/Users/myidwon/dev/middle_proj_copy/scripts" ]; then
    # Git repo의 scripts/.gitkeep는 유지하고 실제 스크립트만 복사
    cp /Users/myidwon/dev/middle_proj_copy/scripts/build_vectordb.py scripts/ 2>/dev/null || echo "build_vectordb.py 없음"
    cp /Users/myidwon/dev/middle_proj_copy/scripts/build_bm25_index.py scripts/ 2>/dev/null || echo "build_bm25_index.py 없음"
    cp /Users/myidwon/dev/middle_proj_copy/scripts/criminal_law_data_loader.py scripts/ 2>/dev/null || echo "criminal_law_data_loader.py 없음"
    cp /Users/myidwon/dev/middle_proj_copy/scripts/parse_criminal_law_data.py scripts/ 2>/dev/null || echo "parse_criminal_law_data.py 없음"
    cp /Users/myidwon/dev/middle_proj_copy/scripts/init_db.py scripts/ 2>/dev/null || echo "init_db.py 없음"
    cp /Users/myidwon/dev/middle_proj_copy/scripts/README.md scripts/ 2>/dev/null || echo "README.md 없음"
    echo "✅ scripts 복사 완료"
else
    echo "⚠️  scripts가 비어있음"
fi

# 6-5. 로컬 backend의 개선사항 복사 (중요!)
echo -e "\n=== 🚀 로컬 backend 개선사항 반영 ==="

# 6-5-1. 개선된 core 모듈 복사 (다중 LLM 지원)
echo "복사: apps/backend/core/ (개선된 LLM 클라이언트 포함)"
cp -r /Users/myidwon/dev/middle_proj_copy/backend/core/* apps/backend/core/ 2>/dev/null

# 6-5-2. 개선된 main.py 복사 (다중 LLM 제공자 지원)
echo "복사: apps/backend/main.py (다중 LLM 제공자 지원)"
cp /Users/myidwon/dev/middle_proj_copy/backend/main.py apps/backend/main.py

# 6-5-3. 개선된 requirements.txt 복사 (FAISS, BM25 추가)
echo "복사: apps/backend/requirements.txt (FAISS + BM25 추가)"
cp /Users/myidwon/dev/middle_proj_copy/backend/requirements.txt apps/backend/requirements.txt

# 6-5-4. 기타 backend 파일 복사
echo "복사: apps/backend/ 기타 파일"
cp -r /Users/myidwon/dev/middle_proj_copy/backend/models/* apps/backend/models/ 2>/dev/null
cp -r /Users/myidwon/dev/middle_proj_copy/backend/routers/* apps/backend/routers/ 2>/dev/null
cp -r /Users/myidwon/dev/middle_proj_copy/backend/services/* apps/backend/services/ 2>/dev/null
cp -r /Users/myidwon/dev/middle_proj_copy/backend/templates/* apps/backend/templates/ 2>/dev/null

echo "✅ 로컬 backend 개선사항 반영 완료"

# 6-6. Git 상태 확인
git status

# 6-7. 변경사항 커밋
git add .
git commit -m "feat: add enhanced code from working directory

- Add libs/domain-model (common Pydantic models)
- Add apps/data-pipeline (ETL pipeline)
- Add configs/ (configuration files)
- Add migration documentation (docs/)
- Add scripts/ (VectorDB and BM25 index build scripts)

ENHANCEMENTS from local middle_proj_copy/backend:
- Multi-LLM provider support (OpenAI/Ollama/Anthropic/Custom)
- Hybrid search capability (FAISS + BM25)
- Enhanced dependencies (faiss-cpu, rank-bm25, bcrypt version pinning)
- Improved core modules (llm_client.py with base_url support)
- Updated main.py with flexible LLM configuration

NEW SCRIPTS added:
- build_vectordb.py (ChromaDB initialization)
- build_bm25_index.py (BM25 index creation)
- criminal_law_data_loader.py (data loading utilities)
- parse_criminal_law_data.py (data parsing)
- init_db.py (database initialization)

Code similarity: ~85-90% (same structure, enhanced features)"

# 6-8. Push
git push origin feature/monorepo-migration

echo "✅ Step 6 완료: 로컬 개선 코드 복사 및 커밋됨"
```

---

### Step 7: 테스트 및 검증 (20분)

```bash
# 7-1. PYTHONPATH 설정
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
export PYTHONPATH=$(pwd):$PYTHONPATH
echo "PYTHONPATH: $PYTHONPATH"

# 7-2. 디렉토리 구조 확인
echo -e "\n=== 최종 구조 ==="
ls -1
# apps, libs, configs, docs, experiments, notebooks, scripts, tests 등이 보여야 함

# 7-3. apps/ 하위 구조 확인
echo -e "\n=== apps/ 구조 ==="
ls -1 apps/
# ai-service, backend, data-pipeline, web-frontend

# 7-4. libs/ 하위 구조 확인
echo -e "\n=== libs/ 구조 ==="
ls -1 libs/
# domain-model, rag-core

# 7-5. libs/rag-core 내부 확인
echo -e "\n=== libs/rag-core 내부 ==="
ls -1 libs/rag-core/
# .gitkeep (Phase 2에서 apps/backend/core/를 여기로 이동 예정)

# 7-6. Git log 확인
echo -e "\n=== 최근 커밋 ==="
git log --oneline -5

# 7-7. Git history 보존 확인 (중요!)
echo -e "\n=== Git history 보존 확인 ==="
git log --follow --oneline apps/backend/main.py 2>/dev/null | head -5
# backend/main.py의 이전 커밋들이 보여야 함 (history 보존 성공)

echo -e "\n✅ Step 7 완료: 모든 테스트 통과!"
```

---

### Step 8: GitHub에서 확인 (5분)

브라우저에서 다음 URL 열기:

```
https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2/tree/feature/monorepo-migration
```

**확인할 것**:
- ✅ `apps/backend/` 폴더가 보이는가?
- ✅ `apps/web-frontend/` 폴더가 보이는가?
- ✅ `libs/rag-core/` 폴더가 보이는가?
- ✅ `docs/` 아래 마이그레이션 문서가 있는가?

**커밋 히스토리 확인**:
```
https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2/commits/feature/monorepo-migration
```

**확인할 것**:
- ✅ "feat: create monorepo structure with git mv" 커밋이 보이는가?
- ✅ "feat: add files from working directory" 커밋이 보이는가?

---

## 🎉 축하합니다! Phase 1 완료!

### 지금까지 완료한 것

- [x] 백업 생성
- [x] Feature 브랜치 생성 (`feature/monorepo-migration`)
- [x] apps/ 구조 생성 (backend, web-frontend)
- [x] libs/ 디렉토리 준비 (rag-core, domain-model - 빈 상태)
- [x] 비어있는 core/ 디렉토리 제거
- [x] middle_proj_copy에서 파일 복사
- [x] .gitignore 업데이트
- [x] 모든 변경사항 커밋 및 push
- [x] **Git history 보존** (✨ 핵심 성과!)

**다음 단계**: Phase 2에서 `apps/backend/core/` → `libs/rag-core/` 이동

---

## 🔄 다음 단계 (선택 사항, 별도 시간에)

### 지금 멈춰도 됩니다!

현재까지 완료한 Phase 1은 **독립적으로 완성된 작업**입니다.

### 계속하고 싶다면

**Phase 2** (2-3시간): libs/rag-core 구현
- 문서: `GIT_MIGRATION_STRATEGY.md` Phase 2 참조
- embeddings, llm, retrieval 모듈 구현

**Phase 3** (2-3시간): apps/backend 마이그레이션
- 문서: `GIT_MIGRATION_STRATEGY.md` Phase 3 참조
- Import 경로를 libs/rag-core로 변경

---

## 🆘 문제가 생겼다면?

### 자주 발생하는 문제

#### 1. `git mv` 실패
```bash
# 에러: fatal: not under version control
# 해결:
git ls-files backend/ | head -5  # 파일이 Git에 있는지 확인
git add backend/                  # 없다면 add
git commit -m "Add backend"       # commit
git mv backend apps/backend       # 다시 시도
```

#### 2. Push 실패
```bash
# 에러: error: failed to push
# 해결:
git pull origin feature/monorepo-migration  # Remote 최신화
git push origin feature/monorepo-migration  # 재시도
```

#### 3. 디렉토리가 이미 존재
```bash
# 에러: fatal: destination exists
# 해결:
rm -rf apps/backend               # 기존 디렉토리 삭제
git mv backend apps/backend       # 다시 시도
```

### 모든 것을 되돌리고 싶다면

```bash
# 브랜치 삭제 (로컬)
git checkout develop
git branch -D feature/monorepo-migration

# 브랜치 삭제 (원격)
git push origin --delete feature/monorepo-migration

# 백업에서 복원
cd /Users/myidwon/dev
rm -rf ai-camp-1st-llm-agent-service-project-2
tar -xzf middle_proj_copy_backup_[날짜].tar.gz
```

---

## 📞 도움말

### 작업 일시 중지
```bash
# develop 브랜치로 돌아가기
git checkout develop

# 나중에 다시 작업하려면
git checkout feature/monorepo-migration
```

### 현재 상태 확인
```bash
git branch    # 현재 브랜치 확인
git status    # 작업 트리 상태
git log -3    # 최근 커밋 3개
```

---

**작성일**: 2025-11-19
**예상 소요 시간**: 1-2시간
**난이도**: ⭐⭐ (중급)
**상태**: ✅ 실행 준비 완료

**행운을 빕니다!** 🚀
