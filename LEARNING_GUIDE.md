# 형사법 RAG 챗봇 학습 가이드

> **목표**: RAG, Constitutional AI, Few-Shot Learning 등 최신 LLM 기술을 실제로 구현하고 이해하기

## 🎓 학습 목표

이 프로젝트를 통해 배울 수 있는 것들:

1. **RAG (Retrieval-Augmented Generation)**
   - 왜 RAG가 필요한가?
   - Fine-tuning vs RAG 비교
   - 벡터 데이터베이스 구축 및 활용

2. **임베딩 (Embeddings)**
   - 텍스트를 벡터로 변환하는 이유
   - 한국어 특화 모델 선택 기준
   - 코사인 유사도 계산

3. **청킹 전략 (Chunking)**
   - 왜 문서를 나누어야 하는가?
   - 최적의 chunk size 결정
   - Overlap의 역할

4. **Constitutional AI**
   - AI에게 원칙을 부여하는 방법
   - 자기 검증 메커니즘
   - Hallucination 방지

5. **Few-Shot Learning**
   - 0-shot vs Few-shot 비교
   - 최적의 예시 개수
   - 예시 선택 기준

6. **프롬프트 엔지니어링**
   - 효과적인 프롬프트 구조
   - 법률 AI를 위한 특수 고려사항

---

## 📚 학습 로드맵

### Phase 1: 기초 이해 (1-2주)

#### Week 1: RAG 개념과 임베딩

**읽어볼 것**:
- `DESIGN_DECISIONS.md` 섹션 1, 2
- Lewis et al. (2020) - "Retrieval-Augmented Generation" 논문

**실습**:
```python
# 1. 임베딩 생성 실험
from src.embeddings.embedder import KoreanLegalEmbedder

embedder = KoreanLegalEmbedder()

# 유사한 문장들 임베딩
texts = [
    "절도죄는 타인의 재물을 절취하는 범죄이다",
    "도둑질은 남의 물건을 훔치는 행위이다",
    "사기죄는 사람을 속여 재물을 취득하는 범죄이다"
]

embeddings = embedder.embed_documents(texts)

# 유사도 비교
sim_1_2 = embedder.compute_similarity(embeddings[0], embeddings[1])
sim_1_3 = embedder.compute_similarity(embeddings[0], embeddings[2])

print(f"절도죄 vs 도둑질: {sim_1_2:.4f}")  # 높은 유사도 (같은 의미)
print(f"절도죄 vs 사기죄: {sim_1_3:.4f}")  # 낮은 유사도 (다른 범죄)
```

**질문해볼 것**:
1. 왜 코사인 유사도를 사용하는가? (유클리드 거리와 차이)
2. 임베딩 차원이 768인 이유는?
3. 한국어 모델과 영어 모델의 성능 차이는?

#### Week 2: 청킹과 벡터 DB

**읽어볼 것**:
- `DESIGN_DECISIONS.md` 섹션 3, 4
- ChromaDB 공식 문서

**실습**:
```python
# 청킹 실험
from src.data.preprocessor import LawTextPreprocessor

preprocessor = LawTextPreprocessor(chunk_size=500, chunk_overlap=50)

# 긴 판결문 청킹
long_text = """
제329조(절도) 타인의 재물을 절취한 자는 6년 이하의 징역 또는
1천만원 이하의 벌금에 처한다.

제330조(야간주거침입절도) 야간에 사람의 주거...
"""

chunks = preprocessor.chunk_text(long_text)

print(f"원본 길이: {len(long_text)} 자")
print(f"청크 개수: {len(chunks)}")
for i, chunk in enumerate(chunks):
    print(f"Chunk {i+1}: {len(chunk['text'])} 자")
```

**실험 과제**:
1. chunk_size를 300, 500, 800으로 바꿔가며 결과 비교
2. overlap 0%, 10%, 20% 비교
3. 어떤 설정이 검색 품질이 좋은지 테스트

---

### Phase 2: RAG 파이프라인 구축 (2-3주)

#### Week 3: 벡터 DB 구축

**실습**: 실제 데이터로 벡터 DB 만들기

```bash
# 테스트용 (1000개 문서)
python scripts/build_vectordb.py \
    --db_type chroma \
    --max_docs 1000 \
    --test_query "절도죄의 구성요건은?"

# 전체 데이터 (시간 소요)
python scripts/build_vectordb.py \
    --db_type chroma
```

**관찰할 것**:
1. 임베딩 생성 시간 (1000개 vs 10000개)
2. 벡터 DB 크기
3. 검색 속도

