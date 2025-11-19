# Shell 호환성 및 Git 명령어 가이드

> **macOS 기본 쉘**: zsh (Catalina 이후)
> **작성일**: 2025-11-19

---

## 🐚 macOS Shell 상황

### 확인 방법
```bash
echo $SHELL
# /bin/zsh  ← macOS Catalina 이후 기본
# /bin/bash ← 구버전 macOS
```

---

## ❌ 문제: `shopt -s dotglob`

### 문제점
```bash
shopt -s dotglob  # ❌ zsh에서 작동 안 함 (bash 전용)
```

### ✅ 해결책: zsh 대응

#### Option 1: zsh 네이티브 방식 (권장)
```bash
# zsh에서 숨김 파일 포함하여 이동
setopt dotglob  # zsh 방식
mv backend/* apps/backend/
unsetopt dotglob
```

#### Option 2: 명시적으로 숨김 파일 포함
```bash
# .(점)으로 시작하는 파일도 명시
mv backend/* backend/.* apps/backend/ 2>/dev/null
```

#### Option 3: 쉘 관계없이 동작 (가장 안전)
```bash
# find + cp/mv 조합
find backend -maxdepth 1 -mindepth 1 -exec mv {} apps/backend/ \;
```

#### Option 4: rsync (가장 확실)
```bash
# rsync는 모든 파일 포함 (숨김 파일도)
rsync -av backend/ apps/backend/
rm -rf backend/
```

---

## 🤔 `mv` vs `git mv` 비교

### 핵심 차이점

| 항목 | `mv` | `git mv` |
|------|------|----------|
| **Git history 추적** | ❌ 새 파일로 인식 | ✅ 이동으로 인식 |
| **Rename 감지** | 🟡 유사도 기반 (불완전) | ✅ 명시적 기록 |
| **파일 개수** | 많아도 OK | 많으면 느림 |
| **Unstaged 상태** | 필요 없음 | Git 관리 필수 |
| **실수 복구** | 어려움 | `git reset` 가능 |

---

## 🎯 상황별 권장 방법

### Case 1: Git 관리되는 파일 이동 (우리 경우) ⭐

**권장: `git mv`**

```bash
# ✅ Git history 보존됨
git mv backend apps/backend
git mv frontend apps/web-frontend

# Git이 이동을 명시적으로 추적
git status
# renamed: backend/main.py -> apps/backend/main.py
```

**장점:**
- ✅ Git history 완벽 보존
- ✅ `git log --follow` 동작
- ✅ Blame 추적 가능
- ✅ 실수 시 `git reset` 가능

**단점:**
- ⚠️ Git 관리되는 파일만 가능
- ⚠️ 파일 많으면 느림

---

### Case 2: 디렉토리 전체 이동 (간단한 경우)

**권장: `git mv` (디렉토리 단위)**

```bash
# ✅ 디렉토리 전체 이동 (한 번에)
git mv backend apps/backend
git mv frontend apps/web-frontend

# 확인
git status
# renamed: backend -> apps/backend
# renamed: frontend -> apps/web-frontend
```

이게 **가장 간단하고 안전**합니다!

---

### Case 3: Git 관리 안 되는 파일 포함 (예: node_modules)

**권장: `mv` + `git add`**

```bash
# 1. 일반 mv로 이동
mv backend apps/backend
mv frontend apps/web-frontend

# 2. Git에 변경사항 등록
git add apps/backend apps/web-frontend
git rm -r backend frontend

# 3. Git이 rename 감지 (유사도 기반)
git status
# renamed: backend/main.py -> apps/backend/main.py (similarity 95%)
```

**장점:**
- ✅ Git 관리 안 되는 파일도 이동
- ✅ 빠름

**단점:**
- ⚠️ Rename 감지가 불완전할 수 있음
- ⚠️ Git history 추적이 덜 명확

---

## 🎯 우리 프로젝트 권장 방법

### ✅ 최종 권장: `git mv` (디렉토리 단위)

**이유:**
1. **Git history 완벽 보존** (가장 중요!)
2. **간단함** (디렉토리 통째로 이동)
3. **안전함** (실수 시 복구 쉬움)

**실행 방법:**

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# 1. apps/ 디렉토리 생성
mkdir -p apps

# 2. Git mv로 이동 (history 보존)
git mv backend apps/backend
git mv frontend apps/web-frontend
git mv core libs/rag-core

# 3. 확인
git status
# renamed: backend -> apps/backend (100%)
# renamed: frontend -> apps/web-frontend (100%)
# renamed: core -> libs/rag-core (100%)

# 4. 커밋
git commit -m "chore: reorganize to monorepo structure

- Move backend → apps/backend
- Move frontend → apps/web-frontend
- Move core → libs/rag-core

Git history preserved via git mv"

# 5. Push
git push origin feature/monorepo-migration
```

---

## 🔍 `git mv` 동작 원리

### `git mv`는 사실 3단계 조합입니다:

```bash
# git mv backend apps/backend

# 실제로는 이렇게 동작:
# 1. mv backend apps/backend
# 2. git rm backend
# 3. git add apps/backend

# 하지만 Git이 "rename"으로 명시적 기록!
```

### History 추적 테스트

```bash
# 파일 이동 후에도 히스토리 추적 가능
git log --follow apps/backend/main.py

# Blame도 추적 가능
git blame apps/backend/main.py
```

---

## ⚠️ 주의사항

### 1. `.gitignore`된 파일은 `git mv` 안 됨

```bash
# node_modules 같은 건 Git 관리 안 됨
git mv backend/node_modules apps/backend/node_modules
# error: not under version control

