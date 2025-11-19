# 🚀 모노레포 마이그레이션 실행 가이드

> **시작 전 확인**: 아직 아무것도 안 했다면 이 문서를 따라하세요!
> **소요 시간**: 약 1-2시간
> **난이도**: ⭐⭐ (중급)

---

## ✅ 시작하기 전 체크리스트

다음 항목을 확인하고 시작하세요:

- [ ] macOS를 사용하고 있음
- [ ] Git이 설치되어 있음 (`git --version`)
- [ ] GitHub 계정에 로그인되어 있음
- [ ] `/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2` 폴더가 존재함
- [ ] `/Users/myidwon/dev/middle_proj_copy` 폴더가 존재함
- [ ] 시간이 1-2시간 있음 (중간에 멈춰도 됨)

---

## 📌 Step 0: 현재 상태 확인 (5분)

터미널을 열고 다음 명령어를 **하나씩** 실행하세요.

### 0-1. Git 저장소 확인

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
pwd
```

**예상 출력:**
```
/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
```

### 0-2. Git 상태 확인

```bash
git status
```

**예상 출력:**
```
On branch develop
Your branch is up to date with 'origin/develop'.

nothing to commit, working tree clean
```

**⚠️ 만약 "nothing to commit" 이 아니라면:**
```bash
# 변경사항이 있다면 먼저 커밋하거나 stash
git status  # 무엇이 변경되었는지 확인
git stash   # 임시 저장 (나중에 git stash pop으로 복원)
```

### 0-3. 현재 구조 확인

```bash
ls -la
```

**확인할 것:**
- `backend/` 폴더가 있는가? ✅
- `frontend/` 폴더가 있는가? ✅
- `core/` 폴더가 있는가? ✅

**✅ 체크포인트:** 위 3개 폴더가 모두 있으면 계속 진행!

---

## 📦 Step 1: 백업 생성 (5분)

**왜 백업을 하나요?**
실수로 뭔가 잘못되어도 돌아갈 수 있도록 안전장치를 만듭니다.

### 1-1. middle_proj_copy 백업

```bash
cd /Users/myidwon/dev
tar -czf middle_proj_copy_backup_$(date +%Y%m%d_%H%M%S).tar.gz middle_proj_copy/
```

**실행 후 확인:**
```bash
ls -lh middle_proj_copy_backup_*.tar.gz
```

**예상 출력:**
```
-rw-r--r--  1 myidwon  staff   123M Nov 19 14:30 middle_proj_copy_backup_20251119_143000.tar.gz
```

### 1-2. Git 저장소 백업 (선택사항, 하지만 권장)

```bash
cd /Users/myidwon/dev
tar -czf git_repo_backup_$(date +%Y%m%d_%H%M%S).tar.gz ai-camp-1st-llm-agent-service-project-2/
```

**실행 후 확인:**
```bash
ls -lh git_repo_backup_*.tar.gz
```

**✅ 체크포인트:** 백업 파일 2개가 생성되었으면 성공!

---

## 🌿 Step 2: Feature 브랜치 생성 (5분)

**왜 브랜치를 만드나요?**
develop 브랜치를 직접 건드리지 않고, 실험용 브랜치에서 작업합니다.

### 2-1. Git 저장소로 이동

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2
```

### 2-2. develop 브랜치 최신화

```bash
git checkout develop
git pull origin develop
```

**예상 출력:**
```
Already on 'develop'
Your branch is up to date with 'origin/develop'.
```

### 2-3. 새 브랜치 생성

```bash
git checkout -b feature/monorepo-migration
```

**예상 출력:**
```
Switched to a new branch 'feature/monorepo-migration'
```

### 2-4. Remote에 브랜치 생성

```bash
git push -u origin feature/monorepo-migration
```