**A/B 테스트**:
```python
# ChromaDB vs FAISS 비교
import time

# ChromaDB
start = time.time()
chroma_results = chroma_db.search(query_embedding, top_k=5)
chroma_time = time.time() - start

# FAISS
start = time.time()
faiss_results = faiss_db.search(query_embedding, top_k=5)
faiss_time = time.time() - start

print(f"ChromaDB: {chroma_time:.4f}s")
print(f"FAISS: {faiss_time:.4f}s")
```

#### Week 4-5: RAG 검색 실험

**실습**: 다양한 검색 전략 비교

```python
from src.retrieval.retriever import LegalDocumentRetriever

retriever = LegalDocumentRetriever(vectordb, embedder, top_k=5)

# 1. 기본 검색
results_basic = retriever.retrieve("절도죄란?")

# 2. 다양성 고려 검색
results_diverse = retriever.get_diverse_results(
    "절도죄란?",
    diversity_threshold=0.85
)

# 3. 스코어 필터링
results_filtered = retriever.retrieve_with_scores(
    "절도죄란?",
    score_threshold=0.7
)

# 비교 분석
print("기본 검색:", len(results_basic))
print("다양성 검색:", len(results_diverse))
print("필터링 검색:", len(results_filtered))
```

**실험 메트릭**:
```python
def evaluate_retrieval(query, expected_doc_ids, retrieved_docs):
    """검색 품질 평가"""
    retrieved_ids = [doc['id'] for doc in retrieved_docs]

    # Precision: 검색된 것 중 관련 문서 비율
    relevant_retrieved = set(expected_doc_ids) & set(retrieved_ids)
    precision = len(relevant_retrieved) / len(retrieved_ids)

    # Recall: 관련 문서 중 검색된 비율
    recall = len(relevant_retrieved) / len(expected_doc_ids)

    # F1 Score
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {
        'precision': precision,
        'recall': recall,
        'f1': f1
    }
```

---

### Phase 3: Constitutional AI (2주)

#### Week 6: Constitutional Principles 이해

**읽어볼 것**:
- `DESIGN_DECISIONS.md` 섹션 7
- Anthropic (2022) - "Constitutional AI" 논문
- `src/llm/constitutional_prompts.py` 코드

**실습**: 원칙 위반 찾기

```python
from src.llm.constitutional_prompts import ConstitutionalPrinciples

# 나쁜 답변 예시 (원칙 위반)
bad_answer = """
절도죄는 남의 물건을 훔치면 됩니다.
초범이면 집행유예 받을 수 있어요!
"""

# 좋은 답변 예시 (원칙 준수)
good_answer = """
절도죄(형법 제329조)는 "타인의 재물을 절취한 자는
6년 이하의 징역 또는 1천만원 이하의 벌금에 처한다"고
규정하고 있습니다.

[판례: 대법원 2020도1234]에 따르면...

⚠️ 이는 법률 정보이며, 실제 사건은 변호사와 상담하세요.
"""

# 어떤 원칙을 위반/준수했는지 분석해보세요!
```

**과제**:
1. 각 원칙이 왜 필요한지 설명하기
2. 원칙 위반 사례 5개 만들기
3. Constitutional Principles 1개 추가 제안하기

#### Week 7: Self-Critique 구현

**실습**: 자기 검증 메커니즘

```python
from src.llm.constitutional_chatbot import ConstitutionalLawChatbot

# Self-Critique 활성화
chatbot = ConstitutionalLawChatbot(
    retriever=retriever,
    llm_client=llm_client,
    enable_self_critique=True,
    critique_threshold=0.5
)

# 디버그 모드로 검증 과정 확인
response = chatbot.chat(
    "절도죄란?",
    include_critique_log=True
)

print("=== 초기 답변 ===")
print(response['answer'])

print("\n=== 검증 결과 ===")
print(response.get('critique', {}))

print(f"\n수정 여부: {response['revised']}")
```

**실험**:
```python
# 실험: Self-Critique 효과 측정

results_with_critique = []
results_without_critique = []

test_queries = [
    "절도죄란?",
    "사기죄 vs 횡령죄",
    "정당방위 요건은?"
]

# With Self-Critique
chatbot_with = ConstitutionalLawChatbot(
    retriever, llm_client,
    enable_self_critique=True
)

for query in test_queries:
    response = chatbot_with.chat(query)
    results_with_critique.append(response)

# Without Self-Critique
chatbot_without = ConstitutionalLawChatbot(
    retriever, llm_client,
    enable_self_critique=False
)

for query in test_queries:
    response = chatbot_without.chat(query)
    results_without_critique.append(response)

# 비교 분석: 출처 명시율, 면책 조항 포함 여부 등
```

---

### Phase 4: Few-Shot Learning (1주)

#### Week 8: Few-Shot 실험

**읽어볼 것**:
- `DESIGN_DECISIONS.md` 섹션 6
- `src/llm/constitutional_prompts.py` - FewShotExamples

