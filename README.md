# [여기에 팀 이름을 입력하세요] 🤖 LLM Agent 기반 OOO 서비스 개발

_본 레포지토리는 'LLM Agent 서비스 개발'을 위한 템플릿입니다._
_프로젝트를 시작하기 전, 팀원들과 함께 `[ ]`로 표시된 부분을 채워주세요._

## 1. 👥 팀원 및 역할

| 이름 | GitHub |
| :--- |  :--- |
| [이름] |  [GitHub ID] |
| [이름] |  [GitHub ID] |
| [이름] |  [GitHub ID] |
| [이름] |  [GitHub ID] |

---

## 2. 🎯 프로젝트 개요

### 2.1. 프로젝트 주제
- **`[여기에 구체적인 프로젝트 주제를 입력하세요]`**
- 예: 바이오 연구자를 위한 RAG 기반 논문 분석 및 인사이트 도출 플랫폼

### 2.2. 제작 배경 (해결하고자 하는 문제)
- `[프로젝트가 해결하고자 하는 핵심 문제를 1~2줄로 요약]`
- `[이 문제가 왜 중요한지, 현재 어떤 어려움(Pain Point)이 있는지 서술]`

### 2.3. 핵심 목표 (제공하는 가치)
- `[위 문제를 해결하기 위해 우리 서비스가 제공하는 핵심 기능 및 가치 서술]`
- 예:
    1.  **정보 탐색 시간 단축**: LLM Agent가 ...
    2.  **도메인 특화 분석**: ...
    3.  **트렌드 시각화**: ...

---

## 3. 🛠️ 기술 스택 (Tech Stack)

본 프로젝트는 다음 기술 스택을 기반으로 합니다. (팀별 상황에 맞게 수정 가능)

| 구분 | 기술 |
| :--- | :--- |
| **Backend / FEP** | Python, FastAPI, (Django), LangChain |
| **Frontend** | Streamlit, (HTML/JS, React.js) |
| **Database** | Vector DB (Chroma, FAISS 등), (PostgreSQL) |
| **AI / ML** | OpenAI API, Gemini API, Hugging Face, (도메인 특화 모델) |
| **Infra / Tools** | Git, Docker, SonarQube |

---

## 4. 🚀 시작하기 (Getting Started)

### 4.1. 개발 환경 통일
- **Python 버전**: `[예: 3.10.x]`
- **OS**: `[예: Ubuntu 22.04 LTS 또는 Windows 11]`
- **주요 라이브러리**: `requirements.txt` 참조

### 4.2. 설치 및 실행
1.  **레포지토리 복제**
    ```bash
    git clone [본 레포지토리 URL]
    cd [프로젝트 폴더명]
    ```

2.  **가상 환경 생성 및 활성화**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\activate

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **의존성 설치**
    ```bash
    pip install -r requirements.txt
    ```

4.  **환경 변수 설정**
    `.env.example` 파일을 복사하여 `.env` 파일을 생성하고, 필요한 API Key 등을 입력합니다.
    ```bash
    cp .env.example .env
    # .env 파일 열어서 [YOUR_API_KEY] 등 수정
    ```

5.  **서비스 실행**
    ```bash
    # 예: FastAPI 실행
    uvicorn backend.main:app --reload
    ```

---

## 5. 🌳 레포지토리 구조

```
/ 
├── backend/        # API 서버 (FastAPI/Django 소스코드)
├── frontend/       # 웹 UI (Streamlit/React 소스코드)
├── core/           # RAG 파이프라인, 임베딩 등 핵심 AI 로직
├── scripts/        # 배치 스크립트, 데이터 수집/전처리 유틸리티
├── notebooks/      # 데이터 탐색, 모델 테스트용 Jupyter Notebook
├── data/           # (Git-ignored) 원본/전처리 데이터
├── docs/           # 아키텍처, ERD, WBS 등 문서 산출물
│
├── .env.example    # 환경 변수 템플릿
├── requirements.txt# Python 의존성
└── README.md       # 프로젝트 소개 문서
```

---

## 6. 룰 & 가이드라인 (Rules & Guidelines)

### 6.1. 핵심 수행 규칙
1.  **매일 오전 10시 KST** : 팀 스크럼 진행 (어제 한 일, 오늘 할 일, 장애물 공유)
2.  **문서화**: 아키텍처, ERD 등 주요 산출물은 **[Notion 링크]`** 에 문서화하고 팀원과 공유합니다.
3.  **환경 통일**: Python 및 주요 라이브러리 버전을 통일하여 개발 환경 차이로 인한 문제를 방지합니다. (`requirements.txt` 준수)
4.  **보안**: API Key, DB 접속 정보 등 민감 정보는 `.env` 파일을 사용하며, 절대로 Git에 커밋하지 않습니다. (`.gitignore` 확인)

### 6.2. Git 브랜치 전략
본 프로젝트는 **Git Flow**를 기반으로 한 브랜치 전략을 따릅니다.

-   **`master`**: 최종 릴리즈(배포) 브랜치. (7주차 발표회)
-   **`develop`**: 개발의 중심이 되는 브랜치.
-   **`feature/[기능명]`**: 신규 기능 개발 브랜치. (예: `feature/pdf-processing`)
    -   개발 완료 후 `develop` 브랜치로 Pull Request(PR)
-   **`hotfix/[버그명]`**: `master` 브랜치의 긴급 버그 수정.


```
[개발 플로우]

feature 브랜치 생성 (git checkout -b feature/my-feature develop)

기능 개발 및 커밋

develop 브랜치로 PR 요청 (코드 리뷰 진행)

develop 브랜치에 Merge
```

---

## 7. 🗓️ 프로젝트 로드맵 (7-Week Plan)

| 주차 | 핵심 목표 | 주요 산출물 |
| :--- | :--- | :--- |
| **1주차** | **기획 및 아키텍처 설계** | 시스템 아키텍처, ERD, WBS |
| **2주차** | **데이터 수집 및 전처리** | 데이터 수집/전처리/배치 모듈 코드 |
| **3주차** | **임베딩 및 벡터 DB 구축** | 임베딩 추출/DB 저장 모듈 코드 |
| **4주차** | **핵심 로직 구현 (RAG/Agent)** | RAG 응답 기능 소스코드 |
| **5주차** | **애플리케이션 기능 개발** | 유사도 검색, 비교, 추천 기능 코드 |
| **6주차** | **UI/UX 구현 및 고도화** | 트렌드 분석/웹 UI 소스코드 |
| **7주차** | **최적화, 테스트 및 배포** | **동작하는 웹 서비스 (최종 산출물)** |

---

## 8. 📄 산출물 링크 (Documentation)

> 팀의 Notion, Fimga 등 관련 링크를 업데이트하세요.

-   **[➡️ 서비스 기획서 및 요구사항 명세서]([링크])`**
-   **[➡️ 시스템 아키텍처 다이어그램]([링크])`**
-   **[➡️ 데이터베이스 ERD]([링크])`**
-   **[➡️ 팀 WBS / Scrum 보드]([링크])`**

---

## 9. 🏁 최종 결과물 (Final Deliverables)

1.  **웹 UI 기반 서비스**: `[최종 배포된 서비스 URL]`
2.  **데이터 처리 모듈**: 데이터 수집, 전처리, 배치 프로세싱 모듈 소스코드
3.  **임베딩 및 DB 모듈**: 임베딩 추출 및 Vector DB 저장 모듈 소스코드
4.  **핵심 기능 모듈**: RAG 응답, 유사 논문 추천, 비교, 트렌드 분석 모듈 코드
5.  **최종 발표 자료 및 데모 영상**
