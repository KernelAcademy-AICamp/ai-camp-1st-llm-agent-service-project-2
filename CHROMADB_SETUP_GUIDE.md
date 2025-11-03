# ChromaDB RAG 시스템 구축 가이드

## 📋 개요

ChromaDB를 사용한 교통 관련 법률 RAG (Retrieval-Augmented Generation) 시스템 구축 가이드

---

## 🎯 주요 기능

### 1. 유사 판례 검색
- 의미적 유사도 기반 판례 검색
- 메타데이터 필터링 (법원명, 케이스 타입)
- Top-K 결과 반환

### 2. 법률 질의응답 (RAG)
- 질문에 대한 유사 판례 자동 검색
- GPT-4를 활용한 답변 생성
- 출처 판례 제공

### 3. 판례 추천
- 특정 판례와 유사한 다른 판례 추천
- 코사인 유사도 기반

---

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# OpenAI API 키 설정
export OPENAI_API_KEY='your-openai-api-key'

# (선택) ChromaDB 디렉토리 설정
export CHROMA_DB_PATH='./chroma_db'
```

### 2. 샘플 테스트 (추천)

**20건 샘플로 빠른 테스트**:
```bash
python3 scripts/test_chromadb_with_sample.py \
  --openai-api-key $OPENAI_API_KEY \
  --sample-size 20
```

**예상 시간**: 1~2분
**예상 비용**: ~$0.01 (OpenAI)

**출력 예시**:
```
2025-11-03 18:00:00 - INFO - 샘플 데이터 추출 중: 20건
2025-11-03 18:00:01 - INFO - ChromaDB 초기화 완료: ./chroma_db_test
2025-11-03 18:00:02 - INFO - 판례 임베딩 생성 시작: 20건
...
2025-11-03 18:01:30 - INFO - ✅ 전체 임베딩 생성 완료
2025-11-03 18:01:30 - INFO - ChromaDB 총 벡터 수: 20
```

---

### 3. 전체 데이터 임베딩 생성

**11,769건 전체 데이터**:
```bash
python3 scripts/create_embeddings_chromadb.py \
  unified_traffic_data/unified_traffic_data_20251103_174822.json \
  --openai-api-key $OPENAI_API_KEY \
  --chroma-dir ./chroma_db \
  --reset
```

**예상 시간**: 15~20분
**예상 비용**: ~$0.47 (OpenAI)

**주요 옵션**:
- `--reset`: 기존 컬렉션 삭제 후 재생성
- `--chroma-dir`: ChromaDB 저장 디렉토리
- `--test-query`: 완료 후 테스트 쿼리

---

### 4. API 서버 시작

```bash
# FastAPI 서버 시작
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**API 문서**: http://localhost:8000/docs

---

## 📡 API 사용 예시

### 1. 유사 판례 검색

```bash
curl -X POST "http://localhost:8000/api/v1/rag/similar-cases" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "무보험 차량 교통사고",
    "top_k": 5,
    "case_type": "판례"
  }'
```

**응답**:
```json
{
  "query": "무보험 차량 교통사고",
  "results": [
    {
      "case_id": "판례_79038",
      "case_type": "판례",
      "사건번호": "2007노799",
      "법원명": "전주지방법원",
      "선고일자": "2008.02.15",
      "판결요지": "교통사고처리특례법 제4조 제1항은...",
      "similarity_score": 0.92
    }
  ],
  "total_found": 5
}
```

---

### 2. 법률 질의응답 (RAG)

```bash
curl -X POST "http://localhost:8000/api/v1/rag/legal-qa" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "무보험 차량으로 교통사고를 냈을 때 처벌은 어떻게 되나요?",
    "top_k": 3,
    "include_sources": true
  }'
```

