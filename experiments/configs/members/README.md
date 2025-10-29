# 멤버별 실험 Config 가이드

## 🚀 새로운 실험 시작하기

### 방법 1: init 명령 사용 (권장)

```bash
python run.py init [이름] "[실험 설명]"

# 예시
python run.py init jh "JH의 첫 실험"
```

**자동으로 생성되는 것:**
- `experiments/configs/members/jh/jh_baseline.yaml`
- `experiments/results/jh/` 폴더
- Config에 올바른 `results_dir` 자동 설정

---

### 방법 2: 기존 Config 복사 (주의 필요)

다른 사람의 config를 참고하려면:

```bash
# 1. Config 복사
cp experiments/configs/members/wh/wh_config_chunk_512.yaml \
   experiments/configs/members/jh/jh_config_chunk_512.yaml

# 2. 필수 수정 항목
vim experiments/configs/members/jh/jh_config_chunk_512.yaml
```

**⚠️ 반드시 수정해야 할 항목:**

```yaml
experiment_name: jh_experiment  # ← 본인 이름으로 변경
author: jh                      # ← 본인 이름으로 변경

experiment:
  results_dir: experiments/results/jh/  # ← 본인 폴더로 변경!
```

**수정하지 않으면 발생하는 문제:**
- 다른 사람의 results 폴더에 결과가 저장됨
- 실험 결과가 섞임

---

## 📂 폴더 구조

```
experiments/
├── configs/members/
│   ├── jh/
│   │   ├── jh_baseline.yaml
│   │   └── jh_config_chunk_512.yaml
│   ├── jy/
│   ├── nw/
│   └── wh/
└── results/
    ├── jh/  ← jh의 모든 실험 결과
    ├── jy/  ← jy의 모든 실험 결과
    ├── nw/
    └── wh/
```

**규칙:**
- Config 폴더: `experiments/configs/members/{이름}/`
- Results 폴더: `experiments/results/{이름}/`

---

## ✅ Config 검증

실험 실행 전 자동으로 검증됩니다:

```bash
python run.py experiment --config experiments/configs/members/jh/jh_config.yaml
```

**검증 항목:**
- ✅ results_dir이 본인 폴더를 가리키는지
- ✅ chunk_size, top_k 등 파라미터 유효 범위
- ✅ API keys 설정 여부

---

## 🎯 베스트 프랙티스

### 1. 네이밍 컨벤션

```
{이름}_config_{설명}.yaml

예시:
- jh_baseline.yaml
- jh_config_chunk_512.yaml
- jh_config_mmr_reranking.yaml
```

### 2. Config에 주석 추가

```yaml
# JH - 실험 목적: chunk_size 512 vs 1024 비교
chunking:
  chunk_size: 512  # 작은 청크로 정밀한 검색 테스트
```

### 3. 실험 설명 작성

```yaml
experiment_name: jh_experiment_v1
description: "chunk_size 512, MMR 검색, OpenAI embedding 조합 테스트"
```

---

## 🔍 문제 해결

**Q: 다른 사람 폴더에 결과가 저장됨**

```bash
# Config 파일 확인
cat experiments/configs/members/jh/jh_config.yaml | grep results_dir

# 출력이 다른 사람 이름이면 수정 필요:
# results_dir: experiments/results/wh/  ← 잘못됨!
# results_dir: experiments/results/jh/  ← 올바름!
```

**Q: init으로 만든 config를 찾을 수 없음**

```bash
# 멤버 폴더 확인
ls -la experiments/configs/members/jh/

# config 파일 이름은 {이름}_baseline.yaml
```

**Q: 실험 결과가 섞임**

- 각 실험은 타임스탬프로 구분됩니다
- `results_20251029_123456.json` 형식
- 같은 폴더에 여러 실험 결과 저장 가능

---

## 📚 추가 참고

- 전체 Config 옵션: `experiments/configs/template_config.yaml`
- Config 검증 규칙: `core/config/README.md`
- Claude Code 가이드: `CLAUDE_CODE_GUIDE.md`
