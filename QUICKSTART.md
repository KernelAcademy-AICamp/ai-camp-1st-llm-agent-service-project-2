# ⚡ RAG 베이스라인 빠른 시작 (5분)

## 🚀 바로 실행하기 (복사해서 붙여넣기)

```bash
# 1. 환경 설정 (처음 한 번만)
python -m venv .venv
source .venv/bin/activate  # Mac/Linux
# .venv\Scripts\activate  # Windows
pip install -r requirements.txt

# .env 파일 생성하고 OpenAI API 키 추가
echo "OPENAI_API_KEY=sk-your-key-here" > .env

# 2. 바로 테스트 (샘플 데이터로 동작 확인)
python run.py baseline

# 3. 자신의 실험 초기화 (git pull 받고 처음 한 번만 실행)
python run.py init-experiment --name myname --description "첫 실험"

# 4. Config 파일 수정 (생성된 파일: myname_config.yaml)
vim experiments/configs/members/myname/myname_config.yaml
# chunk_size, top_k, model 등 원하는 값으로 수정

# 5. 실험 실행
python run.py experiment --config experiments/configs/members/myname/myname_config.yaml

# 6. (선택) 추가 실험용 Config 복사 및 수정
cp experiments/configs/members/myname/myname_config.yaml \
   experiments/configs/members/myname/myname_config_chunk_256.yaml
# chunk_size: 256 등으로 수정 후
python run.py experiment --config experiments/configs/members/myname/myname_config_chunk_256.yaml
```



## 2️⃣ Device 설정 (중요!)

**experiments/baseline/config.yaml** 파일에서:

```yaml
# Mac M1/M4 사용자
device: "mps"

# Windows/Linux 사용자
device: "cpu"
```

---


## 4️⃣ 자신의 실험 시작

```bash
# 1. 실험 초기화
python run.py init-experiment --name jy --description "내 실험"

# 2. Config 수정
vim experiments/configs/members/jy/jy_config.yaml
# 예: chunk_size: 256으로 변경

# 3. 실험 실행 (캐시 자동 활용)
python run.py experiment --config experiments/configs/members/jy/jy_config.yaml
```

---

## 🆕 개선된 기능들

### 📦 캐시 시스템
```bash
# 캐시 목록 확인
python run.py list-caches

# 특정 캐시 사용
python run.py generate --config config.yaml --cache-key "fixed_512_bge-m3_faiss_flat_v1" --query "질문"

# 캐시 삭제
python run.py delete-cache --cache-key "old_cache"
```

### 🔄 효율적인 실험
- **청킹/임베딩/VectorDB 변경**: 자동 재인덱싱
- **검색/생성만 변경**: 캐시 재사용 (5초!)
- **팀원 간 캐시 공유**: 중복 작업 제거

---

## 📁 핵심 파일

```
prog_test/
├── run.py                    # 🎮 메인 CLI (개선된 v2)
├── .env                      # 🔑 API 키 설정 (OpenAI 사용시)
├── experiments/
│   ├── baseline/
│   │   └── config.yaml       # 📝 기본 설정
│   ├── configs/
│   │   ├── template_config.yaml  # 템플릿
│   │   └── members/          # 팀원별 설정 폴더
│   │       ├── wh/           # wh 팀원 설정
│   │       ├── jh/           # jh 팀원 설정
│   │       ├── jy/           # jy 팀원 설정
│   │       └── nw/           # nw 팀원 설정
│   ├── results/              # 팀원별 실험 결과
│   │   ├── wh/
│   │   ├── jh/
│   │   ├── jy/
│   │   └── nw/
│   └── indexed_data/         # 공유 캐시
└── requirements.txt          # 📦 패키지 목록
```

---

## ⚙️ API 키 설정 (선택사항)

기본은 로컬 모델(BGE-M3)을 사용하지만, OpenAI를 쓰려면:

**.env 파일:**
```env
# OpenAI GPT 사용시
OPENAI_API_KEY=sk-...your-key...
```

**config.yaml:**
```yaml
# 임베딩을 OpenAI로 변경
embedding:
  type: "openai"
  model: "text-embedding-ada-002"

# 생성 모델 설정
generation:
  provider: "openai"
  model: "gpt-3.5-turbo"
```

---

## 🆘 문제 해결

### "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### Mac에서 "MPS 오류"
```yaml
device: "cpu"  # mps → cpu로 변경
```

### 메모리 부족
```yaml
data:
  max_documents: 50  # 문서 수 줄이기
embedding:
  batch_size: 16    # 배치 크기 줄이기
```


---

## ✅ 정상 실행 확인

성공하면 이렇게 나옵니다:
```
🚀 Running Baseline RAG Experiment...
🔑 Cache Key: fixed_512_bge-m3_faiss_flat_v1
✅ Using cached index (또는 Creating new index)
✓ Loaded 4 documents
✓ Indexing complete: 15 chunks in 2.3s
✓ Evaluation complete
```

---

## 💡 핵심 명령어

```bash
# 기본 실행
python run.py baseline

# 캐시 활용 워크플로우
python run.py index --config config.yaml      # 인덱싱
python run.py search --config config.yaml --query "검색어"  # 검색만
python run.py generate --config config.yaml --query "질문"  # RAG 전체

# 캐시 관리
python run.py list-caches      # 캐시 목록
python run.py delete-cache --cache-key "key"  # 캐시 삭제

# 실험 관리
python run.py init-experiment --name "이름"  # 새 실험
python run.py experiment --config config.yaml  # 실험 실행
```

---