**응답**:
```json
{
  "question": "무보험 차량으로 교통사고를 냈을 때 처벌은 어떻게 되나요?",
  "answer": "교통사고처리특례법 제4조 제1항에 따르면, 교통사고를 일으킨 차량이 보험에 가입되어 있지 않은 경우 공소를 제기할 수 있습니다...",
  "sources": [
    {
      "case_id": "판례_79038",
      "사건번호": "2007노799",
      "판결요지": "...",
      "similarity_score": 0.92
    }
  ]
}
```

---

### 3. 판례 추천

```bash
curl -X POST "http://localhost:8000/api/v1/rag/recommend-cases" \
  -H "Content-Type: application/json" \
  -d '{
    "case_id": "판례_79038",
    "top_k": 5
  }'
```

---

### 4. 통계 조회

```bash
curl "http://localhost:8000/api/v1/rag/stats"
```

**응답**:
```json
{
  "total_cases": 11769,
  "collection_name": "traffic_legal_cases",
  "type_distribution": {
    "판례": 9198,
    "결정례": 466,
    "해석례": 12,
    "법령": 2093
  },
  "embedding_model": "text-embedding-3-small",
  "embedding_dimension": 1536
}
```

---

## 🔧 Python 코드 예시

### 직접 ChromaDB 사용

```python
import chromadb
from chromadb.config import Settings
from openai import OpenAI

# ChromaDB 클라이언트
chroma_client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=Settings(anonymized_telemetry=False)
)

# 컬렉션 가져오기
collection = chroma_client.get_collection("traffic_legal_cases")

# OpenAI 클라이언트
openai_client = OpenAI(api_key="your-api-key")

# 쿼리 임베딩 생성
query = "음주운전 처벌"
response = openai_client.embeddings.create(
    model="text-embedding-3-small",
    input=query
)
query_embedding = response.data[0].embedding

# 검색
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    include=["metadatas", "documents", "distances"]
)

# 결과 출력
for i, (metadata, distance) in enumerate(zip(
    results['metadatas'][0],
    results['distances'][0]
)):
    print(f"{i+1}. 사건번호: {metadata['사건번호']}")
    print(f"   법원: {metadata['법원명']}")
    print(f"   유사도: {1.0 - distance:.4f}")
```

---

## 📊 데이터 구조

### ChromaDB 컬렉션 구조

**컬렉션 이름**: `traffic_legal_cases`

**ID 형식**: `{case_type}_{판례일련번호}`
- 예: `판례_79038`, `법령_12345`

**메타데이터 필드**:
```python
{
    "case_type": "판례",  # 판례, 결정례, 해석례, 법령
    "사건번호": "2007노799",
    "법원명": "전주지방법원",
    "선고일자": "2008.02.15",
    "판례일련번호": "79038",
    "판결요지": "교통사고처리특례법 제4조...",  # 500자 제한
    "CSV존재여부": "True"
}
```

**임베딩 벡터**: 1536차원 (text-embedding-3-small)

**문서 (Documents)**: 전체 텍스트 (판시사항 + 판결요지 + 이유 + 전문)

---

## 💡 주요 기능 설명

### 1. 임베딩 생성 전략

**텍스트 조합 우선순위**:
```
1. 사건 정보 (사건번호, 법원, 선고일자)
2. 판시사항
3. 판결요지
4. 이유 (최대 2000자)
5. 전문 (최대 3000자)
6. 참조조문
```

**총 길이 제한**: 8000자

---

### 2. 검색 알고리즘

**유사도 계산**:
- 코사인 유사도 (Cosine Similarity)
- `similarity_score = 1.0 - distance`

**필터링**:
- `case_type`: 판례, 결정례, 해석례, 법령
- `법원명`: 대법원, 고등법원 등
- 복합 필터 가능

---

### 3. RAG 프롬프트 전략

**시스템 프롬프트**:
```
당신은 대한민국 교통 관련 법률 전문가입니다.
주어진 판례를 참조하여 사용자의 질문에 정확하고 명확하게 답변하세요.
```

**유저 프롬프트**:
```
===== 참조 판례 =====
[판례 1] ...
[판례 2] ...
[판례 3] ...

===== 질문 =====
{사용자 질문}
```