**예상 출력:**
```
Total 0 (delta 0), reused 0 (delta 0), pack-reused 0
To https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2.git
 * [new branch]      feature/monorepo-migration -> feature/monorepo-migration
branch 'feature/monorepo-migration' set up to track 'origin/feature/monorepo-migration'.
```

### 2-5. 브랜치 확인

```bash
git branch
```

**예상 출력:**
```
  develop
* feature/monorepo-migration
```

**✅ 체크포인트:** `*` 표시가 `feature/monorepo-migration`에 있으면 성공!

---

## 📁 Step 3: apps/ 디렉토리 생성 및 이동 (10분)

**지금부터가 핵심입니다!**
`backend/`, `frontend/`를 `apps/` 아래로 이동합니다.

### 3-1. apps/ 디렉토리 생성

```bash
mkdir -p apps
```

**확인:**
```bash
ls -ld apps
```

**예상 출력:**
```
drwxr-xr-x  2 myidwon  staff  64 Nov 19 14:35 apps
```

### 3-2. backend/ → apps/backend/ 이동 (Git history 보존!)

```bash
git mv backend apps/backend
```

**⚠️ 에러가 발생한다면:**
```bash
# 에러 예: fatal: not under version control
# → backend가 Git에 없다는 뜻 (있을 수 없지만 혹시나)
# 확인:
git ls-files backend/ | head -5
# 파일 목록이 나오면 정상
```

**정상 실행 시 출력:** (아무것도 안 나와도 정상)

### 3-3. frontend/ → apps/web-frontend/ 이동

```bash
git mv frontend apps/web-frontend
```

### 3-4. 확인

```bash
ls -la apps/
```

**예상 출력:**
```
total 0
drwxr-xr-x   4 myidwon  staff  128 Nov 19 14:36 .
drwxr-xr-x  20 myidwon  staff  640 Nov 19 14:36 ..
drwxr-xr-x  12 myidwon  staff  384 Nov 19 14:36 backend
drwxr-xr-x   9 myidwon  staff  288 Nov 19 14:36 web-frontend
```

### 3-5. Git 상태 확인

```bash
git status
```

**예상 출력:**
```
On branch feature/monorepo-migration
Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
        renamed:    backend/core/auth/__init__.py -> apps/backend/core/auth/__init__.py
        renamed:    backend/core/embeddings/embedder.py -> apps/backend/core/embeddings/embedder.py
        ... (수십 개의 renamed 메시지)
        renamed:    frontend/package.json -> apps/web-frontend/package.json
        ... (수십 개의 renamed 메시지)
```

**✅ 핵심 확인:** `renamed:` 라는 단어가 보이면 성공! (Git history 보존됨)

### 3-6. 첫 번째 커밋

```bash
git commit -m "chore: move backend and frontend to apps/ directory

- Move backend/ → apps/backend/ (preserve git history)
- Move frontend/ → apps/web-frontend/ (preserve git history)
- Prepare for monorepo structure

BREAKING CHANGE: Directory structure changed"
```

**예상 출력:**
```
[feature/monorepo-migration a1b2c3d] chore: move backend and frontend to apps/ directory
 150 files changed, 0 insertions(+), 0 deletions(-)
 rename backend/... -> apps/backend/... (100%)
 ...
```

### 3-7. Push

```bash
git push origin feature/monorepo-migration
```

**예상 출력:**
```
Enumerating objects: 5, done.
Counting objects: 100% (5/5), done.
...
To https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2.git
   abc1234..def5678  feature/monorepo-migration -> feature/monorepo-migration
```

**✅ 체크포인트:** Push 성공하면 GitHub에서 확인 가능!

---

## 📚 Step 4: libs/ 디렉토리 생성 및 core 이동 (10분)

### 4-1. libs/ 디렉토리 생성

```bash
mkdir -p libs
```

### 4-2. core/ → libs/rag-core/ 이동

```bash
git mv core libs/rag-core
```

### 4-3. libs/domain-model/ 빈 디렉토리 생성

