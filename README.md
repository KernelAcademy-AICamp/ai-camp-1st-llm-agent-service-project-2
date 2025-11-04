# [2팀] 🚗 교통 법률 AI 에이전트 서비스

_LLM 기반 교통 관련 법률 판례 검색 및 질의응답 서비스_

---

## 📌 프로젝트 현황

| 항목 | 상태 |
|------|------|
| **진행률** | 85% |
| **현재 단계** | RAG 시스템 구축 완료 |
| **다음 단계** | 임베딩 생성 및 자동화 |

**✅ 최근 업데이트**: ChromaDB RAG 시스템 구현 완료 (2025-11-04)

---

## 1. 👥 팀원 및 역할

| 이름 | GitHub | 역할 |
| :--- |  :--- | :--- |
| 박남욱 | [nwpark82](https://github.com/nwpark82) | 팀장, 백엔드 |
| 정원형 | [wh5905](https://github.com/wh5905) | RAG 시스템 |
| 박재형 | [baaakgun4543](https://github.com/baaakgun4543) | 데이터 처리 |
| 김지윤 | [YuliSpiel](https://github.com/YuliSpiel) | 프론트엔드 |

---

## 2. 🎯 프로젝트 개요

### 2.1. 프로젝트 주제
**교통 법률 AI 에이전트 서비스**
- 교통사고 관련 판례 및 법령 검색
- RAG 기반 법률 질의응답
- 유사 판례 추천 시스템

### 2.2. 해결하고자 하는 문제
- 교통사고 피해자/가해자가 법률 정보에 쉽게 접근하기 어려움
- 방대한 판례 중 유사 사례 찾기 어려움
- 법률 전문 용어로 인한 이해 어려움

### 2.3. 핵심 가치
1. **빠른 법률 정보 접근** - 11,769건 판례 데이터 즉시 검색
2. **AI 기반 맞춤 답변** - GPT-4를 활용한 쉬운 법률 설명
3. **유사 판례 추천** - 의미적 유사도 기반 관련 판례 제공

---

## 3. 🏗️ 시스템 아키텍처

```
사용자
  ↓
FastAPI REST API
  ├─ Upload API (PDF OCR)
  ├─ Documents API (문서 관리)
  ├─ OCR API (텍스트 추출)
  └─ RAG API ⭐ (판례 검색, 질의응답)
  ↓
┌──────────┬──────────┬──────────┐
│PostgreSQL│ ChromaDB │  MinIO   │
│(메타데이터)│(벡터 DB)  │(파일 저장)│
└──────────┴──────────┴──────────┘
```

**주요 구성**:
- **FastAPI**: REST API 서버
- **PostgreSQL**: 문서 메타데이터, 사용자 관리
- **ChromaDB**: 판례 임베딩 벡터 저장 (11,769건)
- **OpenAI**: 임베딩 생성 & GPT-4 질의응답
- **Tesseract**: PDF OCR 처리

---

## 4. 🛠️ 기술 스택

| 구분 | 기술 |
| :--- | :--- |
| **Backend** | Python 3.11, FastAPI 0.115.9 |
| **Database** | PostgreSQL 16.2, ChromaDB 0.3.23, Redis 7.2 |
| **AI/ML** | OpenAI API (text-embedding-3-small, GPT-4o-mini), Tesseract OCR |
| **Storage** | MinIO (S3-compatible) |
| **Infrastructure** | Docker, Docker Compose, Alembic |

---

## 5. 🚀 빠른 시작

### 5.1. 환경 설정

```bash
# 1. 저장소 클론
git clone https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2.git
cd ai-camp-1st-llm-agent-service-project-2

# 2. 환경 변수 설정
cp .env.example .env
# .env 파일 편집: OPENAI_API_KEY 설정

# 3. Docker 서비스 시작
docker-compose up -d

# 4. Python 의존성 설치
pip install -r requirements.txt
```

### 5.2. 데이터 확인

현재 **11,769건**의 교통 관련 판례가 준비되어 있습니다:

```bash
# 통합 데이터 확인 (444MB)
ls -lh unified_traffic_data/

# 필터링된 원본 확인 (21MB)
ls -lh filtered_traffic_data/
```

### 5.3. RAG 시스템 테스트

#### 샘플 테스트 (빠른 체험)
```bash
export OPENAI_API_KEY='your-api-key'

# 20건 샘플로 테스트 (1~2분, ~$0.01)
python3 scripts/test_chromadb_with_sample.py --sample-size 20
```

#### 전체 임베딩 생성 (선택)
```bash
# 11,769건 전체 (15~20분, ~$0.47)
python3 scripts/create_embeddings_chromadb.py \
  unified_traffic_data/unified_traffic_data_20251103_174822.json \
  --openai-api-key $OPENAI_API_KEY \
  --chroma-dir ./chroma_db
```

### 5.4. API 서버 시작

```bash
# FastAPI 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# API 문서 확인
open http://localhost:8000/docs
```

---

## 6. 📡 API 사용 예시

### 6.1. 유사 판례 검색

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
      "사건번호": "2007노799",
      "법원명": "전주지방법원",
      "판결요지": "교통사고처리특례법 제4조...",
      "similarity_score": 0.92
    }
  ]
}
```

### 6.2. 법률 질의응답 (RAG)

```bash
curl -X POST "http://localhost:8000/api/v1/rag/legal-qa" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "음주운전으로 사고를 냈을 때 처벌은?",
    "top_k": 3
  }'
