# RAG 및 임베딩을 위한 데이터 구조 분석

## 🎯 요구사항

1. **사건별 임베딩 생성**
2. **RAG (Retrieval-Augmented Generation) 시스템 구축**
3. **비슷한 판례 추천**
4. **관련 법령 추천**

---

## 📊 현재 데이터 구조

### 통합 JSON (현재)

```json
{
  "수집정보": {...},
  "판례": [
    {
      "검색어": "교통사고",
      "사건번호": "2007노799",
      "상세정보": {...},
      "메타데이터": {...}
    },
    // 11,769건이 하나의 배열에...
  ],
  "결정례": [...],
  "해석례": [...],
  "법령": [...]
}
```

**파일:** `unified_traffic_data_20251103_174822.json` (444MB)

---

## ❓ 질문: 사건별로 JSON 파일을 만들어야 하나?

### 답변: **아니오, 하나의 큰 파일이 더 좋습니다!**

하지만 **Vector Database (벡터 DB)**를 사용해야 합니다.

---

## 🎯 RAG 시스템 구조 권장안

### Option 1: Vector Database 사용 (강력 추천 ⭐⭐⭐⭐⭐)

```
통합 JSON (444MB)
    ↓
임베딩 생성 (사건별)
    ↓
Vector Database (Qdrant/Pinecone/Weaviate)
    ├─ 판례 11,769개 벡터
    ├─ 메타데이터 포함
    └─ 빠른 유사도 검색
    ↓
RAG 시스템
    ├─ 유사 판례 검색
    ├─ 관련 법령 추천
    └─ LLM 답변 생성
```

**장점:**
- ✅ 빠른 검색 (벡터 인덱스)
- ✅ 확장 가능 (수백만 건도 가능)
- ✅ 복잡한 쿼리 지원
- ✅ 메타데이터 필터링 (날짜, 법원, 키워드)

**단점:**
- ⚠️ 추가 인프라 필요 (벡터 DB)

---

### Option 2: 개별 JSON 파일 (권장하지 않음 ⭐⭐)

```
unified_traffic_data/
├── 판례/
│   ├── 2007노799.json
│   ├── 2007노1012.json
│   └── ... (11,769개 파일)
├── 결정례/
└── 법령/
```

**장점:**
- ✅ 파일 시스템으로 관리
- ✅ 개별 수정 용이

**단점:**
- ❌ 검색 느림 (11,769개 파일 스캔)
- ❌ 유사도 계산 비효율적
- ❌ 확장성 문제

---

### Option 3: PostgreSQL + pgvector (추천 ⭐⭐⭐⭐)

```
PostgreSQL Database
├── documents 테이블 (메타데이터)
├── document_embeddings 테이블
│   └── embedding VECTOR(1536)  -- OpenAI 임베딩
└── pgvector 확장
    └── 코사인 유사도 검색
```

**장점:**
- ✅ 기존 PostgreSQL 활용
- ✅ SQL 쿼리 가능
- ✅ 메타데이터와 벡터 통합 관리

**단점:**
- ⚠️ 대규모 데이터에서는 전문 Vector DB보다 느림

---

## 🏗️ 권장 아키텍처

### 시스템 구성

```
┌─────────────────────────────────────────────────────────────┐
│                     사용자 질의                              │
│           "교통사고 무보험 관련 판례를 찾아줘"                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    LLM API (FastAPI)                         │
│  1. 질의 임베딩 생성                                         │
│  2. 벡터 DB 검색                                             │
│  3. LLM 답변 생성                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               Vector Database (Qdrant)                       │
│  ┌──────────────────────────────────────────┐               │
│  │ Collection: precedents (판례)             │               │
│  │  - 벡터: [0.123, -0.456, ...]  (1536차원) │               │
│  │  - 메타데이터: {                          │               │
│  │      "사건번호": "2007노799",              │               │
│  │      "법원명": "전주지방법원",              │               │
│  │      "키워드": ["교통사고", "무보험"]      │               │
│  │    }                                      │               │
│  │  - 원본 텍스트: "판결요지 + 전문"          │               │
│  └──────────────────────────────────────────┘               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                PostgreSQL (메타데이터)                        │
│  - documents 테이블                                          │
│  - document_ai_labels 테이블                                 │
│  - 관계형 데이터 관리                                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 💡 실제 구현 예시

### 1. 임베딩 생성 및 저장

```python
# scripts/create_embeddings_and_store.py