```bash
mkdir -p libs/domain-model
touch libs/domain-model/.gitkeep
```

**왜 .gitkeep?**
Git은 빈 디렉토리를 추적하지 않으므로, `.gitkeep` 파일을 넣어 디렉토리를 유지합니다.

### 4-4. 확인

```bash
ls -la libs/
```

**예상 출력:**
```
total 0
drwxr-xr-x   4 myidwon  staff  128 Nov 19 14:40 .
drwxr-xr-x  21 myidwon  staff  672 Nov 19 14:40 ..
drwxr-xr-x   2 myidwon  staff   64 Nov 19 14:40 domain-model
drwxr-xr-x   7 myidwon  staff  224 Nov 19 14:40 rag-core
```

### 4-5. Git 상태 확인

```bash
git status
```

**예상 출력:**
```
On branch feature/monorepo-migration
Changes to be committed:
        renamed:    core/auth/__init__.py -> libs/rag-core/auth/__init__.py
        ... (수십 개의 renamed)

Untracked files:
        libs/domain-model/
```

### 4-6. 커밋

```bash
git add libs/
git commit -m "chore: create libs/ directory and move core to libs/rag-core

- Move core/ → libs/rag-core/ (preserve git history)
- Create libs/domain-model/ (empty, for future use)
- Prepare for shared library structure"
```

### 4-7. Push

```bash
git push origin feature/monorepo-migration
```

**✅ 체크포인트:** Push 성공!

---

## 🏗️ Step 5: 추가 디렉토리 생성 (5분)

### 5-1. apps/ 하위 디렉토리 생성

```bash
mkdir -p apps/ai-service
mkdir -p apps/data-pipeline
```

### 5-2. .gitkeep 파일 생성 (빈 디렉토리 유지용)

```bash
touch apps/ai-service/.gitkeep
touch apps/data-pipeline/.gitkeep
```

### 5-3. .gitignore 업데이트

```bash
cat >> .gitignore << 'EOF'

# ==========================================
# Monorepo 추가 설정
# ==========================================

# Data directories (용량 큼, Git 제외)
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
```

### 5-4. 확인

```bash
tail -20 .gitignore
```

**예상 출력:**
방금 추가한 내용이 보여야 함

### 5-5. 커밋

```bash
git add apps/ .gitignore
git commit -m "chore: create apps subdirectories and update .gitignore

- Create apps/ai-service/ (empty)
- Create apps/data-pipeline/ (empty)
- Update .gitignore for monorepo structure"
```

### 5-6. Push

```bash
git push origin feature/monorepo-migration
```

**✅ 체크포인트:** 여기까지 성공하면 기본 구조 완성!

---

## 📋 Step 6: 현재 상태 확인 (5분)

### 6-1. 디렉토리 구조 확인

```bash
tree -L 2 -d apps libs
```

**tree 명령어가 없다면:**
```bash
brew install tree
```

**또는 ls로 확인:**
```bash
echo "=== apps/ ===" && ls -R apps/ | grep ":$" && echo -e "\n=== libs/ ===" && ls -R libs/ | grep ":$"
```

**예상 출력:**
```
apps/
├── ai-service
├── backend
├── data-pipeline
└── web-frontend

libs/
├── domain-model
└── rag-core
```

### 6-2. Git log 확인

```bash
git log --oneline -5
```

**예상 출력:**
```
def5678 chore: create apps subdirectories and update .gitignore
abc1234 chore: create libs/ directory and move core to libs/rag-core
9876543 chore: move backend and frontend to apps/ directory
...
```

### 6-3. GitHub에서 확인

브라우저에서 다음 URL 열기:
```
https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2/tree/feature/monorepo-migration
```

**확인할 것:**
- `apps/backend/` 폴더가 보이는가?
- `apps/web-frontend/` 폴더가 보이는가?
- `libs/rag-core/` 폴더가 보이는가?

**✅ 체크포인트:** GitHub에서 위 폴더들이 보이면 성공!

