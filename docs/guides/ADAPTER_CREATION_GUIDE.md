# 🎯 QDoRA Adapter 제작 가이드

> **교통사고 전문 Adapter 제작 워크플로우**

## 📌 QDoRA란?

**QDoRA (Quantized Domain-Specific Adapter)**는 QLoRA의 확장 개념으로, 특정 도메인(법률 전문 분야)에 특화된 경량 어댑터입니다.

### QLoRA vs QDoRA
```
QLoRA: 범용 fine-tuning (모든 태스크)
QDoRA: 도메인 특화 fine-tuning (교통사고 전문)
  ↓
  - 도메인 특화 데이터만 사용
  - 도메인 특화 평가 지표
  - 도메인 특화 System Prompt
```

---

## 🗂️ Phase 1: 데이터 파이프라인 (1주)

### 1.1 교통사고 판례 필터링

**목적**: 로컬 32,525개 판례에서 교통사고 관련 추출

**파일**: `scripts/filter_traffic_data.py`

**키워드 전략**:
```python
TRAFFIC_KEYWORDS = [
    # 핵심 법률
    "교통사고처리특례법",
    "도로교통법",

    # 범죄 유형
    "음주운전", "무면허운전", "뺑소니",
    "난폭운전", "보복운전",

    # 결과
    "중상해", "교통사고", "인명사고",

    # 가중 처벌
    "특정범죄가중처벌법", "특가법",
]
```

**필터링 로직**:
```python
1. CSV 판례 파일 읽기 (04.형사법 폴더)
2. "판시사항" + "판결요지" 필드에서 키워드 매칭
3. 3개 이상 키워드 매칭 → 교통사고 판례로 분류
4. 중복 제거 (판례일련번호 기준)
5. 결과 저장: data/raw/traffic_precedents.json
```

**목표 결과**: 3,000-4,000건

---

### 1.2 Open API 추가 크롤링

**목적**: 최신 교통사고 판례 보강

**파일**: `scripts/crawl_traffic_precedents.py`

**API 활용**:
```python
# 국가법령정보센터 Open API
endpoint = "https://www.law.go.kr/DRF/lawSearch.do"
params = {
    "OC": "your_api_key",
    "target": "prec",  # 판례
    "query": "음주운전+교통사고",
    "display": 100,
    "sort": "date",  # 최신순
}
```

**크롤링 전략**:
1. 키워드별로 API 호출 (음주운전, 무면허, 뺑소니 등)
2. 2020년 이후 최신 판례 우선
3. 로컬 데이터와 중복 체크 (판례번호)
4. 결과 저장: `data/raw/traffic_precedents_api.json`

**목표 결과**: 1,000-2,000건

---

### 1.3 Instruction Tuning 데이터 변환

**목적**: QDoRA 학습용 Instruction Format 생성

**파일**: `scripts/prepare_instruction_data.py`

**변환 전략**:

#### 입력 (CSV 판례)
```csv
판례일련번호,구분,문장번호,내용
100029,판시사항,1,"업무상 과실치사죄로..."
100029,판결요지,2,"업무상 과실치사죄로..."
100029,판례내용,5,"【피 고 인】"
...
```

#### 출력 (Instruction Format)
```json
{
  "instruction": "다음 교통사고 사건을 분석하고, 관련 법률과 예상 판결을 제시하세요.",
  "input": "피고인은 업무상 과실로 차량을 운전하다 피해자를 사망케 하였습니다. 당시 차량 유리창에 성애가 끼어 있었고, 노폭이 2.4m인 비포장 도로였습니다.",
  "output": "## 법적 분석\n\n### 1. 관련 법령\n- 교통사고처리특례법 제3조 제1항\n- 형법 제268조 (업무상과실치사)\n\n### 2. 쟁점\n- 전방주시 의무 위반 여부\n- 성애 제거 의무 위반\n\n### 3. 판례 분석\n본 사건에서 원심은 피고인의 과실 내용을 명확히 밝히지 않아 파기되었습니다. 업무상과실치사죄를 적용하려면 구체적인 과실 내용이 입증되어야 합니다.\n\n### 4. 결론\n심리 미진으로 원심 파기 환송"
}
```

**변환 로직**:
```python
def create_instruction_data(precedent):
    # 1. 판시사항 → instruction
    instruction = f"다음 교통사고 사건을 분석하고, 관련 법률과 예상 판결을 제시하세요."

    # 2. 사실관계 추출 → input
    input_text = extract_facts(precedent["판례내용"])

    # 3. 판결요지 + 법리 → output
    output = format_legal_analysis(
        법령=precedent["참조조문"],
        판시사항=precedent["판시사항"],
        판결요지=precedent["판결요지"],
    )

    return {"instruction": instruction, "input": input_text, "output": output}
```

**목표 결과**: `data/traffic_instruction_5k.json` (5,000건)

---

## 🚀 Phase 2: Colab QDoRA 학습 (3-5일)

### 2.1 학습 환경 구성

**파일**: `notebooks/train_traffic_qdora.ipynb` (Colab Pro+)

**GPU**: A100 (40GB) 권장

