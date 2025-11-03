# CSV 판결문 전문 저장 방식 설명

## ❓ 질문: CSV 파일 판결 내용이 저장되나요?

**답변: 현재는 CSV 파일 경로만 저장되고, 실제 내용은 저장되지 않습니다.**

---

## 📊 현재 상태 (Option 1) - 기본값

### 저장되는 내용

```json
{
  "documents": [
    {
      "id": "...",
      "title": "교통사고처리특례법위반",
      "metadata": {
        "source_csv_path": ".data/.../TS_판결문/HS_P_79038.csv",
        "source_csv_exists": false
      }
    }
  ],
  "structured_data": [
    {
      "section_type": "instruction",
      "content": "질의에 대한 응답은..."
    },
    {
      "section_type": "input",
      "content": "교통사고를 일으킨 차량이..."
    },
    {
      "section_type": "output",
      "content": "교통사고처리특례법 제4조 제1항은... (판결 요지 전체)"
    }
  ]
}
```

### ✅ 포함되는 것
- Instruction (지시사항)
- Input (질문)
- **Output (판결 요지 및 법원 판단)**
- CSV 파일 경로 (metadata)

### ❌ 포함되지 않는 것
- CSV 파일의 50+ 문장 (피고인 정보, 주문, 이유, 사실 관계 등)

### 📊 데이터 크기
- JSON 파일: 56MB
- Structured Data: 27,436행
- Documents: 11,769건

---

## 🎯 Option 1 vs Option 2 비교

| 항목 | Option 1 (현재) | Option 2 (전문 포함) |
|------|----------------|-------------------|
| **CSV 전문 저장** | ❌ 경로만 | ✅ 전체 내용 |
| **파일 크기** | 56MB | ~300MB (5~6배) |
| **Structured Data** | 27,436행 | ~200,000행 |
| **판결 요지** | ✅ output_text | ✅ output_text |
| **판결 전문** | CSV 파일 참조 | DB에 직접 저장 |
| **검색 속도** | 빠름 | 느림 |
| **DB 부담** | 낮음 | 높음 |
| **추가 작업** | 없음 | 스크립트 실행 필요 |

---

## 💡 추천: Option 1 (현재 방식)

### 이유 1: Output에 이미 충분한 정보 포함

**Output 예시:**
> 교통사고처리특례법 제4조 제1항은 '교통사고를 일으킨 차'가 보험에 가입된 경우 공소를 제기할 수 없도록 규정하고 있습니다. 여기서 '보험에 가입된 경우'란, 교통사고를 일으킨 당해 차량뿐만 아니라 그 차량의 운전자가 피해자에게 손해배상금 전액을 배상할 수 있는 보험에 가입된 경우를 포함합니다. 따라서 이 사건의 경우 피고인이 다른 자동차에 대한 보험에 가입하여 피해자가 손해배상을 받을 수 있었다면, 교통사고처리특례법 제4조 제1항의 특례 규정이 적용될 수 있습니다. 이러한 이유로 검사의 항소는 이유 없으므로, 형사소송법 제364조 제4항에 따라 주문과 같이 검사의 항소를 기각합니다.

**포함 내용:**
- ✅ 법조문 해석
- ✅ 법원 판단
- ✅ 주문 내용
- ✅ 적용 법리

**대부분의 사용자에게 충분합니다!**

---

### 이유 2: 전문이 필요한 경우는 드뭅니다

**사용 케이스별:**

| 사용 케이스 | 필요한 내용 | 현재 방식 충분? |
|------------|-----------|--------------|
| AI 챗봇 학습 | 판결 요지 | ✅ |
| RAG 시스템 | 판결 요지 + 법리 | ✅ |
| 일반 사용자 검색 | 요약본 | ✅ |
| 법률 전문가 | 전문 (필요시) | ⚠️ 동적 로딩 |
| 학술 연구 | 전문 (일부) | ⚠️ 동적 로딩 |

---

### 이유 3: 필요시 동적으로 로딩 가능

**API 구현 예시:**

