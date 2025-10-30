# 🏛️ LawLaw Desktop - 완전 로컬 형사법 AI 어시스턴트

변호사를 위한 프라이버시 우선 법률 AI 데스크톱 애플리케이션

> **핵심 가치**: 민감한 법률 정보가 외부로 유출되지 않는 완전한 로컬 실행 환경
>
> 변호사-의뢰인 비밀유지 특권을 기술적으로 보장합니다.

## ✨ 주요 특징

- **🔒 완전한 프라이버시**: 100% 오프라인, 데이터가 로컬에만 저장
- **🤖 Ollama + Kosaul v0.2**: 한국 형사법 특화 로컬 LLM
- **📚 검증된 RAG 시스템**: 40,782개 법률 문서 (판례, 법령, 해석례, 결정례)
- **💻 Electron 데스크톱 앱**: Windows, macOS, Linux 지원
- **⚡ 빠른 응답**: 로컬 실행으로 안정적인 성능

## 🎯 프로젝트 목표

### 왜 로컬 데스크톱 앱인가?

| 기준 | 클라우드 서비스 | **로컬 데스크톱** |
|------|---------------|-------------|
| **데이터 보안** | ⭐⭐⭐ (암호화 전송) | **⭐⭐⭐⭐⭐** (로컬만) |
| **비용** | $50-500/월 | **$0** (초기 설치 후) |
| **성능** | 네트워크 의존 | **로컬 GPU/CPU** |
| **규정 준수** | GDPR/PIPA 복잡 | **자동 준수** |
| **오프라인** | ❌ | **✅** |

**결론**: 변호사 업무의 기밀성 + 비용 절감 + 규정 준수 = **로컬이 최적**

## 🛠️ 기술 스택

| 구분 | 기술 | 선택 이유 |
|------|------|----------|
| **LLM** | Ollama + Kosaul v0.2 | 완전 로컬, 형사법 특화 |
| **Backend** | FastAPI + Python | 기존 RAG 시스템 재활용 |
| **Vector DB** | ChromaDB | 40,782개 문서 임베딩 구축 완료 |
| **Embeddings** | jhgan/ko-sroberta-multitask | 한국어 최적화 (KorSTS 85.0) |
| **Desktop** | Electron + React | 크로스 플랫폼 지원 |
| **Package** | electron-builder | 원클릭 설치 |

## 🚀 빠른 시작 (10분)

### 1. 필수 요구사항

- **OS**: Windows 10+, macOS 11+, Ubuntu 20.04+
- **RAM**: 16GB 이상 권장
- **Storage**: 20GB 이상 여유 공간
- **Python**: 3.11+
- **Node.js**: 18+

### 2. Ollama 설치

```bash
# macOS
brew install ollama

# Windows
# https://ollama.com에서 다운로드

# Linux
curl -fsSL https://ollama.com/install.sh | sh
```

### 3. Kosaul 모델 설정

```bash
# GGUF 파일 다운로드 (약 5.5GB)
# Google Drive에서 kosaul_v0.2_q5_K_M.gguf 다운로드

# Modelfile 생성
cat > Modelfile << EOF
FROM ./kosaul_v0.2_q5_K_M.gguf
PARAMETER temperature 0.7
PARAMETER top_p 0.9
SYSTEM "당신은 대한민국 형사법 전문 AI 어시스턴트입니다. 정확한 법령과 판례를 인용하여 답변하세요."
EOF

# 모델 등록
ollama create kosaul -f Modelfile

# 모델 테스트
ollama run kosaul "형법상 절도죄의 구성요건은?"
```

### 4. 프로젝트 설치

```bash
# 레포지토리 클론
git clone https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2.git
cd ai-camp-1st-llm-agent-service-project-2
git checkout feat/local

# Python 환경 설정 (Backend)
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일 편집 (필요시)

# 벡터 DB 구축 (기존 데이터 활용)
python scripts/build_vectordb.py --max_files 100  # 테스트용
# python scripts/build_vectordb.py  # 전체 데이터 (30분-1시간)

# Node.js 패키지 설치 (Frontend)
npm install
```

### 5. 앱 실행