**실습**: Shot 수 비교

```python
# 0-Shot (예시 없음)
prompt_0shot = """
질문: 절도죄란?

답변:
"""

# 1-Shot
prompt_1shot = """
예시:
Q: 사기죄란?
A: 사기죄(형법 제347조)는...

질문: 절도죄란?

답변:
"""

# 3-Shot (현재 설정)
prompt_3shot = FewShotExamples.format_examples() + """
질문: 절도죄란?

답변:
"""

# 5-Shot
prompt_5shot = """
[5개 예시...]

질문: 절도죄란?

답변:
"""

# 결과 비교
# - 답변 품질
# - 토큰 사용량
# - 응답 시간
```

**실험 결과 분석**:
```python
import matplotlib.pyplot as plt

shot_counts = [0, 1, 3, 5]
quality_scores = [3.2, 4.1, 4.7, 4.8]  # 사람이 평가
token_costs = [100, 300, 700, 1100]  # 토큰 수

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

ax1.plot(shot_counts, quality_scores, marker='o')
ax1.set_title('답변 품질 vs Shot 수')
ax1.set_xlabel('Shot 수')
ax1.set_ylabel('품질 점수 (1-5)')

ax2.plot(shot_counts, token_costs, marker='o', color='red')
ax2.set_title('토큰 비용 vs Shot 수')
ax2.set_xlabel('Shot 수')
ax2.set_ylabel('토큰 수')

plt.tight_layout()
plt.show()

# 결론: 3-shot이 품질과 비용의 최적점!
```

---

## 🔬 실험 프로젝트

### 실험 1: 청킹 전략 최적화

**목표**: 최적의 chunk_size와 overlap 찾기

**방법**:
```python
from src.llm.constitutional_chatbot import ExperimentalChatbot

configs = [
    {'chunk_size': 300, 'overlap': 30},
    {'chunk_size': 500, 'overlap': 50},  # 현재 설정
    {'chunk_size': 800, 'overlap': 100},
]

test_queries = [
    "절도죄 구성요건은?",
    "정당방위 요건은?",
    # ... 더 많은 테스트 쿼리
]

results = {}

for config in configs:
    # 각 설정으로 벡터 DB 재구축
    preprocessor = LawTextPreprocessor(**config)
    # ... (벡터 DB 구축)

    chatbot = ExperimentalChatbot(retriever, llm_client, config)

    for query in test_queries:
        response = chatbot.chat(query)
        # 결과 저장

    results[str(config)] = chatbot.get_experiment_results()

# 결과 비교 및 시각화
```

### 실험 2: 임베딩 모델 비교

**목표**: 한국어 모델 간 성능 비교

**방법**:
```python
models = [
    "jhgan/ko-sroberta-multitask",  # 현재
    "BM-K/KoSimCSE-roberta",
    "snunlp/KR-SBERT-V40K-klueNLI-augSTS"
]

for model_name in models:
    embedder = KoreanLegalEmbedder(model_name=model_name)
    # 벡터 DB 구축
    # 검색 테스트
    # 메트릭 수집
```

### 실험 3: Constitutional AI 효과 측정

**목표**: Self-Critique의 실제 효과 검증

**평가 기준**:
1. 출처 명시율
2. Hallucination 발생률
3. 답변 품질 (사람 평가)

```python
def evaluate_constitutional_ai(answers):
    metrics = {
        'cite_rate': 0,  # 출처 명시 비율
        'hallucination_rate': 0,  # 환각 발생 비율
        'disclaimer_rate': 0,  # 면책 조항 포함 비율
        'professional_tone': 0  # 전문적 어조 (1-5)
    }

    for answer in answers:
        # [법령:...] 또는 [판례:...] 포함 여부
        if '[법령:' in answer or '[판례:' in answer:
            metrics['cite_rate'] += 1

        # ⚠️ 포함 여부
        if '⚠️' in answer:
            metrics['disclaimer_rate'] += 1

        # ... 더 많은 메트릭

    # 비율 계산
    for key in metrics:
        metrics[key] /= len(answers)

    return metrics
```

---

## 💡 확장 아이디어

### 1. Hybrid Search 구현

**RAG 개선**:
```python
# Semantic Search + BM25 (키워드)
from rank_bm25 import BM25Okapi

class HybridRetriever:
    def __init__(self, vectordb, embedder):
        self.semantic_retriever = SemanticRetriever(vectordb, embedder)
        self.bm25 = None  # 초기화 필요

    def retrieve(self, query, top_k=5, semantic_weight=0.7):
        # Semantic 검색
        semantic_results = self.semantic_retriever.retrieve(query, top_k=20)

        # BM25 검색
        bm25_results = self.bm25_search(query, top_k=20)

        # 가중 합산 및 재순위화
        combined = self.combine_results(
            semantic_results,
            bm25_results,
            semantic_weight
        )

        return combined[:top_k]
```