**GPT 설정**:
- 모델: `gpt-4o-mini` (빠르고 저렴) 또는 `gpt-4` (높은 정확도)
- Temperature: `0.3` (일관된 답변)
- Max Tokens: `1000`

---

## 🔍 필터링 예시

### 법원별 검색

```python
# 대법원 판례만 검색
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"법원명": "대법원"}
)
```

### 타입별 검색

```python
# 판례만 검색
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={"case_type": "판례"}
)
```

### 복합 필터

```python
# 대법원 판례만
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    where={
        "$and": [
            {"case_type": "판례"},
            {"법원명": "대법원"}
        ]
    }
)
```

---

## 📈 성능 및 비용

### OpenAI API 비용

**임베딩 생성 비용** (text-embedding-3-small):
- 가격: $0.00002 / 1K tokens
- 평균 케이스: ~1500 tokens
- 11,769건: ~17.65M tokens
- **총 비용**: ~$0.47

**GPT API 비용** (gpt-4o-mini):
- 입력: $0.00015 / 1K tokens
- 출력: $0.00060 / 1K tokens
- 평균 질문: 입력 3K tokens, 출력 500 tokens
- **질문당 비용**: ~$0.0007

---

### 검색 성능

| 데이터 규모 | 검색 시간 | 메모리 사용 |
|------------|---------|----------|
| 100건 | ~5ms | ~50MB |
| 1,000건 | ~10ms | ~200MB |
| 10,000건 | ~15ms | ~1GB |
| 100,000건 | ~30ms | ~5GB |

**11,769건**: ~12ms 검색 시간

---

## 🛠️ 트러블슈팅

### 1. OpenAI API 키 오류

```bash
Error: OpenAI API 키가 필요합니다
```

**해결**:
```bash
export OPENAI_API_KEY='sk-...'
```

---

### 2. ChromaDB 컬렉션을 찾을 수 없음

```bash
Error: ChromaDB 컬렉션을 찾을 수 없습니다
```

**해결**: 임베딩 먼저 생성
```bash
python3 scripts/create_embeddings_chromadb.py ...
```

---

### 3. 메모리 부족

**증상**: 전체 데이터 임베딩 시 메모리 초과

**해결**: 배치 크기 줄이기
```python
# create_embeddings_chromadb.py 수정
batch_size = 50  # 기본 100 → 50으로 변경
```

---

### 4. 임베딩 생성 속도 느림

**개선 방법**:
1. 배치 크기 증가 (메모리 허용 시)
2. 병렬 처리 (추후 구현)
3. GPU 사용 (sentence-transformers로 로컬 임베딩)

---

## 🔄 증분 업데이트

### 신규 판례 추가

```python
from scripts.create_embeddings_chromadb import ChromaDBEmbeddingCreator

creator = ChromaDBEmbeddingCreator(
    openai_api_key="your-key",
    chroma_persist_dir="./chroma_db"
)

# 기존 컬렉션 사용
creator.collection = creator.chroma_client.get_collection("traffic_legal_cases")

# 신규 케이스만 추가
new_cases = [...]  # 크롤링된 신규 케이스
creator.add_cases_to_chromadb(new_cases, "판례")
```

---

## 📚 참고 자료

- [ChromaDB 공식 문서](https://docs.trychroma.com/)
- [OpenAI Embeddings API](https://platform.openai.com/docs/guides/embeddings)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)

---

## ✅ 체크리스트

### 초기 설정
- [ ] ChromaDB, OpenAI 설치
- [ ] OpenAI API 키 발급 및 설정
- [ ] 환경변수 설정

### 테스트
- [ ] 샘플 테스트 (20건)
- [ ] API 엔드포인트 테스트
- [ ] 검색 결과 확인

### 프로덕션
- [ ] 전체 데이터 임베딩 (11,769건)
- [ ] API 서버 시작
- [ ] 모니터링 설정

---

**작성일**: 2025-11-03
**버전**: 1.0
**데이터**: unified_traffic_data (11,769건)
