# 형사법 RAG 챗봇 사용 가이드

## 📋 목차

1. [설치](#설치)
2. [환경 설정](#환경-설정)
3. [데이터 준비](#데이터-준비)
4. [벡터 DB 구축](#벡터-db-구축)
5. [챗봇 실행](#챗봇-실행)
6. [고급 사용법](#고급-사용법)
7. [문제 해결](#문제-해결)

## 설치

### 1. 저장소 클론
```bash
git clone <repository-url>
cd lawlaw
```

### 2. 가상환경 생성
```bash
python -m venv venv

# macOS/Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

## 환경 설정

### 1. 환경 변수 파일 생성
```bash
cp .env.example .env
```

### 2. API 키 설정
`.env` 파일을 열어 다음 항목을 설정하세요:

```bash
# LLM API Keys (둘 중 하나만 필요)
OPENAI_API_KEY=sk-...
# 또는
ANTHROPIC_API_KEY=sk-ant-...

# 임베딩 모델 (한국어 특화)
EMBEDDING_MODEL=jhgan/ko-sroberta-multitask

# LLM 모델
LLM_MODEL=gpt-4-turbo-preview
# 또는
# LLM_MODEL=claude-3-opus-20240229

# 벡터 DB 타입
VECTOR_DB_TYPE=chroma  # 또는 faiss

# RAG 설정
TOP_K_RETRIEVAL=5
CHUNK_SIZE=500
CHUNK_OVERLAP=50
```

## 데이터 준비

### 1. AI Hub에서 데이터 다운로드
- [AI Hub 형사법 데이터셋](https://www.aihub.or.kr) 접속
- 데이터셋 다운로드 및 압축 해제

### 2. 데이터 배치
다운로드한 CSV 파일들을 `data/raw/` 디렉토리에 배치:

```bash
data/raw/
├── 판례_데이터.csv
├── 법령_데이터.csv
├── 해석례_데이터.csv
└── ...
```

### 3. 데이터 구조 확인
CSV 파일이 다음과 같은 구조를 가져야 합니다:
- 텍스트 컬럼 (예: `text`, `content`, `내용`)
- 기타 메타데이터 컬럼

## 벡터 DB 구축

### 기본 사용법
```bash
python scripts/build_vectordb.py --db_type chroma
```

### 옵션 설명
```bash
# ChromaDB 사용 (권장)
python scripts/build_vectordb.py --db_type chroma

# FAISS 사용 (대용량 데이터)
python scripts/build_vectordb.py --db_type faiss

# 텍스트 컬럼명 지정
python scripts/build_vectordb.py --text_column "내용"

# 테스트용으로 일부 데이터만 사용
python scripts/build_vectordb.py --max_docs 1000

# 테스트 쿼리로 검증
python scripts/build_vectordb.py --test_query "절도죄란?"
```

### 예상 소요 시간
- 1만 문서: 약 5-10분
- 10만 문서: 약 30-60분
- 305만 문서: 약 3-5시간

## 챗봇 실행

### 1. Streamlit UI (추천)
```bash
streamlit run src/ui/app.py
```

브라우저에서 `http://localhost:8501` 접속

**주요 기능:**
- 대화형 인터페이스
- 참고 문서 실시간 표시
- 검색 파라미터 조정
- 대화 히스토리 관리

### 2. Gradio UI
```bash
python src/ui/gradio_app.py
```

브라우저에서 `http://localhost:7860` 접속

**옵션:**
```bash
# 외부 공유 링크 생성
python src/ui/gradio_app.py --share

# 포트 변경
python src/ui/gradio_app.py --port 8080

# FAISS 사용
python src/ui/gradio_app.py --db_type faiss

# Claude 사용
python src/ui/gradio_app.py --llm_provider anthropic
```

### 3. CLI
```bash
python scripts/chat_cli.py
```

**CLI 명령어:**
- `quit`, `exit`, `q`: 종료
- `clear`, `c`: 대화 히스토리 초기화
- `help`, `h`: 도움말

**옵션:**
```bash
# 참고 문서 표시
python scripts/chat_cli.py --show_sources

# 검색 문서 수 조정
python scripts/chat_cli.py --top_k 10
```

## 고급 사용법

### 1. Python 스크립트에서 사용

```python
from configs.config import config
from src.embeddings.embedder import KoreanLegalEmbedder
from src.embeddings.vectordb import create_vector_db
from src.retrieval.retriever import LegalDocumentRetriever
from src.llm.llm_client import create_llm_client
from src.llm.rag_chatbot import RAGChatbot

# 초기화
embedder = KoreanLegalEmbedder(
    model_name=config.embedding.model_name
)

vectordb = create_vector_db(
    "chroma",
    persist_directory=config.vectordb.chroma_persist_dir
)

retriever = LegalDocumentRetriever(
    vectordb=vectordb,
    embedder=embedder,
    top_k=5
)

llm_client = create_llm_client(
    provider="openai",
    api_key=config.llm.openai_api_key,
    model="gpt-4-turbo-preview"
)

chatbot = RAGChatbot(
    retriever=retriever,
    llm_client=llm_client
)

# 질문하기
response = chatbot.chat("절도죄의 구성요건은?")
print(response['answer'])
```

### 2. 출처 타입별 검색

```python
from src.llm.rag_chatbot import AdvancedRAGChatbot

# 고급 챗봇 사용
advanced_chatbot = AdvancedRAGChatbot(retriever, llm_client)

# 판례만 검색
response = advanced_chatbot.chat_with_source_filter(
    "절도죄의 구성요건은?",
    source_types=['court_decision'],
    top_k=5
)

# 법령만 검색
response = advanced_chatbot.chat_with_source_filter(
    "형법 제329조는?",
    source_types=['statute'],
    top_k=3
)
```

### 3. 커스텀 시스템 프롬프트

```python
custom_prompt = """
당신은 형사법 전문 변호사입니다.
판례와 법령을 정확히 인용하며,
실무적 조언을 제공해주세요.
"""

chatbot = RAGChatbot(
    retriever=retriever,
    llm_client=llm_client,
    system_prompt=custom_prompt
)
```

### 4. 임베딩 모델 변경

```python
# 다른 한국어 모델 사용
embedder = KoreanLegalEmbedder(
    model_name="BM-K/KoSimCSE-roberta"  # 문장 유사도 특화
)

# 또는
embedder = KoreanLegalEmbedder(
    model_name="snunlp/KR-SBERT-V40K-klueNLI-augSTS"
)
```

## 문제 해결

### 1. 임베딩 모델 다운로드 오류
```bash
# 모델을 수동으로 다운로드
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('jhgan/ko-sroberta-multitask')"
```

### 2. ChromaDB 오류
```bash
# ChromaDB 재구축
rm -rf data/vectordb/chroma
python scripts/build_vectordb.py --db_type chroma
```

### 3. API 키 오류
- `.env` 파일의 API 키 확인
- 유효한 API 키인지 확인
- 충분한 크레딧이 있는지 확인

### 4. 메모리 부족
```python
# 배치 크기 줄이기 (.env 파일)
EMBEDDING_BATCH_SIZE=16

# 또는 코드에서:
embedder = KoreanLegalEmbedder(batch_size=16)
```

### 5. CUDA 오류
```bash
# CPU 사용으로 전환 (.env 파일)
EMBEDDING_DEVICE=cpu
```

## 성능 최적화

### 1. 검색 성능
- `TOP_K_RETRIEVAL`: 5-10 사이 권장
- `CHUNK_SIZE`: 300-700 사이 권장
- `CHUNK_OVERLAP`: chunk_size의 10-20%

### 2. 임베딩 성능
- GPU 사용: 10-50배 빠름
- 배치 크기 증가: 속도 향상 (메모리 허용 시)

### 3. LLM 비용 절감
- `max_tokens`: 필요한 만큼만 설정
- `temperature`: 0.1-0.3 (일관성 있는 답변)
- top_k 감소로 컨텍스트 크기 감소

## 예시 질문

### 형사법 일반
- 절도죄의 구성요건은 무엇인가요?
- 정당방위가 성립하는 요건은?
- 긴급피난과 정당방위의 차이는?

### 판례 검색
- 특수절도죄 관련 판례를 알려주세요
- 업무상 횡령죄 판례는?

### 법령 해석
- 형법 제329조는 무엇인가요?
- 형사소송법상 구속 요건은?

### 비교 질문
- 절도죄와 강도죄의 차이는?
- 사기죄와 배임죄를 비교해주세요

## 추가 자료

- [ChromaDB 문서](https://docs.trychroma.com/)
- [FAISS 문서](https://github.com/facebookresearch/faiss)
- [Sentence Transformers](https://www.sbert.net/)
- [LangChain 문서](https://python.langchain.com/)