### 2. 답변 품질 자동 평가

**RAGAS (RAG Assessment) 프레임워크**:
```python
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy

# 답변이 검색 문서에 충실한가?
faithfulness_score = faithfulness.score(
    question=query,
    answer=answer,
    contexts=retrieved_docs
)

# 답변이 질문과 관련있는가?
relevancy_score = answer_relevancy.score(
    question=query,
    answer=answer
)
```

### 3. 다양한 프롬프트 전략

**Chain-of-Thought (CoT)**:
```python
COT_PROMPT = """
질문: {question}

단계적으로 생각해봅시다:

1단계: 이 질문의 핵심은 무엇인가?
2단계: 관련 법령은 무엇인가?
3단계: 관련 판례는 어떻게 판단했는가?
4단계: 위 내용을 종합하면?

최종 답변:
"""
```

**Tree-of-Thought (ToT)**:
```python
# 여러 추론 경로를 탐색하고 최선 선택
```

---

## 📊 평가 및 개선

### 메트릭 수집

```python
class MetricsCollector:
    def __init__(self):
        self.metrics = {
            'retrieval': {
                'precision': [],
                'recall': [],
                'mrr': []  # Mean Reciprocal Rank
            },
            'generation': {
                'faithfulness': [],  # 검색 문서 기반 답변 비율
                'cite_rate': [],  # 출처 명시 비율
                'hallucination_rate': []  # 환각 발생 비율
            },
            'user_experience': {
                'response_time': [],
                'satisfaction': []  # 사용자 만족도 (1-5)
            }
        }

    def log_query(self, query, response, ground_truth=None):
        """각 쿼리의 메트릭 기록"""
        # ... 메트릭 계산 및 저장

    def generate_report(self):
        """종합 리포트 생성"""
        # ... 통계 분석 및 시각화
```

### 사용자 피드백

```python
# Streamlit UI에 피드백 버튼 추가
if st.button("👍 도움이 되었어요"):
    collect_feedback(query, answer, rating=5)

if st.button("👎 별로예요"):
    collect_feedback(query, answer, rating=1)
    reason = st.text_input("어떤 점이 아쉬웠나요?")
```

---

## 🎯 학습 체크리스트

### 기초

- [ ] RAG가 무엇이고 왜 필요한지 설명할 수 있다
- [ ] 임베딩이 텍스트를 어떻게 벡터로 변환하는지 안다
- [ ] 코사인 유사도를 계산할 수 있다
- [ ] 청킹의 목적과 중요성을 이해한다

### 중급

- [ ] 벡터 데이터베이스를 직접 구축할 수 있다
- [ ] 다양한 검색 전략을 비교 실험할 수 있다
- [ ] Constitutional AI의 핵심 개념을 설명할 수 있다
- [ ] Few-Shot Learning의 효과를 실험으로 검증할 수 있다

### 고급

- [ ] 여러 임베딩 모델의 성능을 비교 분석할 수 있다
- [ ] 자신만의 Constitutional Principles를 정의할 수 있다
- [ ] A/B 테스트로 시스템을 개선할 수 있다
- [ ] 답변 품질을 정량적으로 평가할 수 있다

---

## 📖 추천 읽을거리

### 논문
1. Lewis et al. (2020) - "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
2. Anthropic (2022) - "Constitutional AI: Harmlessness from AI Feedback"
3. Brown et al. (2020) - "Language Models are Few-Shot Learners" (GPT-3)

### 블로그/아티클
- Anthropic Blog: Constitutional AI
- HuggingFace: Sentence Transformers Guide
- OpenAI Cookbook: Embeddings Guide

### 도구 문서
- ChromaDB Documentation
- FAISS Documentation
- LangChain Documentation

---

## 🤝 커뮤니티

**토론 주제**:
1. 법률 AI에서 가장 중요한 것은 정확성인가, 설명가능성인가?
2. Constitutional AI의 한계는 무엇인가?
3. Few-Shot Learning의 최적 예시 개수는 도메인마다 다른가?
4. RAG vs Fine-tuning, 언제 무엇을 선택해야 하는가?

**기여 방법**:
1. 새로운 Few-Shot 예시 추가
2. Constitutional Principles 개선
3. 평가 메트릭 제안
4. 버그 리포트 및 수정

---

이 프로젝트를 통해 단순히 코드를 작성하는 것을 넘어,
**왜 이런 기술을 사용하는지, 어떤 상황에서 효과적인지**를
깊이 이해하시길 바랍니다!

Happy Learning! 🚀