# 해결: 그냥 mv 사용 (또는 나중에 npm install)
mv backend/node_modules apps/backend/node_modules
```

### 2. 큰 디렉토리는 느릴 수 있음

```bash
# 파일 수천 개면 git mv가 느릴 수 있음
# 하지만 우리 프로젝트는 괜찮음 (backend/, frontend/ 정도)
```

### 3. Rename 감지율

```bash
# Git의 rename 감지 임계값 (기본 50%)
git config merge.renameLimit 999999

# 또는 commit 시 명시
git commit -m "..." --find-renames=40%
```

---

## 📋 수정된 마이그레이션 스크립트

### ✅ macOS (zsh) 호환 버전

```bash
#!/bin/zsh
# 또는 #!/bin/bash (어느 쪽이든 동작)

echo "======================================"
echo "LawLaw Monorepo Migration - Phase 0-1"
echo "======================================"

# 0. 백업
echo -e "\n[Step 0] Creating backups..."
cd /Users/myidwon/dev
tar -czf middle_proj_copy_backup_$(date +%Y%m%d_%H%M%S).tar.gz middle_proj_copy/
echo "✅ Backup created"

# 1. Git repo로 이동
echo -e "\n[Step 1] Moving to Git repository..."
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# 2. develop 최신화
echo -e "\n[Step 2] Updating develop branch..."
git checkout develop
git pull origin develop

# 3. Feature 브랜치 생성
echo -e "\n[Step 3] Creating feature branch..."
git checkout -b feature/monorepo-migration
git push -u origin feature/monorepo-migration

# 4. 디렉토리 생성
echo -e "\n[Step 4] Creating directories..."
mkdir -p apps libs

# 5. Git mv로 이동 (history 보존)
echo -e "\n[Step 5] Moving directories with git mv..."

# backend → apps/backend
if [ -d "backend" ]; then
    git mv backend apps/backend
    echo "✅ Moved backend → apps/backend"
else
    echo "⚠️  backend directory not found"
fi

# frontend → apps/web-frontend
if [ -d "frontend" ]; then
    git mv frontend apps/web-frontend
    echo "✅ Moved frontend → apps/web-frontend"
else
    echo "⚠️  frontend directory not found"
fi

# core → libs/rag-core
if [ -d "core" ]; then
    git mv core libs/rag-core
    echo "✅ Moved core → libs/rag-core"
else
    echo "⚠️  core directory not found"
fi

# 6. 커밋
echo -e "\n[Step 6] Committing changes..."
git commit -m "chore: reorganize to monorepo structure

- Move backend → apps/backend (git mv)
- Move frontend → apps/web-frontend (git mv)
- Move core → libs/rag-core (git mv)

Git history preserved via git mv"

# 7. Push
echo -e "\n[Step 7] Pushing to remote..."
git push origin feature/monorepo-migration

# 8. 추가 디렉토리 생성
echo -e "\n[Step 8] Creating additional directories..."
mkdir -p apps/ai-service apps/data-pipeline libs/domain-model

# 9. .gitignore 업데이트
echo -e "\n[Step 9] Updating .gitignore..."
cat >> .gitignore << 'EOF'

# ==========================================
# Monorepo 추가 설정
# ==========================================

# Data directories
data/vectordb/
data/uploads/
data/raw/

# Virtual Environment
.venv/
venv/
ENV/

# Logs
*.log
logs/

# Temporary files
*.bak
*.backup
*.tmp

EOF

# 10. 최종 커밋
echo -e "\n[Step 10] Final commit..."
git add apps/ libs/ .gitignore
git commit -m "chore: add monorepo subdirectories and update .gitignore"
git push origin feature/monorepo-migration

echo -e "\n======================================"
echo "✅ Phase 0-1 Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Copy files from middle_proj_copy"
echo "2. Implement libs/rag-core"
echo "3. Migrate apps/backend"
echo ""
echo "Git history preserved: ✅"
echo "Branch: feature/monorepo-migration"
```

---

## 🎯 최종 권장사항

### 1. **쉘 호환성**: shopt 제거

```bash
# ❌ 사용 금지 (bash 전용)
shopt -s dotglob

# ✅ 대신 git mv 사용 (쉘 무관)
git mv backend apps/backend
```

### 2. **파일 이동**: git mv 사용

```bash
# ✅ 권장: Git history 보존
git mv backend apps/backend

# ❌ 비권장: History 손실 위험
mv backend apps/backend
git add apps/backend
git rm -r backend
```

### 3. **스크립트**: zsh 호환 버전 사용

위의 "수정된 마이그레이션 스크립트" 사용

---

## 📊 비교 요약

| 방법 | Git History | 속도 | 안전성 | 권장도 |
|------|------------|------|--------|--------|
| **`git mv`** | ✅ 완벽 | 🟡 중간 | ✅ 높음 | ⭐⭐⭐⭐⭐ |
| **`mv` + git add/rm** | 🟡 불완전 | ✅ 빠름 | 🟡 중간 | ⭐⭐⭐ |
| **`rsync` + git** | ❌ 새 파일 | ✅ 빠름 | 🟡 중간 | ⭐⭐ |

**결론: `git mv` 사용!** ✅

---

**작성일**: 2025-11-19
**작성자**: Claude (AI Assistant)
**대상 OS**: macOS (zsh)