import json
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# OpenAI 임베딩
client_openai = OpenAI()

def create_embedding(text: str):
    """텍스트 임베딩 생성"""
    response = client_openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

# Qdrant 클라이언트
client_qdrant = QdrantClient(host="localhost", port=6333)

# Collection 생성
client_qdrant.create_collection(
    collection_name="precedents",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)

# 통합 JSON 로드
with open("unified_traffic_data/unified_traffic_data_20251103_174822.json", "r") as f:
    data = json.load(f)

# 사건별 임베딩 생성 및 저장
points = []
for idx, case in enumerate(data["판례"]):
    # 임베딩할 텍스트 구성
    text_to_embed = f"""
    사건번호: {case['사건번호']}
    법원: {case['법원명']}
    판결요지: {case['상세정보'].get('판결요지', '')}
    전문: {case['상세정보'].get('전문', '')[:2000]}
    """

    # 임베딩 생성
    embedding = create_embedding(text_to_embed)

    # Qdrant에 저장
    point = PointStruct(
        id=idx,
        vector=embedding,
        payload={
            "사건번호": case['사건번호'],
            "법원명": case['법원명'],
            "선고일자": case['선고일자'],
            "검색어": case['검색어'],
            "판결요지": case['상세정보'].get('판결요지', ''),
            "전문": case['상세정보'].get('전문', ''),
            "매칭키워드": case.get('메타데이터', {}).get('매칭키워드', [])
        }
    )
    points.append(point)

    # 배치 저장 (100개씩)
    if len(points) >= 100:
        client_qdrant.upsert(
            collection_name="precedents",
            points=points
        )
        points = []
        print(f"진행: {idx + 1}/{len(data['판례'])}")

# 남은 데이터 저장
if points:
    client_qdrant.upsert(collection_name="precedents", points=points)

print("임베딩 생성 및 저장 완료!")
```

---

### 2. RAG 검색 구현

```python
# app/services/rag_service.py

from openai import OpenAI
from qdrant_client import QdrantClient

class RAGService:
    def __init__(self):
        self.openai_client = OpenAI()
        self.qdrant_client = QdrantClient(host="localhost", port=6333)

    def search_similar_cases(self, query: str, top_k: int = 5):
        """유사 판례 검색"""

        # 1. 질의 임베딩 생성
        query_embedding = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        ).data[0].embedding

        # 2. 벡터 DB 검색
        results = self.qdrant_client.search(
            collection_name="precedents",
            query_vector=query_embedding,
            limit=top_k
        )

        # 3. 결과 반환
        similar_cases = []
        for result in results:
            similar_cases.append({
                "사건번호": result.payload['사건번호'],
                "법원명": result.payload['법원명'],
                "판결요지": result.payload['판결요지'],
                "유사도": result.score,
                "전문": result.payload.get('전문', '')
            })

        return similar_cases

    def answer_with_rag(self, question: str):
        """RAG 기반 답변 생성"""

        # 1. 유사 판례 검색
        similar_cases = self.search_similar_cases(question, top_k=3)

        # 2. 컨텍스트 구성
        context = "\n\n".join([
            f"[판례 {i+1}] {case['사건번호']}\n{case['판결요지']}"
            for i, case in enumerate(similar_cases)
        ])

        # 3. LLM 답변 생성
        response = self.openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 법률 전문가입니다. 제공된 판례를 바탕으로 답변하세요."
                },
                {
                    "role": "user",
                    "content": f"질문: {question}\n\n참고 판례:\n{context}"
                }
            ]
        )

        return {
            "answer": response.choices[0].message.content,
            "similar_cases": similar_cases
        }
```

---

### 3. API 엔드포인트

```python
# app/api/v1/rag.py

from fastapi import APIRouter
from app.services.rag_service import RAGService

router = APIRouter(prefix="/api/v1/rag", tags=["RAG"])
rag_service = RAGService()

@router.get("/search")
async def search_similar_cases(query: str, top_k: int = 5):
    """유사 판례 검색"""
    return rag_service.search_similar_cases(query, top_k)

@router.post("/ask")
async def ask_question(question: str):
    """RAG 기반 질의응답"""
    return rag_service.answer_with_rag(question)

@router.get("/recommend/{case_number}")
async def recommend_related_cases(case_number: str, top_k: int = 5):
    """특정 판례와 유사한 판례 추천"""
    # 해당 판례의 판결요지로 검색
    case = get_case_by_number(case_number)
    query = case['상세정보']['판결요지']
    return rag_service.search_similar_cases(query, top_k)
