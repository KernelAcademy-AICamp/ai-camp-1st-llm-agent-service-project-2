# Scripts

프로젝트 초기화 및 데이터 파이프라인 스크립트

## 📁 파일 목록

| 파일 | 용도 | 사용 시점 |
|------|------|----------|
| `init_db.py` | PostgreSQL/SQLite 테이블 생성 | 최초 1회 |
| `build_vectordb.py` | Vector DB (ChromaDB) 구축 | 최초 1회 또는 재인덱싱 시 |
| `build_bm25_index.py` | BM25 인덱스 구축 | Vector DB 구축 후 |

---

## 🚀 사용 방법

### 1. 데이터베이스 초기화

```bash
# PostgreSQL/SQLite 테이블 생성
python scripts/init_db.py

# 테스트 유저 생성 (옵션)
CREATE_TEST_USER=true python scripts/init_db.py
```

**결과:**
- SQLite: `data/lawlaw.db` 생성
- 테이블: `users`, `precedents`, `precedent_feedback` 등

---

### 2. Vector DB 구축

#### Option A: 판례 크롤링 데이터 사용 (추천)
```bash
# 1. 백엔드 서버로 판례 100개 크롤링
# (백엔드가 실행 중이어야 함)

# 2. DB에서 판례 로드하여 Vector DB 구축
python scripts/build_vectordb.py \
    --source db \
    --max_docs 100 \
    --build_bm25
```

#### Option B: AI-Hub 데이터 사용 (원본 방식)
```bash
# AI-Hub 형사법 데이터셋 필요
python scripts/build_vectordb.py \
    --source aihub \
    --data_dir /path/to/aihub/data \
    --max_files 10 \
    --max_docs 1000 \
    --build_bm25
```

#### 빠른 테스트 (10개 문서)
```bash
python scripts/build_vectordb.py \
    --source db \
    --max_docs 10 \
    --build_bm25 \
    --test_query "절도죄의 구성요건은?"
```

**결과:**
- ChromaDB: `apps/data/vectordb/chroma_criminal_law/`
- BM25 Index: `apps/data/vectordb/bm25/`

---

### 3. BM25 인덱스만 재구축

Vector DB는 이미 있고 BM25만 다시 만들고 싶을 때:

```bash
python scripts/build_bm25_index.py
```

---

## 📊 데이터 소스

### 1. PostgreSQL Database (기본)
- 판례 크롤러로 수집한 데이터
- `precedents` 테이블에서 로드

### 2. AI-Hub 형사법 데이터셋
- 40,782개 파일 (전체)
- 경로: `04.형사법 LLM 사전학습 및 Instruction Tuning 데이터/`

---

## ⚙️ 파라미터 설명

### build_vectordb.py

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `--source` | `db` | 데이터 소스 (`db` 또는 `aihub`) |
| `--db_type` | `chroma` | Vector DB 종류 (`chroma`, `faiss`) |
| `--max_docs` | `None` | 최대 문서 수 (테스트용) |
| `--max_files` | `None` | 최대 파일 수 (AI-Hub 사용 시) |
| `--build_bm25` | `False` | BM25 인덱스도 함께 구축 |
| `--test_query` | 기본 쿼리 | 구축 후 테스트 검색 |

---

## 🔧 문제 해결

### Vector DB가 비어있다고 나올 때
```bash
# 판례가 DB에 있는지 확인
sqlite3 data/lawlaw.db "SELECT COUNT(*) FROM precedents;"

# 없으면 크롤러 실행 (백엔드 필요)
# 프론트엔드에서 "최신 판례 10건 가져오기" 버튼 클릭
```

### Import 오류
```bash
# PYTHONPATH 설정
export PYTHONPATH=/Users/myidwon/dev/middle_proj:$PYTHONPATH
python scripts/build_vectordb.py
```

### Embedding 속도가 느릴 때
```bash
# GPU 사용 (CUDA 설치 필요)
DEVICE=cuda python scripts/build_vectordb.py

# 배치 사이즈 증가
# configs/config.py에서 batch_size 조정
```

---

## 📝 실행 예시

```bash
# 전체 워크플로우
# 1. DB 초기화
python scripts/init_db.py

# 2. 백엔드 실행 (판례 크롤링용)
cd apps/backend
uvicorn main:app --reload

# 3. 프론트엔드에서 판례 100개 크롤링
# (또는 API 직접 호출)

# 4. Vector DB 구축
python scripts/build_vectordb.py --source db --max_docs 100 --build_bm25

# 5. 백엔드 재시작
# 로그 확인: "Vector DB loaded with 100 documents"
```

---

## 📈 예상 소요 시간

| 작업 | 문서 수 | 소요 시간 |
|------|---------|----------|
| DB 초기화 | - | 1초 |
| Vector DB (10개) | 10 | 30초 |
| Vector DB (100개) | 100 | 3분 |
| Vector DB (1,000개) | 1,000 | 30분 |
| Vector DB (10,000개) | 10,000 | 3시간 |
| BM25 (100개) | 100 | 5초 |
| BM25 (10,000개) | 10,000 | 1분 |

---

## 🎯 추천 설정

### 개발/테스트
```bash
python scripts/build_vectordb.py --max_docs 100 --build_bm25
```

### 데모/평가
```bash
python scripts/build_vectordb.py --max_docs 500 --build_bm25
```

### 프로덕션
```bash
python scripts/build_vectordb.py --build_bm25
# 모든 데이터 사용
```