```

**응답**:
```json
{
  "question": "음주운전으로 사고를 냈을 때 처벌은?",
  "answer": "도로교통법 제44조에 따르면, 음주운전으로 사고를 낸 경우 특정범죄가중처벌법이 적용됩니다...",
  "sources": [...]
}
```

### 6.3. API 문서

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## 7. 📊 데이터 현황

### 7.1. 수집 데이터

| 타입 | 건수 | 비율 | 전문 포함 |
|------|------|------|----------|
| **판례** | 9,198건 | 78.2% | 81.2% |
| **법령** | 2,093건 | 17.8% | - |
| **결정례** | 466건 | 4.0% | 81.2% |
| **해석례** | 12건 | 0.1% | - |
| **합계** | **11,769건** | 100% | - |

### 7.2. 데이터 소스

- **학습 데이터**: AI Hub 형사법 LLM 데이터 (75,046건 → 11,769건 필터링)
- **크롤링 데이터**: 법제처 OpenAPI (주기적 업데이트 예정)

### 7.3. 키워드 필터링

**강한 키워드** (7개):
- 교통사고, 도로교통법, 음주운전, 뺑소니, 교통사고처리특례법, 무면허운전, 신호위반

**일반 키워드** (40+개):
- 차량, 자동차, 속도위반, 중앙선침범, 안전운전, 보험가입, 운전면허 등

---

## 8. 🗂️ 프로젝트 구조

```
ai-camp-1st-llm-agent-service-project-2/
├── app/                          # FastAPI 애플리케이션
│   ├── api/v1/
│   │   ├── endpoints/           # API 엔드포인트
│   │   │   ├── upload.py
│   │   │   ├── documents.py
│   │   │   └── ocr.py
│   │   └── rag.py              # RAG API ⭐
│   ├── core/                    # 핵심 설정
│   ├── models/                  # DB 모델
│   ├── services/                # 비즈니스 로직
│   └── main.py
│
├── scripts/                     # 데이터 처리 스크립트
│   ├── filter_traffic_from_training_data.py    # 필터링
│   ├── unify_to_crawling_format.py            # 형식 통합
│   ├── create_embeddings_chromadb.py          # 임베딩 생성
│   ├── test_chromadb_with_sample.py           # 샘플 테스트
│   └── crawl_legal_cases.py                   # 크롤링
│
├── docs/                        # 문서
│   └── archive/                # 참고 문서
│       ├── CHROMADB_SETUP_GUIDE.md
│       ├── RAG_DATA_STRUCTURE_ANALYSIS.md
│       └── PERIODIC_UPDATE_WORKFLOW.md
│
├── filtered_traffic_data/       # 필터링된 데이터 (21MB)
├── unified_traffic_data/        # 통합 데이터 (444MB)
├── chroma_db/                   # ChromaDB 저장소
│
├── docker-compose.yml           # Docker 설정
├── requirements.txt             # Python 의존성
├── .env.example                 # 환경 변수 템플릿
├── SYSTEM_DESIGN.md            # 시스템 설계서 ⭐
├── PROJECT_STATUS_SUMMARY.md   # 프로젝트 현황
└── README.md                    # 본 문서
```

---

## 9. 📚 주요 문서

### 필수 문서
- **[SYSTEM_DESIGN.md](SYSTEM_DESIGN.md)** - 시스템 설계서 (⭐ 메인 문서)
- **[PROJECT_STATUS_SUMMARY.md](PROJECT_STATUS_SUMMARY.md)** - 프로젝트 현황 정리

### 참고 문서 (docs/archive/)
- **[CHROMADB_SETUP_GUIDE.md](docs/archive/CHROMADB_SETUP_GUIDE.md)** - ChromaDB 설정 가이드
- **[RAG_DATA_STRUCTURE_ANALYSIS.md](docs/archive/RAG_DATA_STRUCTURE_ANALYSIS.md)** - RAG 시스템 분석
- **[PERIODIC_UPDATE_WORKFLOW.md](docs/archive/PERIODIC_UPDATE_WORKFLOW.md)** - 자동화 워크플로우
- **[UNIFIED_DATA_FORMAT.md](docs/archive/UNIFIED_DATA_FORMAT.md)** - 데이터 형식 명세

---

## 10. 🎯 로드맵

### ✅ 완료 (85%)
- [x] FastAPI 기본 구조
- [x] PostgreSQL, Redis, MinIO 설정
- [x] Tesseract OCR 통합
- [x] 학습 데이터 필터링 (11,769건)
- [x] 크롤링 형식 통합 (444MB)
- [x] ChromaDB RAG 시스템
- [x] RAG API 구현
  - [x] 유사 판례 검색
  - [x] 법률 질의응답
  - [x] 판례 추천
  - [x] 통계 조회

### 🚧 진행 중 (10%)
- [ ] 전체 데이터 임베딩 (11,769건)
- [ ] 주기적 크롤링 자동화
- [ ] 성능 최적화

### 📋 계획 (5%)
- [ ] 인증/권한 시스템
- [ ] 프론트엔드 개발
- [ ] 배포 및 모니터링

---

## 11. 💰 예상 비용

### OpenAI API (월간)
| 항목 | 비용 |
|------|------|
| 초기 임베딩 (11,769건) | ~$0.47 (1회) |
| 일일 크롤링 (~50건) | ~$0.06/월 |
| 질의응답 (100건/일) | ~$2.10/월 |
| **월간 합계** | **~$2.63** |

### 인프라
- Docker, PostgreSQL, ChromaDB, Redis: **무료** (Self-hosted)

---

## 12. 🔒 Git 브랜치 전략

```
main              # 프로덕션 브랜치
  └─ Feat/crawling   # 크롤링 기능 개발 (현재)
      ├─ feature/rag           # RAG 시스템 ✅
      ├─ feature/data-pipeline # 데이터 처리 ✅
      └─ feature/ocr          # OCR 시스템 ✅
```

---

## 13. 📞 문의 및 기여

### 이슈 보고
- GitHub Issues를 통해 버그 리포트 및 기능 제안

### 기여 방법
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 14. 📄 라이선스

본 프로젝트는 교육 목적으로 제작되었습니다.

---

## 15. 🏁 최종 결과물 (예정)

1. **웹 서비스**: 판례 검색 및 법률 질의응답 UI
2. **RAG API**: 유사 판례 검색, GPT 기반 답변
3. **데이터 파이프라인**: 자동 크롤링 및 업데이트
4. **문서화**: 시스템 설계서, API 문서, 사용 가이드

---

**최종 업데이트**: 2025-11-04
**현재 버전**: v0.8.5
**진행률**: 85%

🚀 **Next Step**: 전체 데이터 임베딩 생성 → API 성능 테스트 → 프론트엔드 개발