```

---

## 📊 데이터 구조 비교

### ❌ 개별 JSON 파일 방식

```
unified_traffic_data/
├── 2007노799.json (3KB)
├── 2007노1012.json (3KB)
└── ... (11,769개 파일)

검색 시:
1. 11,769개 파일 읽기 → 느림 ❌
2. 각 파일 임베딩 비교 → 매우 느림 ❌
3. 유사도 계산 → 비효율적 ❌
```

### ✅ Vector Database 방식 (권장)

```
unified_traffic_data_20251103_174822.json (444MB, 1개 파일)
    ↓ 한 번만 처리
Qdrant Vector DB
├── 11,769개 벡터 (인덱스됨)
└── 메타데이터

검색 시:
1. 질의 임베딩 생성 (0.1초)
2. 벡터 인덱스 검색 (0.01초) → 빠름 ✅
3. Top-K 결과 반환 (즉시) → 효율적 ✅
```

---

## 🎯 추천 방안

### Phase 1: 기본 RAG 시스템 (우선)

```bash
# 1. Qdrant 설치
docker run -p 6333:6333 qdrant/qdrant

# 2. 임베딩 생성
python scripts/create_embeddings_and_store.py

# 3. RAG API 실행
uvicorn app.main:app --reload
```

**필요한 것:**
- ✅ 통합 JSON 파일 (이미 있음)
- ✅ Qdrant (Docker)
- ✅ OpenAI API Key (임베딩용)

---

### Phase 2: 고급 기능 추가

```python
# 메타데이터 필터링
results = qdrant_client.search(
    collection_name="precedents",
    query_vector=query_embedding,
    query_filter={
        "must": [
            {"key": "법원명", "match": {"value": "대법원"}},
            {"key": "선고일자", "range": {"gte": "2020-01-01"}}
        ]
    },
    limit=5
)

# 키워드 기반 하이브리드 검색
# 벡터 검색 + 키워드 필터
```

---

### Phase 3: 관련 법령 추천

```python
# 별도 Collection: statutes (법령)
client_qdrant.create_collection(
    collection_name="statutes",
    vectors_config=VectorParams(size=1536, distance=Distance.COSINE)
)

# 판례 → 관련 법령 추천
def recommend_related_statutes(case_number: str):
    case = get_case(case_number)

    # 참조조문 추출
    statutes_text = case['상세정보']['참조조문']

    # 법령 DB에서 검색
    embedding = create_embedding(statutes_text)
    results = qdrant_client.search(
        collection_name="statutes",
        query_vector=embedding,
        limit=5
    )

    return results
```

---

## 📋 구현 체크리스트

### 데이터 준비
- [x] 통합 JSON 파일 생성 (444MB)
- [ ] Vector Database 설치 (Qdrant)
- [ ] 임베딩 생성 스크립트 작성
- [ ] 임베딩 생성 실행 (11,769건)

### RAG 시스템
- [ ] RAG Service 구현
- [ ] API 엔드포인트 추가
- [ ] 유사 판례 검색 기능
- [ ] 질의응답 기능

### 고급 기능
- [ ] 메타데이터 필터링
- [ ] 관련 법령 추천
- [ ] 하이브리드 검색 (벡터 + 키워드)

---

## 💰 비용 예상 (OpenAI 임베딩)

```
모델: text-embedding-3-small
가격: $0.02 / 1M tokens

11,769건 × 평균 2,000 토큰 = 23,538,000 토큰
비용: $0.47 (약 600원)

✅ 매우 저렴!
```

---

## 🎯 결론

### ❌ 개별 JSON 파일로 분리: **필요 없음**

**이유:**
1. 검색 성능 저하
2. 관리 복잡도 증가
3. Vector DB가 훨씬 효율적

### ✅ 권장 방안

```
통합 JSON (1개 파일, 444MB) ← 현재 상태 유지
    ↓
임베딩 생성 (한 번만)
    ↓
Vector DB (Qdrant)
    ├─ 빠른 검색
    ├─ 유사 판례 추천
    └─ 관련 법령 추천
```

**다음 단계:**
1. Qdrant 설치
2. 임베딩 생성 스크립트 실행
3. RAG API 구현

---

**작성일:** 2025-11-03
**데이터:** unified_traffic_data_20251103_174822.json (11,769건)
**권장 Vector DB:** Qdrant (오픈소스, Docker 지원)