```python
# app/api/v1/documents.py

@router.get("/{document_id}/full-text")
async def get_document_full_text(document_id: str):
    """판결문 전문 조회 (필요시에만)"""

    # 1. Document 조회
    document = await get_document(document_id)

    # 2. output_text 먼저 반환 (빠름)
    ai_label = await get_ai_label(document_id)
    summary = ai_label.output_text

    # 3. 전문이 요청되면 CSV 파일 읽기
    if request.query_params.get("include_full_text") == "true":
        csv_path = document.metadata.get("source_csv_path")

        if csv_path and os.path.exists(csv_path):
            full_text = read_csv_file(csv_path)
            return {
                "summary": summary,
                "full_text": full_text
            }

    return {
        "summary": summary,
        "full_text": None
    }
```

**사용자 경험:**
```
1. 기본 조회: 판결 요지만 표시 (빠름)
2. "더 자세히 보기" 버튼 클릭
3. 전문 로딩 (필요시에만)
```

---

## 🔧 Option 2가 필요한 경우

### 다음과 같은 경우에만 고려하세요:

1. **전문 검색이 필수인 경우**
   - "피고인의 이름으로 검색"
   - "특정 증거 번호로 검색"

2. **CSV 파일 접근이 불가능한 경우**
   - 원본 CSV 파일이 삭제됨
   - CSV 파일이 다른 서버에 있음

3. **매우 빠른 전문 조회가 필요한 경우**
   - 대량 전문 분석
   - 실시간 전문 비교

### Option 2 실행 방법

```bash
# 스크립트 실행
python3 scripts/add_csv_fulltext_to_structured_data.py \
  converted_training_data/converted_training_db_format_20251103_170534.json

# 확인 메시지
⚠️  CSV 전문 추가 확인
이 작업은 다음과 같은 영향이 있습니다:
  - 파일 크기: 56MB → 약 300MB (5~6배 증가)
  - Structured Data: 27,436행 → 약 200,000행
  - 처리 시간: 약 10~20분 소요

계속 진행하시겠습니까? (yes/no):
```

---

## 📋 실제 사용 시나리오

### 시나리오 1: AI 챗봇 (Option 1 충분)

```
사용자: 교통사고 무보험 차량 관련 판례 알려줘

챗봇: [DB에서 ai_labels.output_text 조회]
      교통사고처리특례법 제4조 제1항에 따르면...
      (판결 요지 전체 제공)

사용자: 👍 (만족)
```

**결과: 빠르고 효율적**

---

### 시나리오 2: 법률 전문가 (Option 1 + 동적 로딩)

```
전문가: 교통사고 무보험 관련 판례 검색

시스템: [판결 요지 표시]
        교통사고처리특례법 제4조 제1항에 따르면...

        [더 자세히 보기] 버튼

전문가: [버튼 클릭]

시스템: [CSV 파일 읽기 - 0.1초]
        【피 고 인】
        【항 소 인】 검사
        【주    문】 검사의 항소를 기각한다.
        【이    유】1.항소이유의 요지...
        (전문 50+ 문장 제공)

전문가: 👍 (만족)
```

**결과: 필요한 사람만 전문 보기, DB 부담 없음**

---

## 🎯 최종 추천

### ✅ 권장 방식: Option 1 (현재)

**이유:**
1. output_text에 판결 요지 포함 → 대부분의 경우 충분
2. DB 크기 작음 → 빠른 검색, 낮은 비용
3. 전문 필요시 동적 로딩 가능

### 📝 구현 체크리스트

- [x] JSON 파일에 output_text 포함 ✅
- [x] CSV 파일 경로 metadata에 포함 ✅
- [ ] API에 동적 전문 로딩 기능 추가 (필요시)

```python
# 추가 구현 예시
@router.get("/{document_id}/full-text")
async def get_full_text(document_id: str):
    # CSV 파일 읽기 로직
    pass
```

---

## 📊 요약 표

| 항목 | 값 |
|------|-----|
| **현재 저장 방식** | CSV 경로만 저장 |
| **Output 텍스트** | 판결 요지 포함 (100%) |
| **전문 접근** | CSV 파일 참조 (77.1%) |
| **추천 방식** | Option 1 (현재 유지) |
| **추가 작업** | 불필요 |

---

**작성일:** 2025-11-03
**문서 버전:** 1.0
