# 🚀 Quick Start Guide

## 시작하기 전에

이 프로젝트는 **학습 목적**으로 설계되었습니다. RAG, Constitutional AI, Few-Shot Learning 등의 개념을 실제로 구현하고 이해하는 것이 목표입니다.

## ✅ 전제 조건

1. **Python 3.8+** 설치
2. **AI Hub 형사법 데이터** 다운로드 완료
   - 경로: `~/Downloads/04.형사법 LLM 사전학습 및 Instruction Tuning 데이터/`
3. **OpenAI API 키** (선택사항, Constitutional AI 챗봇 실행 시 필요)

## 📦 설치 (5분)

### 1. 저장소 클론
```bash
cd ~/Documents/libraries/lawlaw
```

### 2. 가상환경 생성 및 활성화
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 패키지 설치
```bash
pip install -r requirements.txt
```

**중요**: `requirements.txt`는 안정적인 버전을 사용합니다:
- `sentence-transformers==2.7.0` (mutex 문제 해결)
- `transformers==4.36.0`
- `tokenizers==0.15.0`

### 4. 환경변수 설정
```bash
cp .env.example .env
# .env 파일을 열어 OPENAI_API_KEY 입력
```

`.env` 예시:
```
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=your-key-here  # 선택사항
```

## 🧪 빠른 테스트 (3분)

### Step 1: 컴포넌트 테스트
각 컴포넌트가 정상 작동하는지 확인:

```bash
export TOKENIZERS_PARALLELISM=false
python scripts/test_components.py
```

**예상 출력:**
```
✅ 데이터 로딩 성공: 236개 행
✅ 전처리 성공: 50개 청크
✅ 임베딩 모델 로드 성공!
   모델: jhgan/ko-sroberta-multitask
   임베딩 차원: 768
✅ 임베딩 생성 성공: (10, 768)
🎉 모든 컴포넌트 테스트 통과!
```

### Step 2: 작은 벡터 DB 구축
10개 파일로 빠른 테스트:

```bash
export TOKENIZERS_PARALLELISM=false
python scripts/build_vectordb.py \
  --max_files 10 \
  --max_docs 100 \
  --test_query "절도죄의 구성요건은 무엇인가요?"
```

**소요 시간**: 약 10-20초

**예상 출력:**
```
2025-10-28 17:40:13 | INFO | Step 1: Loading data...
2025-10-28 17:40:13 | INFO | Loaded 1060 rows from 10 files
2025-10-28 17:40:13 | INFO | Step 2: Preprocessing and chunking...
2025-10-28 17:40:13 | INFO | Created 1056 chunks
2025-10-28 17:40:18 | INFO | Step 3: Generating embeddings...
2025-10-28 17:40:20 | INFO | Generated embeddings with shape: (100, 768)
2025-10-28 17:40:20 | INFO | Step 4: Building chroma vector database...
2025-10-28 17:40:21 | INFO | Vector database built successfully!
2025-10-28 17:40:21 | INFO | Total documents in DB: 100

Testing search with query: '절도죄의 구성요건은 무엇인가요?'
--- Result 1 (score: 0.4313) ---
Text: 사 건 2022노2009 사기, 횡령...
```

## 🚀 실제 사용

### Option 1: 중간 크기로 테스트 (100개 파일)
```bash
python scripts/build_vectordb.py \
  --max_files 100 \
  --max_docs 1000
```
**소요 시간**: 약 2-3분

### Option 2: 전체 데이터 구축 (40,782개 파일)
⚠️  **주의**: 시간이 오래 걸립니다 (30분-1시간+)
```bash
python scripts/build_vectordb.py
```

### Option 3: Constitutional AI 챗봇 실행
```bash
# 1. 벡터 DB가 구축되어 있어야 함
# 2. .env에 OPENAI_API_KEY 설정 필요

python src/ui/app.py  # Streamlit UI
# 또는
python src/ui/gradio_app.py  # Gradio UI
```

## 💡 학습 경로

### 초급자 (1-2주)
1. `README.md` 읽기 - 프로젝트 개요 이해
2. `DESIGN_DECISIONS.md` 읽기 - 왜 이런 기술을 선택했는지
3. 작은 데이터셋으로 테스트 실행
4. `src/embeddings/embedder.py` 코드 읽기

### 중급자 (2-3주)
1. `LEARNING_GUIDE.md` Week 1-4 따라하기
2. 청킹 전략 실험 (chunk_size 변경)
3. Top-K 파라미터 조정 실험
4. `src/llm/constitutional_prompts.py` 분석

### 고급자 (4주+)
1. Constitutional Principles 직접 설계
2. Few-Shot 예시 추가
3. Self-Critique 메커니즘 개선
4. 평가 메트릭 개발 및 A/B 테스트

## 🔧 트러블슈팅

### 문제 1: `mutex.cc` 메시지에서 멈춤
**해결책:**
```bash
export TOKENIZERS_PARALLELISM=false
# 그 후 스크립트 재실행
```

자세한 내용은 `TROUBLESHOOTING.md` 참조.

### 문제 2: 임베딩 모델 다운로드 느림
**원인**: `jhgan/ko-sroberta-multitask` 모델 (약 1.1GB) 다운로드 중

**해결책**: 첫 실행 시 1-2분 소요는 정상입니다.

### 문제 3: 메모리 부족
**해결책**: `--max_docs` 파라미터로 문서 수 제한
```bash
python scripts/build_vectordb.py --max_files 10 --max_docs 50
```

### 문제 4: FAISS 또는 ChromaDB 설치 오류
**해결책:**
```bash
pip install faiss-cpu chromadb -U
```

## 📊 예상 결과

### 작은 테스트 (10개 파일, 100개 문서)
- **데이터**: 약 1,060개 행
- **청크**: 약 1,056개
- **임베딩 시간**: 2-3초
- **DB 구축 시간**: < 1초
- **총 시간**: 약 10-20초

### 중간 테스트 (100개 파일, 1,000개 문서)
- **데이터**: 약 10,000개 행
- **청크**: 약 10,000개
- **임베딩 시간**: 20-30초
- **DB 구축 시간**: 2-3초
- **총 시간**: 약 30초-1분

### 전체 데이터 (40,782개 파일)
- **데이터**: 약 250만개 문장
- **예상 청크**: 100만+
- **예상 시간**: 30분-1시간+
- **권장**: 서버 또는 GPU 환경

## 🎯 다음 단계

1. **Constitutional AI 이해하기**
   - `src/llm/constitutional_prompts.py` 읽기
   - 6가지 Principles 이해

2. **Few-Shot Learning 실험**
   - 예시 개수 조정 (0, 1, 3, 5)
   - 성능 비교

3. **Self-Critique 분석**
   - `src/llm/constitutional_chatbot.py` 읽기
   - 2-stage generation 이해

4. **나만의 챗봇 만들기**
   - Constitutional Principles 커스터마이징
   - 도메인 특화 Few-Shot 예시 추가

## 📚 추가 리소스

- **DESIGN_DECISIONS.md**: 모든 기술 선택의 이유
- **LEARNING_GUIDE.md**: 8주 학습 로드맵
- **TROUBLESHOOTING.md**: 자주 발생하는 문제 해결
- **USAGE_GUIDE.md**: 상세 사용법

## 💬 도움이 필요하신가요?

- **Issues**: 버그 리포트, 기능 제안
- **Discussions**: 질문, 아이디어 공유

---

**Happy Learning!** 🎓

이 프로젝트를 통해 최신 LLM 기술을 실제로 구현하고 이해하는 경험을 얻으시길 바랍니다!