---

### 2.2 학습 스크립트

```python
# ============================================
# 1. 라이브러리 설치
# ============================================
!pip install -q transformers peft bitsandbytes accelerate trl datasets

# ============================================
# 2. 데이터 로드
# ============================================
from datasets import load_dataset

# Google Drive 마운트 후 데이터 업로드
dataset = load_dataset("json", data_files="traffic_instruction_5k.json")
train_test = dataset["train"].train_test_split(test_size=0.1)

# ============================================
# 3. Kosaul 모델 로드 (4-bit Quantization)
# ============================================
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

model_name = "Bllossom/llama-3.2-Korean-Bllossom-3B"  # Kosaul 기반

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

tokenizer = AutoTokenizer.from_pretrained(model_name)
tokenizer.pad_token = tokenizer.eos_token

# ============================================
# 4. QDoRA 설정 (Domain-Specific LoRA)
# ============================================
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training

# 모델 준비
model = prepare_model_for_kbit_training(model)

# LoRA 설정 (교통사고 도메인 특화)
qdora_config = LoraConfig(
    r=16,                    # Rank (adapter 크기)
    lora_alpha=32,           # Scaling factor
    target_modules=[         # Fine-tune할 레이어
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, qdora_config)
model.print_trainable_parameters()
# 출력 예: trainable params: 42M (1.2%) || all params: 3.4B

# ============================================
# 5. 학습 설정
# ============================================
from transformers import TrainingArguments
from trl import SFTTrainer

training_args = TrainingArguments(
    output_dir="./traffic_qdora_v1",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=10,
    save_steps=100,
    save_total_limit=3,
    warmup_steps=50,
    lr_scheduler_type="cosine",
)

# ============================================
# 6. SFT Trainer로 학습
# ============================================
trainer = SFTTrainer(
    model=model,
    train_dataset=train_test["train"],
    eval_dataset=train_test["test"],
    peft_config=qdora_config,
    dataset_text_field="text",  # instruction + input + output 결합
    max_seq_length=2048,
    tokenizer=tokenizer,
    args=training_args,
)

# 학습 시작 (4-8시간 예상)
trainer.train()

# ============================================
# 7. Adapter 저장
# ============================================
model.save_pretrained("./traffic_adapter_v1")
tokenizer.save_pretrained("./traffic_adapter_v1")

# Google Drive에 백업
!cp -r ./traffic_adapter_v1 /content/drive/MyDrive/lawlaw_adapters/
```

---

### 2.3 하이퍼파라미터 설명

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| **r** | 16 | LoRA rank (클수록 표현력↑, 용량↑) |
| **lora_alpha** | 32 | Scaling factor (보통 r의 2배) |
| **learning_rate** | 2e-4 | 학습률 (QLoRA 권장값) |
| **batch_size** | 4 | A100 기준 최적값 |
| **epochs** | 3 | 과적합 방지 |
| **max_seq_length** | 2048 | 판례 길이 고려 |

---

## 📦 Phase 3: Adapter 배포 (3일)

### 3.1 Adapter 추출 및 검증

**Colab에서 생성된 파일**:
```
traffic_adapter_v1/
├── adapter_model.bin      # 50-200MB (핵심!)
├── adapter_config.json    # LoRA 설정
└── tokenizer files
```

**검증 테스트**:
```python
# Adapter 로드 테스트
from peft import PeftModel

base_model = AutoModelForCausalLM.from_pretrained(model_name)
model = PeftModel.from_pretrained(base_model, "./traffic_adapter_v1")

# 샘플 추론
prompt = "음주운전 3회, 무면허, 중상해 사건의 예상 형량은?"
output = generate(model, prompt)
print(output)
```

---

### 3.2 Ollama 통합

**Option 1: Adapter Merge (권장)**
```python
# Adapter를 base model에 병합
from peft import PeftModel

base_model = AutoModelForCausalLM.from_pretrained(model_name)
model = PeftModel.from_pretrained(base_model, "./traffic_adapter_v1")
merged_model = model.merge_and_unload()

# GGUF로 변환 (llama.cpp 사용)
# 1. HF 체크포인트 저장
merged_model.save_pretrained("./kosaul_traffic_merged")

# 2. GGUF 변환 (로컬에서)
# python llama.cpp/convert.py ./kosaul_traffic_merged
# llama.cpp/quantize ./kosaul_traffic_merged/ggml-model-f16.gguf ./kosaul_traffic_q4.gguf Q4_K_M
```

**Modelfile 작성**: `Modelfile_traffic_v1`
```dockerfile
FROM ./models/kosaul_traffic_q4.gguf

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER stop "<|im_end|>"

SYSTEM """
당신은 교통사고 전문 변호사 AI입니다.

전문 분야:
- 음주운전, 무면허운전, 뺑소니
- 교통사고처리특례법, 특가법 적용 사건
- 인명사고, 중상해 사건

답변 원칙:
1. 판례 기반 분석 (출처 명시)
2. 쟁점 중심 설명
3. 구체적 양형 제시
4. 합의/변론 전략 제안
"""

TEMPLATE """<|im_start|>system
{{ .System }}<|im_end|>
<|im_start|>user
{{ .Prompt }}<|im_end|>
<|im_start|>assistant
"""
```

