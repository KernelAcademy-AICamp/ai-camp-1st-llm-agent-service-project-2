# 트러블슈팅 가이드

## 문제: 임베딩 모델 로딩 시 `mutex.cc` 메시지에서 멈춤

### 증상
```
[mutex.cc : 452] RAW: Lock blocking 0x12f6f8968   @
```

이 메시지가 나타나고 프로그램이 진행되지 않음.

### 원인
1. **sentence-transformers 최신 버전 (5.x) 호환성 이슈**
   - tokenizers 라이브러리와의 충돌
   - 병렬 처리 중 mutex lock 발생

2. **HuggingFace 모델 다운로드 문제**
   - 처음 실행 시 `jhgan/ko-sroberta-multitask` 모델 다운로드 (약 1.1GB)
   - 네트워크 또는 캐시 문제로 다운로드 중단

### 해결 방법

#### 방법 1: sentence-transformers 다운그레이드 (✅ 추천)
```bash
pip install sentence-transformers==2.7.0
```

**이유**: 2.7.0 버전이 안정적이고 검증됨

#### 방법 2: 환경 변수 설정
```bash
export TOKENIZERS_PARALLELISM=false
export TRANSFORMERS_OFFLINE=0
```

스크립트 실행 전에 설정:
```bash
export TOKENIZERS_PARALLELISM=false
python scripts/build_vectordb.py
```

#### 방법 3: OpenAI Embeddings 사용
로컬 모델 대신 OpenAI API 사용:

`.env` 파일에 설정:
```
USE_OPENAI_EMBEDDINGS=true
OPENAI_API_KEY=your-key-here
```

`configs/config.py`에 추가:
```python
use_openai_embeddings = os.getenv("USE_OPENAI_EMBEDDINGS", "false").lower() == "true"
```

**장점**:
- 모델 다운로드 불필요
- 즉시 실행 가능
- 품질 우수

**단점**:
- API 비용 발생 (약 $0.0001/1K tokens)

#### 방법 4: 모델 수동 다운로드
```python
from sentence_transformers import SentenceTransformer

# 미리 다운로드
model = SentenceTransformer('jhgan/ko-sroberta-multitask')
```

#### 방법 5: 더 작은 한국어 모델 사용
`configs/config.py`에서 모델 변경:
```python
EMBEDDING_MODEL="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
```

이 모델은 더 작고 (420MB) 빠르게 다운로드됨.

### 학습 목적 설명

이런 문제가 발생하는 이유:

1. **의존성 버전 관리의 중요성**
   - 최신 버전이 항상 좋은 것은 아님
   - 프로덕션에서는 안정적인 버전 사용

2. **임베딩 모델 선택의 트레이드오프**
   - 로컬 모델: 무료, 오프라인 가능, 하지만 초기 다운로드 필요
   - API: 즉시 사용, 고품질, 하지만 비용 발생

3. **병렬 처리와 Lock**
   - tokenizers는 기본적으로 병렬 처리 활성화
   - 일부 환경에서는 mutex lock 문제 발생
   - `TOKENIZERS_PARALLELISM=false`로 비활성화 가능

### 권장 설정 (requirements.txt)

```
# 안정적인 버전들
sentence-transformers==2.7.0
transformers==4.36.0
tokenizers==0.15.0

# 또는 OpenAI 사용
openai==1.12.0
```

### 추가 디버깅

로그 레벨 증가:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

HuggingFace 캐시 확인:
```bash
ls -lh ~/.cache/huggingface/hub/
```

캐시 삭제 (문제 지속 시):
```bash
rm -rf ~/.cache/huggingface/
```