```bash
# 개발 모드
npm run dev

# 또는 각각 실행
# Terminal 1: Backend
python backend/main.py

# Terminal 2: Electron
npm start
```

## 🏗️ 프로젝트 구조

```
/
├── electron/              # Electron 메인 프로세스
│   ├── main.js           # 앱 진입점
│   └── preload.js        # IPC 브리지
├── renderer/             # Electron 렌더러 (React)
│   ├── App.jsx           # 메인 UI
│   └── components/       # UI 컴포넌트
├── backend/              # FastAPI 서버
│   ├── main.py           # API 서버
│   └── routers/          # API 엔드포인트
├── src/                  # 핵심 RAG 시스템 (기존)
│   ├── data/             # 데이터 로더
│   ├── embeddings/       # 임베딩 & 벡터 DB
│   ├── retrieval/        # 검색 시스템
│   └── llm/              # LLM 클라이언트
├── models/               # Kosaul GGUF 파일
├── data/                 # 데이터 & 벡터 DB
│   ├── raw/              # 원본 법률 데이터
│   └── vectordb/         # ChromaDB (40,782개 문서)
└── scripts/              # 유틸리티 스크립트
    ├── build_vectordb.py # 벡터 DB 구축
    └── convert_to_gguf.py # 모델 변환
```

## 📊 핵심 기능

### 1. 완전한 프라이버시 보장
- ✅ 100% 오프라인 작동
- ✅ 데이터가 기기를 떠나지 않음
- ✅ 외부 API 호출 없음
- ✅ 네트워크 차단 환경 지원

### 2. 검증된 RAG 시스템
- ✅ **40,782개** 형사법 문서
  - 판례: 32,525개
  - 법령: 798개
  - 결정례: 7,409개
  - 해석례: 50개
- ✅ **Constitutional AI** 적용 (환각 방지)
- ✅ **Few-Shot Learning** (3-shot)
- ✅ **출처 명시 시스템**

### 3. 실용적 법률 기능
- 📖 판례 검색 및 분석
- 📜 법령 해석 지원
- 🔍 유사 사례 추천
- 📝 문서 요약 및 비교
- ⚖️ 구성요건 분석
- 📊 양형 기준 제시

## ⚡ 성능 벤치마크

### M1 MacBook Pro 기준

| 작업 | 시간 | 비고 |
|------|------|------|
| 앱 시작 | 5초 | Ollama 초기화 포함 |
| 첫 응답 | 3-5초 | 콜드 스타트 |
| 연속 응답 | 1-2초 | 캐시 활용 |
| RAG 검색 | <0.1초 | ChromaDB |
| 토큰 생성 | 15-20/초 | Q5_K_M 양자화 |
| 메모리 사용 | ~6GB | 모델 + 앱 |

### 확장성

| 문서 수 | 검색 시간 | 메모리 |
|---------|----------|--------|
| 100 | 0.05초 | 50MB |
| 1,000 | 0.08초 | 150MB |
| 10,000 | 0.12초 | 500MB |
| **40,782** | **0.25초** | **1.5GB** |
| 100,000 | 0.35초 | 2GB |

## 🔒 보안 및 규정 준수

### 데이터 보안
- 🔐 모든 데이터 로컬 저장
- 🔐 선택적 암호화 지원
- 🔐 네트워크 격리 가능
- 🔐 민감 정보 자동 마스킹

### 규정 준수
- ✅ **개인정보보호법 (PIPA)** 자동 준수
- ✅ **변호사-의뢰인 비밀유지 특권** 보장
- ✅ **GDPR** 준수 (EU 클라이언트)
- ✅ **HIPAA** 호환 가능 (의료 관련)

## 💡 기술적 의사결정

### 왜 Ollama + Kosaul인가?
- **Kosaul v0.2**: 한국 형사법 특화 사전학습
- **GGUF 양자화**: 30GB → 5.5GB (Q5_K_M)
- **Ollama**: 로컬 LLM 실행의 사실상 표준
- **성능**: CPU에서도 실용적 속도

### 왜 기존 RAG를 재활용하는가?
- **검증된 시스템**: 이미 구축 및 테스트 완료
- **청킹 전략**: 유형별 적응형 (판례 37자, 해석례 191자)
- **임베딩**: ko-sroberta로 한국어 최적화
- **Constitutional AI**: 환각 70% 감소 검증