**Ollama 모델 생성**:
```bash
cd /Users/jaehyungpark/Documents/libraries/lawlaw
ollama create lawlaw:traffic -f Modelfile_traffic_v1
```

---

### 3.3 로컬 테스트 및 평가

**테스트 케이스**: `tests/traffic_test_cases.json`

```json
[
  {
    "case": "음주운전 3회 + 무면허 + 중상해",
    "expected": "특가법 제5조의11, 2-5년 징역",
    "accuracy_threshold": 0.8
  },
  {
    "case": "뺑소니 + 사망사고",
    "expected": "특가법 제5조의3, 무기 또는 3년 이상",
    "accuracy_threshold": 0.9
  }
]
```

**평가 스크립트**: `scripts/evaluate_adapter.py`

```python
import ollama

def evaluate_adapter():
    baseline_model = "kosaul:latest"
    adapter_model = "lawlaw:traffic"

    test_cases = load_json("tests/traffic_test_cases.json")

    for case in test_cases:
        # Baseline 응답
        baseline_response = ollama.chat(baseline_model, case["case"])

        # Adapter 응답
        adapter_response = ollama.chat(adapter_model, case["case"])

        # 평가 (GPT-4 또는 사람이 점수 매김)
        baseline_score = evaluate_response(baseline_response, case["expected"])
        adapter_score = evaluate_response(adapter_response, case["expected"])

        print(f"Case: {case['case']}")
        print(f"Baseline: {baseline_score:.2f}")
        print(f"Adapter: {adapter_score:.2f}")
        print(f"Improvement: {adapter_score - baseline_score:.2f}\n")
```

**목표 성능**:
- Baseline 대비 +30% 정확도 향상
- 판례 인용률 90%+
- 법리 해석 정확도 85%+

---

## 📊 예상 성능

| 지표 | Baseline Kosaul | Traffic Adapter | 개선 |
|------|----------------|-----------------|------|
| **교통사고 정확도** | 65% | **90%** | +38% |
| **판례 매칭** | 70% | **95%** | +36% |
| **법리 해석** | 60% | **85%** | +42% |
| **추론 속도** | 20 tok/s | 20 tok/s | 동일 |
| **모델 크기** | 4.9GB | **5.1GB** | +200MB |

---

## 📂 최종 파일 구조

```
lawlaw/
├── scripts/
│   ├── filter_traffic_data.py           # 교통사고 판례 필터링
│   ├── crawl_traffic_precedents.py      # Open API 크롤링
│   ├── prepare_instruction_data.py      # Instruction 변환
│   └── evaluate_adapter.py              # 성능 평가
│
├── notebooks/
│   └── train_traffic_qdora.ipynb        # Colab 학습 노트북
│
├── data/
│   ├── raw/
│   │   ├── traffic_precedents.json      # 로컬 필터링 결과
│   │   └── traffic_precedents_api.json  # API 크롤링 결과
│   └── traffic_instruction_5k.json      # 학습 데이터
│
├── adapters/
│   └── traffic_v1/
│       ├── adapter_model.bin            # Adapter weights (50-200MB)
│       └── adapter_config.json          # LoRA config
│
├── models/
│   └── kosaul_traffic_q4.gguf          # Merged + quantized model
│
├── tests/
│   └── traffic_test_cases.json          # 평가 케이스
│
├── Modelfile_traffic_v1                 # Ollama 설정
└── ADAPTER_CREATION_GUIDE.md            # 이 문서
```

---

## ⏱️ 타임라인

### Week 1: 데이터 준비
- Day 1-2: 필터링 스크립트 작성 및 실행
- Day 3-4: Open API 크롤링
- Day 5-7: Instruction 데이터 변환 및 검증

### Week 2: 학습 및 최적화
- Day 1: Colab 환경 구성
- Day 2: 학습 실행 (4-8시간)
- Day 3-4: 하이퍼파라미터 튜닝
- Day 5: 재학습 (필요시)

### Week 3: 배포 및 테스트
- Day 1-2: Adapter merge 및 GGUF 변환
- Day 3: Ollama 통합
- Day 4-5: 성능 평가 및 문서화

**총 소요 기간**: 2-3주

---

## 🚀 다음 단계: Phase 2 확장

교통사고 Adapter 완성 후:

1. **형사 일반 Adapter** (절도, 사기, 폭행)
2. **마약범죄 Adapter**
3. **기업범죄 Adapter**
4. **민사 Adapter**
5. **성범죄 Adapter**

각 Adapter는 동일한 워크플로우로 2주 내 제작 가능.

---

## 📌 참고 자료

- [QLoRA Paper](https://arxiv.org/abs/2305.14314)
- [PEFT Documentation](https://huggingface.co/docs/peft)
- [Ollama Modelfile Syntax](https://github.com/ollama/ollama/blob/main/docs/modelfile.md)
- [국가법령정보센터 Open API](https://open.law.go.kr/)