---

## 📦 Step 7: middle_proj_copy에서 파일 복사 (30분)

**이제 작업했던 파일들을 Git 저장소로 가져옵니다.**

### 7-1. libs/domain-model 복사

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# middle_proj_copy에 domain-model이 있는지 확인
ls -la /Users/myidwon/dev/middle_proj_copy/libs/domain-model/
```

**파일이 있다면:**
```bash
# .gitkeep 삭제 (덮어쓸 거니까)
rm libs/domain-model/.gitkeep

# 복사
cp -r /Users/myidwon/dev/middle_proj_copy/libs/domain-model/* libs/domain-model/

# 확인
ls -la libs/domain-model/
```

**파일이 없다면:**
```bash
echo "domain-model이 비어있음, 다음 단계로"
```

### 7-2. apps/data-pipeline 복사

```bash
# middle_proj_copy에 data-pipeline이 있는지 확인
ls -la /Users/myidwon/dev/middle_proj_copy/apps/data-pipeline/
```

**파일이 있다면:**
```bash
# .gitkeep 삭제
rm apps/data-pipeline/.gitkeep

# 복사
cp -r /Users/myidwon/dev/middle_proj_copy/apps/data-pipeline/* apps/data-pipeline/

# 확인
ls -la apps/data-pipeline/
```

### 7-3. configs/ 복사

```bash
# middle_proj_copy에 configs가 있는지 확인
ls -la /Users/myidwon/dev/middle_proj_copy/configs/
```

**파일이 있다면:**
```bash
# 복사 (configs 디렉토리는 이미 있을 수 있음)
cp -r /Users/myidwon/dev/middle_proj_copy/configs/* configs/ 2>/dev/null || echo "configs 파일 없음"

# 확인
ls -la configs/
```

### 7-4. docs/ 복사 (마이그레이션 문서)

```bash
# 마이그레이션 문서들 복사
cp /Users/myidwon/dev/middle_proj_copy/docs/GIT_MIGRATION_STRATEGY.md docs/ 2>/dev/null || echo "파일 없음"
cp /Users/myidwon/dev/middle_proj_copy/docs/MIGRATION_PLAN_REVISED.md docs/ 2>/dev/null || echo "파일 없음"
cp /Users/myidwon/dev/middle_proj_copy/docs/MIGRATION_ACTION_PLAN.md docs/ 2>/dev/null || echo "파일 없음"
cp /Users/myidwon/dev/middle_proj_copy/docs/SHELL_COMPATIBILITY_GUIDE.md docs/ 2>/dev/null || echo "파일 없음"
cp /Users/myidwon/dev/middle_proj_copy/docs/START_HERE.md docs/ 2>/dev/null || echo "파일 없음"

# 확인
ls -la docs/*.md
```

### 7-5. Git 상태 확인

```bash
git status
```

**예상 출력:**
```
On branch feature/monorepo-migration
Untracked files:
  (use "git add <file>..." to include in what will be committed)
        apps/data-pipeline/...
        libs/domain-model/...
        configs/...
        docs/GIT_MIGRATION_STRATEGY.md
        docs/MIGRATION_PLAN_REVISED.md
        ...
```

### 7-6. 변경사항 커밋

```bash
git add apps/data-pipeline/ libs/domain-model/ configs/ docs/
git commit -m "feat: add files from working directory

- Add libs/domain-model (common Pydantic models)
- Add apps/data-pipeline (ETL pipeline)
- Add configs/ (configuration files)
- Add migration documentation"
```

### 7-7. Push

```bash
git push origin feature/monorepo-migration
```

**✅ 체크포인트:** Push 성공!

---

## 🧪 Step 8: 테스트 (20분)

**지금까지 작업이 제대로 되었는지 확인합니다.**

### 8-1. PYTHONPATH 설정 테스트

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

# PYTHONPATH 설정
export PYTHONPATH=$(pwd):$PYTHONPATH

# 확인
echo $PYTHONPATH
```

**예상 출력:**
```
/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2:...
```

### 8-2. libs/rag-core import 테스트

```bash
python3 << 'EOF'
import sys
print("Python path:", sys.path[:3])

# libs/rag-core가 있는지 확인
import os
rag_core_path = "libs/rag-core"
if os.path.exists(rag_core_path):
    print(f"✅ {rag_core_path} exists")
    files = os.listdir(rag_core_path)
    print(f"Files: {files[:5]}")
else:
    print(f"❌ {rag_core_path} not found")
EOF
```

**예상 출력:**
```
Python path: ['/Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2', ...]
✅ libs/rag-core exists
Files: ['auth', 'embeddings', 'llm', 'retrieval', ...]
```

### 8-3. apps/backend 실행 테스트 (선택)

**⚠️ 주의:** 아직 import 경로를 수정하지 않았다면 에러가 날 수 있습니다.

```bash
cd apps/backend
python3 -c "import sys; print('Backend directory accessible')"
```

**예상 출력:**
```
Backend directory accessible
```

### 8-4. 구조 최종 확인

```bash
cd /Users/myidwon/dev/ai-camp-1st-llm-agent-service-project-2

echo "=== 최종 구조 ==="
ls -1
```

**예상 출력:**
```
apps
configs
data
docs
experiments
libs
notebooks
scripts
tests
...
```

**✅ 체크포인트:** `apps/`, `libs/`가 보이면 성공!

---

## 📝 Step 9: README.md 업데이트 (10분)

### 9-1. README.md 백업

```bash
cp README.md README.md.backup
```

### 9-2. README.md 업데이트

**수동 편집:**
```bash
# VS Code로 열기
code README.md

# 또는 nano로 열기
nano README.md
```

**추가할 내용 (파일 맨 위에):**
```markdown
# LawLaw - 형사법 전문 AI 어시스턴트

> 📦 **Monorepo 구조로 전환됨** (2025-11-19)

## 🏗️ 프로젝트 구조 (Monorepo)

```
lawlaw/
├── apps/                 # 실행 가능한 애플리케이션
│   ├── backend/          # FastAPI 백엔드 (포트 8000)
│   ├── web-frontend/     # React 프론트엔드 (포트 3000)
│   ├── ai-service/       # AI 전용 서비스 (포트 8001)
│   └── data-pipeline/    # ETL 파이프라인
│
├── libs/                 # 공통 라이브러리
│   ├── rag-core/         # RAG 핵심 로직 (DB 비의존)
│   └── domain-model/     # 공통 Pydantic 모델
│
├── configs/              # 설정 파일
├── docs/                 # 문서
├── experiments/          # 실험 코드
├── notebooks/            # Jupyter notebooks
└── scripts/              # 유틸리티 스크립트
```

## 🚀 빠른 시작

### PYTHONPATH 설정 (중요!)

```bash
# Repository root를 PYTHONPATH에 추가
export PYTHONPATH=$(pwd):$PYTHONPATH
```

### 백엔드 실행

```bash
cd apps/backend
python main.py
```

### 프론트엔드 실행

```bash
cd apps/web-frontend
npm install
npm start
```

## 📚 마이그레이션 문서

- [시작 가이드](docs/START_HERE.md) - 처음부터 따라하기
- [마이그레이션 전략](docs/GIT_MIGRATION_STRATEGY.md) - 상세 기술 가이드
- [Shell 호환성](docs/SHELL_COMPATIBILITY_GUIDE.md) - macOS/zsh 가이드

---

(기존 README 내용은 여기 아래에...)
```

### 9-3. 커밋

```bash
git add README.md
git commit -m "docs: update README for monorepo structure

- Add monorepo directory structure
- Add PYTHONPATH setup instructions
- Add links to migration documentation"
```

### 9-4. Push

```bash
git push origin feature/monorepo-migration
```

**✅ 체크포인트:** README 업데이트 완료!

---

## 🎉 완료! 다음 단계는? (10분)

### ✅ 지금까지 완료한 것

- [x] 백업 생성
- [x] Feature 브랜치 생성
- [x] apps/ 구조 생성 (backend, web-frontend)
- [x] libs/ 구조 생성 (rag-core, domain-model)
- [x] middle_proj_copy에서 파일 복사
- [x] .gitignore 업데이트
- [x] README.md 업데이트
- [x] 모든 변경사항 커밋 및 push

### 🎯 GitHub에서 확인

브라우저에서 확인:
```
https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2/tree/feature/monorepo-migration
```

**확인할 것:**
- apps/backend/ ✅
- apps/web-frontend/ ✅
- libs/rag-core/ ✅
- docs/START_HERE.md ✅

### 📋 다음 작업 (Phase 2-3)

**지금은 여기서 멈춰도 됩니다!** 다음 작업은 별도로 진행:

1. **libs/rag-core 구현** (2-3시간)
   - 문서: `docs/GIT_MIGRATION_STRATEGY.md` Phase 2 참조
   - embeddings, llm, retrieval 모듈 구현

2. **apps/backend 마이그레이션** (2-3시간)
   - 문서: `docs/GIT_MIGRATION_STRATEGY.md` Phase 3 참조
   - Import 경로를 libs/rag-core로 변경

3. **테스트 및 검증** (1시간)
   - 백엔드/프론트엔드 실행 테스트
   - 통합 테스트 스크립트 실행

4. **PR 생성** (1시간)
   - GitHub에서 Pull Request 생성
   - 팀원 리뷰 요청

### 🔄 현재 브랜치에서 나가기 (작업 일시 중지)

```bash
# develop 브랜치로 돌아가기
git checkout develop

# 나중에 다시 작업하려면
git checkout feature/monorepo-migration
```

---

## ❓ 문제가 생겼다면?

### 자주 발생하는 문제

#### 1. `git mv` 실패

**에러:**
```
fatal: not under version control
```

**해결:**
```bash
# 파일이 Git에 있는지 확인
git ls-files backend/ | head -5

# 없다면 git add 후 다시 시도
git add backend/
git commit -m "Add backend to git"
git mv backend apps/backend
```

#### 2. Push 실패

**에러:**
```
error: failed to push some refs
```

**해결:**
```bash
# Remote 최신화 후 재시도
git pull origin feature/monorepo-migration
git push origin feature/monorepo-migration
```

#### 3. 디렉토리가 이미 존재

**에러:**
```
fatal: destination exists
```

**해결:**
```bash
# 기존 디렉토리 삭제 후 재시도
rm -rf apps/backend
git mv backend apps/backend
```

### 🆘 모든 것을 되돌리고 싶다면

```bash
# 브랜치 삭제 (로컬)
git checkout develop
git branch -D feature/monorepo-migration

# 브랜치 삭제 (원격)
git push origin --delete feature/monorepo-migration

# 백업에서 복원
cd /Users/myidwon/dev
rm -rf ai-camp-1st-llm-agent-service-project-2
tar -xzf git_repo_backup_[날짜].tar.gz
```

---

## 📞 도움이 필요하다면

1. **GitHub Issues**: 팀원들에게 질문
2. **문서 참조**:
   - `docs/GIT_MIGRATION_STRATEGY.md`
   - `docs/SHELL_COMPATIBILITY_GUIDE.md`
3. **Git 로그 확인**: `git log --oneline -10`

---

**축하합니다! 🎉**

모노레포 구조의 기본 골격을 성공적으로 만들었습니다.
이제 팀원들과 공유하고, 다음 단계를 계획하세요!

**작성일**: 2025-11-19
**예상 소요 시간**: 1-2시간
**난이도**: ⭐⭐ (중급)
**상태**: ✅ 실행 준비 완료