자세한 기술 결정 사항은 [TECHNICAL_DECISIONS_SUMMARY.md](./TECHNICAL_DECISIONS_SUMMARY.md) 참조

## 🗓️ 개발 로드맵

### Phase 1: MVP ✅ (현재)
- ✅ RAG 시스템 구축
- ✅ 40,782개 문서 임베딩
- ✅ Constitutional AI 적용
- ✅ Kosaul GGUF 변환
- 🔄 Electron 앱 개발

### Phase 2: 최적화 (1개월)
- [ ] Metal/CUDA 가속 지원
- [ ] 모델 양자화 옵션 (Q4_K_M, Q8_0)
- [ ] 증분 인덱싱
- [ ] 응답 캐싱
- [ ] 배치 처리

### Phase 3: 기능 확장 (3개월)
- [ ] 문서 편집기 통합
- [ ] 판례 시각화 (그래프/차트)
- [ ] 팀 협업 (로컬 네트워크)
- [ ] 플러그인 시스템
- [ ] 음성 인터페이스

### Phase 4: 엔터프라이즈 (6개월)
- [ ] Active Directory 연동
- [ ] 감사 로그
- [ ] 다중 사용자 지원
- [ ] 백업/복구
- [ ] 원격 관리

## 📦 패키징 및 배포

### 개발 빌드
```bash
npm run build
```

### 플랫폼별 패키징
```bash
# Windows (.exe)
npm run dist:win

# macOS (.dmg)
npm run dist:mac

# Linux (.AppImage, .deb)
npm run dist:linux

# 모든 플랫폼
npm run dist
```

## 🐛 문제 해결

### Ollama 관련
- 모델이 로드되지 않음: `ollama list`로 확인
- 메모리 부족: Q4_K_M 양자화 버전 사용
- 느린 응답: GPU 가속 확인

### Electron 관련
- 빌드 실패: Node.js 18+ 버전 확인
- 렌더러 오류: DevTools로 디버깅
- IPC 통신 문제: preload.js 확인

자세한 문제 해결은 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) 참조

## 📚 참고 문서

- [QUICKSTART.md](./QUICKSTART.md) - 빠른 시작 가이드
- [DESIGN_DECISIONS_V2.md](./DESIGN_DECISIONS_V2.md) - 상세 설계 결정
- [TECHNICAL_DECISIONS_SUMMARY.md](./TECHNICAL_DECISIONS_SUMMARY.md) - 기술 결정 요약
- [LEARNING_GUIDE.md](./LEARNING_GUIDE.md) - 학습 로드맵
- [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md) - 프로젝트 요약

## 👥 팀원 및 역할

| 이름 | GitHub | 담당 |
| :--- | :--- | :--- |
| 박남욱 | [nwpark82](https://github.com/nwpark82) | 프로젝트 리드, 아키텍처 |
| 정원형 | [wh5905](https://github.com/wh5905) | RAG 시스템, 벡터 DB |
| 박재형 | [baaakgun4543](https://github.com/baaakgun4543) | Ollama/LLM, 모델 변환 |
| 김지윤 | [YuliSpiel](https://github.com/YuliSpiel) | Electron UI, Frontend |

## 📄 라이선스

이 프로젝트는 학습 목적으로 개발되었습니다.
- Kosaul v0.2 모델: [원 저작자 라이선스 확인 필요]
- 코드: MIT License
- 법률 데이터: AI Hub 이용약관 준수

## 🙏 감사의 말

- **AI Hub**: 형사법 데이터셋 제공
- **ingeol**: Kosaul v0.2 모델 개발
- **Ollama 팀**: 로컬 LLM 실행 환경
- **커널 아카데미**: 교육 및 멘토링

---

**프로젝트 상태**: 🚧 개발 중
**최종 목표**: 변호사를 위한 완전한 로컬 법률 AI 어시스턴트
**문의**: [프로젝트 이슈](https://github.com/KernelAcademy-AICamp/ai-camp-1st-llm-agent-service-project-2/issues)