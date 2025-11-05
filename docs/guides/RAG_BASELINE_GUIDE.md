# Claude Code Guide for RAG Baseline Development

> **이 가이드는 Claude Code를 사용하여 RAG 베이스라인을 이해하고 확장하는 개발자를 위한 문서입니다.**

## 📋 목차

1. [프로젝트 개요](#프로젝트-개요)
2. [베이스라인 아키텍처](#베이스라인-아키텍처)
3. [Claude Code 사용 시작하기](#claude-code-사용-시작하기)
4. [주요 컴포넌트 이해하기](#주요-컴포넌트-이해하기)
5. [새로운 기능 추가하기](#새로운-기능-추가하기)
6. [실험 워크플로우](#실험-워크플로우)
7. [문제 해결 가이드](#문제-해결-가이드)
8. [Claude Code 프롬프트 예시](#claude-code-프롬프트-예시)

---

## 프로젝트 개요

### 🎯 목적
법률 문서 분석을 위한 RAG (Retrieval-Augmented Generation) 시스템 개발 및 실험

### 🏗️ 설계 원칙
1. **모듈화**: 모든 컴포넌트가 독립적으로 교체 가능
2. **확장성**: 새로운 기법을 쉽게 추가 가능
3. **재현성**: Config 기반 실험 관리
4. **팀 협업**: 멤버별 독립적인 실험 공간

### 📊 현재 상태
- ✅ **베이스라인 구축 완료**: 기본 RAG 파이프라인 구현
- ✅ **Config 검증 시스템**: 실험 전 설정 자동 검증
- ✅ **에러 핸들링**: 단계별 명확한 에러 메시지
- ✅ **캐시 시스템**: 인덱스 재사용으로 실험 효율화
- 🔄 **진행 중**: 팀원별 Advanced RAG 실험

---

## 베이스라인 아키텍처

### 📁 디렉토리 구조 (베이스라인 구축 후)

```
/
├── core/                          # 핵심 AI 로직
│   ├── config/                    # Config 검증 모듈 ✨ NEW
│   │   ├── __init__.py
│   │   ├── validator.py          # YAML 설정 검증
│   │   └── README.md             # 검증 규칙 문서
│   │
│   ├── embeddings/                # 임베딩 모델
│   │   ├── __init__.py           # get_embedder() 팩토리
│   │   ├── base.py               # BaseEmbedder 추상 클래스
│   │   ├── openai_embedder.py    # OpenAI 임베딩
│   │   └── huggingface_embedder.py  # HuggingFace 임베딩
│   │
│   ├── models/                    # LLM 모델
│   │   ├── __init__.py           # get_llm() 팩토리
│   │   ├── base.py               # BaseLLM 추상 클래스
│   │   ├── openai_llm.py         # OpenAI LLM
│   │   └── gemini_llm.py         # Google Gemini
│   │
│   ├── rag/                       # RAG 파이프라인
│   │   ├── __init__.py
│   │   ├── pipeline.py           # RAGPipeline (메인 orchestrator) ✨ 에러핸들링 추가
│   │   ├── chunker.py            # 문서 청킹 전략들
│   │   ├── vector_store.py       # 벡터 DB (FAISS, Chroma)
│   │   ├── retriever.py          # 검색 전략 (Similarity, MMR, Hybrid)
│   │   └── cache_manager.py      # 인덱스 캐시 관리
│   │
│   └── evaluation/                # 평가 메트릭
│       ├── __init__.py
│       ├── metrics.py            # 기본 메트릭 (F1, ROUGE, etc.)
│       └── advanced_metrics.py   # 고급 메트릭 (NDCG, RAGAS, etc.)
│
├── experiments/                   # 실험 관리
│   ├── baseline/                  # 베이스라인 실험
│   │   ├── config.yaml           # 베이스라인 설정
│   │   └── results/              # 베이스라인 결과
│   │
│   ├── configs/                   # 실험 설정 파일들
│   │   ├── template_config.yaml  # 템플릿 (복사해서 사용)
│   │   └── members/              # 팀원별 실험 설정
│   │       └── {name}/           # 예: wh/, jy/, etc.
│   │           └── {name}_config.yaml
│   │
│   ├── indexed_data/             # 캐시된 인덱스 (git-ignored)
│   │   ├── {cache_key}/          # 캐시별 디렉토리
│   │   │   ├── index.faiss
│   │   │   ├── data.json
│   │   │   └── cache_config.json
│   │   └── cache_metadata.json
│   │
│   └── results/                  # 실험 결과 (git-ignored)
│       └── {member_name}/
│           └── {config_name}_{timestamp}.json
│
├── scripts/                      # 유틸리티 스크립트
│   └── criminal_law_data_loader.py  # 형사법 데이터 로더
│
├── data/                         # 데이터 디렉토리 (git-ignored)
│   ├── raw/                      # 원본 데이터
│   ├── processed/                # 전처리된 데이터
│   └── evaluation/               # 평가 데이터셋
│       └── test_qa.json          # QA 평가 셋
│
├── run.py                        # 메인 CLI 도구 ✨ 검증 통합
├── requirements.txt              # Python 의존성
├── .env                         # API 키 등 환경변수
├── .gitignore                   # Git 제외 파일
├── CLAUDE.md                    # Claude Code 프로젝트 가이드
└── CLAUDE_CODE_GUIDE.md         # 이 파일
```

### 🔑 핵심 개념

#### 1. **추상 클래스 패턴** (Strategy Pattern)
모든 주요 컴포넌트는 추상 베이스 클래스를 상속:

```python
# 예시: 새 임베딩 모델 추가
from core.embeddings.base import BaseEmbedder

class MyCustomEmbedder(BaseEmbedder):
    def embed(self, texts):
        # 구현
        pass

    def embed_batch(self, texts, batch_size):
        # 구현
        pass
```

#### 2. **팩토리 패턴** (Factory Pattern)
Config 기반으로 컴포넌트 자동 생성:

```python
# core/embeddings/__init__.py
def get_embedder(config: dict) -> BaseEmbedder:
    if config['type'] == 'openai':
        return OpenAIEmbedder(...)
    elif config['type'] == 'custom':  # ← 여기만 추가
        return MyCustomEmbedder(...)
```

#### 3. **Config 기반 실험**
모든 실험 파라미터는 YAML로 관리:

```yaml
# experiments/configs/members/myname/my_config.yaml
chunking:
  strategy: "fixed"
  chunk_size: 512

embedding:
  type: "huggingface"
  model: "BAAI/bge-m3"
```

#### 4. **캐시 시스템**
같은 설정의 인덱스를 재사용:
- **캐시 키**: `chunking_embedding_vectorstore` 조합
- **자동 감지**: 같은 설정이면 재사용
- **수동 제어**: `--force` 플래그로 재인덱싱

---

## Claude Code 사용 시작하기

### 🚀 초기 설정

#### 1. **프로젝트 클론 및 환경 설정**

Claude Code에게 다음과 같이 요청하세요:

```
프로젝트를 설정하고 실행 가능한 상태로 만들어줘:
1. 가상환경 생성 및 활성화
2. requirements.txt 설치
3. .env 파일 생성 (템플릿 필요하면 만들어줘)
4. 데이터 디렉토리 구조 확인
```

#### 2. **프로젝트 구조 이해**

```
현재 프로젝트 구조를 분석하고 다음을 설명해줘:
1. core/ 디렉토리의 주요 모듈들
2. 각 모듈의 역할과 관계
3. 실험을 시작하려면 어떤 파일을 수정해야 하는지
```

#### 3. **베이스라인 실행 테스트**

```
베이스라인 실험을 실행해서 모든 게 정상 작동하는지 확인해줘:
1. python run.py baseline 실행
2. 에러가 있으면 해결
3. 결과 확인
```

### 📖 프로젝트 이해하기

Claude Code에게 다음 질문들을 해보세요:

#### 코드 탐색
```
1. "RAG 파이프라인의 전체 흐름을 설명해줘"
2. "core/rag/pipeline.py의 주요 메서드들을 설명해줘"
3. "캐시 시스템이 어떻게 작동하는지 설명해줘"
4. "Config 검증이 어떤 것들을 체크하는지 알려줘"
```

#### 설정 이해
```
1. "experiments/baseline/config.yaml의 각 설정을 설명해줘"
2. "새 실험 config를 만들려면 어떻게 해야 하는지 알려줘"
3. "캐시 키가 어떻게 생성되는지 설명해줘"
```

---

## 주요 컴포넌트 이해하기

### 🔍 Claude Code에게 컴포넌트 분석 요청하기

#### 1. Chunking 전략

```
core/rag/chunker.py를 분석해서 알려줘:
1. 현재 구현된 청킹 전략들
2. 각 전략의 장단점
3. 새로운 전략을 추가하려면 어떻게 해야 하는지
```

**현재 구현된 전략:**
- `FixedSizeChunking`: 고정 크기 청킹
- `SemanticChunking`: 의미 기반 청킹
- `RecursiveChunking`: 계층적 분할
- `SlidingWindowChunking`: 슬라이딩 윈도우

#### 2. Retrieval 방법

```
core/rag/retriever.py의 검색 방법들을 설명해줘:
1. Similarity 검색
2. MMR (Maximal Marginal Relevance)
3. Hybrid (Vector + BM25)
각각 언제 사용하면 좋은지도 알려줘
```

#### 3. Evaluation Metrics

```
core/evaluation/의 평가 메트릭들을 정리해줘:
1. 기본 메트릭 (metrics.py)
2. 고급 메트릭 (advanced_metrics.py)
3. 각 메트릭이 측정하는 것
```

### 🧩 컴포넌트 간 관계 이해

```
RAG Pipeline에서 각 컴포넌트가 어떻게 연결되는지 플로우차트로 설명해줘:
1. Document → Chunker → Embedder → VectorStore
2. Query → Embedder → Retriever → VectorStore
3. Retrieved Docs + Query → LLM → Answer
```

---

## 새로운 기능 추가하기

### 🎨 확장 패턴

#### Pattern 1: 새 Embedding 모델 추가

```
BAAI/bge-m3 대신 "intfloat/multilingual-e5-large" 모델을 사용하고 싶어.
어떻게 추가하면 되는지 단계별로 알려주고, 필요하면 코드도 작성해줘.
```

**Claude Code가 할 일:**
1. `core/embeddings/` 구조 확인
2. 기존 HuggingFace embedder 분석
3. 새 모델 추가 방법 설명
4. Config 예시 제공

#### Pattern 2: 새 Vector Store 추가 (Qdrant)

```
Qdrant vector store를 추가하고 싶어. 다음을 해줘:
1. core/rag/vector_store.py에 QdrantVectorStore 클래스 추가
2. get_vector_store() 팩토리 함수에 통합
3. 테스트용 config 작성
4. 사용 방법 설명
```

#### Pattern 3: Advanced RAG - Reranking 추가

```
Cross-Encoder reranking을 추가하고 싶어:
1. core/rag/advanced/ 디렉토리 생성
2. reranker.py 모듈 작성 (BaseReranker 추상 클래스 + CrossEncoderReranker)
3. pipeline.py에 선택적으로 통합
4. config에 reranking 섹션 추가
5. 테스트 실행
```

#### Pattern 4: 새 Chunking 전략 추가

```
법률 문서 특화 청킹 전략을 만들고 싶어:
- 조문 단위로 청킹
- "제OO조" 패턴을 인식
- 조문 번호를 metadata에 저장

이걸 구현해주고 기존 chunker.py에 통합해줘.
```

### 🛠️ 실전 예시: HyDE (Hypothetical Document Embeddings) 추가

```
HyDE 기법을 추가하고 싶어. 다음을 해줘:

1. core/rag/advanced/query_rewriter.py 파일 생성
2. BaseQueryRewriter 추상 클래스 정의
3. HyDEQueryRewriter 구현 (LLM으로 가상 문서 생성)
4. core/rag/pipeline.py의 query() 메서드에 통합
5. config에 query_rewriting 섹션 추가
6. 테스트 config로 실행해서 동작 확인
7. 결과를 베이스라인과 비교

단계별로 진행하면서 각 단계마다 확인해줘.
```

---

## 실험 워크플로우

### 📊 전체 실험 프로세스

#### Step 1: 실험 초기화

```
"jy"라는 이름으로 새 실험을 시작하고 싶어:
1. python run.py init-experiment --name jy --description "내 실험" 실행
2. 생성된 config 파일 확인
3. 수정이 필요한 부분 알려줘
```

#### Step 2: Config 커스터마이징

```
experiments/configs/members/jy/jy_config.yaml을 다음과 같이 수정해줘:
- chunk_size를 512에서 1024로 변경
- embedding 모델을 "dragonkue/BGE-m3-ko"로 변경
- retrieval method를 "mmr"로 변경
- top_k를 5에서 10으로 변경
```

#### Step 3: Config 검증

```
내 config가 유효한지 검증해줘:
python run.py index --config experiments/configs/members/jy/jy_config.yaml

에러가 있으면 수정해줘.
```

#### Step 4: 인덱싱

```
데이터를 인덱싱해줘. 진행 상황을 모니터링하고 에러가 있으면 처리해줘.
```

#### Step 5: 실험 실행

```
전체 실험을 실행해줘:
python run.py experiment --config experiments/configs/members/jy/jy_config.yaml

결과를 분석하고 요약해줘.
```

#### Step 6: 결과 비교

```
내 실험 결과와 베이스라인을 비교해줘:
1. experiments/results/jy/의 최신 결과 파일 찾기
2. experiments/baseline/results/의 베이스라인 결과와 비교
3. F1, ROUGE-L, 응답 시간 등 주요 메트릭 비교
4. 개선/악화된 부분 분석
```

### 🔄 반복 실험

```
이전 실험에서 chunk_size=1024가 안 좋았어. 다음 실험을 해보자:

1. 새 config 복사: jy_config_v2.yaml
2. chunk_size를 256으로 변경
3. overlap을 50으로 변경
4. 인덱싱 (새 캐시 키 생성됨)
5. 실험 실행
6. v1, v2, baseline 3가지 비교
```

---

## 문제 해결 가이드

### 🐛 일반적인 문제들

#### 문제 1: API Key 에러

```
"Missing OpenAI API key" 에러가 나. 해결해줘:
1. .env 파일 확인
2. OPENAI_API_KEY 설정 여부 확인
3. 없으면 추가하는 방법 알려줘
4. 환경변수가 제대로 로드되는지 테스트
```

#### 문제 2: 메모리 부족

```
인덱싱 중 메모리 부족 에러가 나. 다음을 확인해줘:
1. config의 batch_size 확인 (너무 크면 줄여줘)
2. 데이터 크기 확인
3. max_per_type 설정으로 데이터 제한 제안
```

#### 문제 3: Config 검증 실패

```
Config 검증이 실패했어. 에러 메시지를 보고 수정해줘:
[에러 메시지 붙여넣기]

각 에러를 설명하고 config를 수정해줘.
```

#### 문제 4: 캐시 관련 문제

```
캐시를 삭제하고 재인덱싱하고 싶어:
1. 현재 캐시 목록 보여줘
2. 특정 캐시 삭제 방법 알려줘
3. --force 옵션으로 재인덱싱 실행
```

### 🔧 고급 디버깅

```
실험이 실패했는데 원인을 모르겠어. 다음을 해줘:
1. 최근 로그 확인 (RAGPipeline 로그)
2. 에러 스택 트레이스 분석
3. 해당 단계의 config 확인
4. 가능한 원인 추론
5. 해결 방법 제시
```

---

## Claude Code 프롬프트 예시

### 🎯 효과적인 프롬프트 작성법

#### ✅ 좋은 프롬프트

```
❌ "코드 수정해줘"
✅ "core/rag/pipeline.py의 query() 메서드에 reranking 단계를 추가해줘.
   retrieved_docs를 받아서 CrossEncoder로 재정렬하는 로직이야."

❌ "에러 났어"
✅ "python run.py index 실행 중 'IndexingError: Failed to generate embeddings' 에러가 났어.
   로그를 보니 API rate limit 같은데, 해결 방법 알려줘."

❌ "실험 설정해줘"
✅ "청크 크기 512, BGE-m3 임베딩, MMR 검색을 사용하는 실험 config를 만들어줘.
   experiments/configs/members/jy/ 디렉토리에 jy_config_mmr.yaml로 저장해줘."
```

### 📚 시나리오별 프롬프트

#### 신규 기능 추가

```
Cohere Rerank API를 사용하는 reranker를 추가하고 싶어. 다음을 순차적으로 해줘:

1. core/rag/advanced/reranker.py 파일 생성
2. BaseReranker 추상 클래스 정의 (rerank 메서드)
3. CohereReranker 구현:
   - __init__에서 cohere client 초기화
   - rerank()에서 query와 documents를 받아 재정렬
   - relevance_score 반환
4. core/rag/pipeline.py 수정:
   - __init__에 reranker 초기화 추가 (config.reranking.enabled)
   - query() 메서드에서 retrieval 후 reranking 단계 추가
5. template_config.yaml에 reranking 섹션 추가
6. 테스트 config로 실행해서 동작 확인

각 단계마다 완료하면 다음 단계로 넘어가자.
```

#### 데이터 분석

```
experiments/results/ 디렉토리의 모든 실험 결과를 분석해줘:

1. 각 실험의 평균 F1, ROUGE-L, 응답시간 추출
2. 표로 정리 (실험명, F1, ROUGE-L, 시간)
3. 가장 성능 좋은 설정 찾기
4. chunk_size와 성능의 상관관계 분석
5. 추천 설정 제안
```

#### 코드 리팩토링

```
core/rag/retriever.py가 너무 길어져서 리팩토링하고 싶어:

1. 현재 구조 분석 (클래스 개수, 라인 수)
2. retrievers/ 디렉토리로 분리 제안
   - retrievers/base.py
   - retrievers/similarity.py
   - retrievers/mmr.py
   - retrievers/hybrid.py
3. __init__.py에서 통합
4. 기존 코드 동작 유지 확인
5. 변경사항 요약
```

#### 성능 최적화

```
인덱싱 속도를 개선하고 싶어:

1. 현재 pipeline.py의 index_documents() 분석
2. 병목 지점 찾기 (chunking, embedding, vector store add)
3. 최적화 방안 제시:
   - batch_size 조정
   - 병렬 처리
   - 진행률 표시
4. 개선 코드 작성
5. 성능 비교 (Before/After)
```

### 🎓 학습용 프롬프트

```
RAG 시스템의 검색 품질을 개선하는 방법들을 알려주고,
우리 베이스라인에 적용 가능한 것들을 제안해줘:

1. Query Expansion
2. Reranking
3. Hybrid Search
4. Parent-Child Chunking
5. Contextual Compression

각각의 개념, 장단점, 구현 난이도를 설명해줘.
```

---

## 베스트 프랙티스

### ✅ DO

```
✅ "core/rag/chunker.py에 있는 FixedSizeChunking 클래스를 참고해서,
   법률 조문 단위로 청킹하는 LegalArticleChunking 클래스를 만들어줘."
   → 구체적이고 참고할 파일 명시

✅ "experiments/baseline/results/의 최신 결과와 내 실험 결과를 비교해줘.
   비교 항목: F1, ROUGE-L, NDCG@5, 평균 응답시간"
   → 명확한 비교 기준 제시

✅ "config 검증에서 'Invalid chunk_size' 에러가 나. validator.py를 확인하고
   유효 범위를 알려준 뒤 내 config를 수정해줘."
   → 문제, 확인할 파일, 원하는 결과 명시
```

### ❌ DON'T

```
❌ "코드 개선해줘"
   → 너무 모호함

❌ "에러 나는데 고쳐줘"
   → 에러 메시지, 발생 위치 없음

❌ "이 파일 설명해줘"
   → 어떤 관점에서 설명할지 불명확
```

### 🎯 효율적인 작업 흐름

1. **큰 작업은 단계별로 나누기**
   ```
   "Reranking 기능을 추가하자. 먼저 reranker.py 파일 구조만 보여줘."
   [확인 후]
   "좋아. 이제 BaseReranker 클래스를 구현해줘."
   [확인 후]
   "이제 CrossEncoderReranker를 구현하자..."
   ```

2. **변경사항은 테스트와 함께**
   ```
   "MMR retriever를 수정했으면, 간단한 테스트 케이스로 동작 확인해줘."
   ```

3. **문서화 요청**
   ```
   "방금 추가한 HyDE 기능을 README에 문서화해줘.
   사용법, 파라미터, 예시 config를 포함해서."
   ```

---

## 협업 가이드

### 🤝 팀원간 협업

#### 내 실험 공유하기

```
내가 만든 reranking 기능을 팀원들이 쉽게 사용할 수 있게 문서화해줘:

1. core/rag/advanced/README.md 작성
2. 사용 방법 (config 예시 포함)
3. 파라미터 설명
4. 성능 비교 결과 (있다면)
5. 주의사항
```

#### 다른 팀원 코드 이해하기

```
팀원 "wh"가 만든 experiments/configs/members/wh/wh_config_chunk_512.yaml을 분석해줘:

1. 베이스라인과 다른 점
2. 각 설정의 의도 추론
3. 예상 성능 특성
4. 내 실험에 적용할 만한 아이디어
```

### 🔀 Git 워크플로우

```
내 실험 결과를 develop 브랜치에 병합하고 싶어:

1. 현재 변경사항 확인
2. 커밋할 파일 선별 (results/ 제외)
3. 의미있는 커밋 메시지 제안
4. feature 브랜치 생성
5. PR 준비 (변경사항 요약)
```

---

## 부록: 자주 사용하는 명령어

### CLI 명령어 요약

```bash
# 실험 초기화
python run.py init-experiment --name {이름} --description "설명"

# 인덱싱 (캐시 자동 감지)
python run.py index --config {config_path}

# 강제 재인덱싱
python run.py index --config {config_path} --force

# 검색 테스트
python run.py search --config {config_path} --query "질문"

# RAG 전체 파이프라인 (검색+생성)
python run.py generate --config {config_path} --query "질문"

# 전체 실험 (인덱싱 + 평가)
python run.py experiment --config {config_path}

# 캐시 목록 확인
python run.py list-caches

# 캐시 삭제
python run.py delete-cache --cache-key {cache_key}

# 실험 결과 비교
python run.py compare --experiments results/a.json results/b.json

# 베이스라인 실행
python run.py baseline
```

---

## 추가 리소스

### 📖 읽을거리

1. **CLAUDE.md** - 프로젝트 전체 개요 및 구조
2. **core/config/README.md** - Config 검증 규칙
3. **experiments/configs/template_config.yaml** - 모든 설정 옵션 설명

### 💡 도움이 필요할 때

```
Claude Code에게 물어보세요:

"CLAUDE.md와 CLAUDE_CODE_GUIDE.md를 읽고 프로젝트를 설명해줘"
"내가 하려는 실험을 위해 어떤 파일들을 수정해야 하는지 알려줘"
"지금까지 구현된 기능들의 목록을 보여줘"
"베이스라인의 아키텍처를 다이어그램으로 설명해줘"
```

---

## 마지막 팁

### 🎯 성공적인 실험을 위한 체크리스트

- [ ] Config 파일 작성 완료
- [ ] Config 검증 통과 확인
- [ ] .env 파일에 필요한 API 키 설정
- [ ] 실험 목적과 가설 명확히 정의
- [ ] 베이스라인 대비 변경사항 문서화
- [ ] 예상 결과와 평가 메트릭 정의
- [ ] 실험 완료 후 결과 분석 및 기록
- [ ] 유용한 발견사항은 팀과 공유

### 🚀 다음 단계

베이스라인을 이해했다면:

1. **간단한 실험부터** - chunk_size 변경 같은 단순한 실험
2. **점진적 개선** - 한 번에 하나씩만 변경
3. **결과 기록** - 모든 실험 결과를 문서화
4. **지식 공유** - 유용한 발견은 팀과 공유

**Happy Experimenting! 🎉**
