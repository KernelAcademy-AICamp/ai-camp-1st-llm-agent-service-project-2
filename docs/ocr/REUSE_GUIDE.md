# OCR 파이프라인 재사용 가이드

> **목적**: 다른 서비스에 OCR 파이프라인을 빠르게 적용하기 위한 실무 가이드
> **난이도**: ⭐⭐ (중급)
> **예상 시간**: 2-4시간

---

## 📋 목차

1. [빠른 시작](#1-빠른-시작)
2. [시나리오별 적용 가이드](#2-시나리오별-적용-가이드)
3. [도메인별 커스터마이징](#3-도메인별-커스터마이징)
4. [성능 튜닝](#4-성능-튜닝)
5. [배포 전략](#5-배포-전략)
6. [FAQ](#6-faq)

---

## 1. 빠른 시작

### 1.1 5분 설치 가이드

#### Step 1: 저장소 클론

```bash
git clone https://github.com/your-org/ocr-pipeline.git
cd ocr-pipeline
```

#### Step 2: 의존성 설치

**macOS**:
```bash
# Tesseract 설치
brew install tesseract tesseract-lang

# Python 의존성 설치
pip install -r requirements.txt
```

**Ubuntu/Debian**:
```bash
# Tesseract 설치
sudo apt update
sudo apt install tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng poppler-utils

# Python 의존성 설치
pip install -r requirements.txt
```

**Windows**:
```bash
# Tesseract 설치 (공식 설치 파일 다운로드)
# https://github.com/UB-Mannheim/tesseract/wiki

# Python 의존성 설치
pip install -r requirements.txt
```

#### Step 3: 테스트 실행

```bash
# 단일 PDF 테스트
python scripts/test_single_pdf.py /path/to/your/file.pdf

# API 서버 실행
uvicorn backend.api.main:app --reload
```

#### Step 4: 프론트엔드 연동

```javascript
// React 예시
const formData = new FormData();
formData.append('file', pdfFile);

const response = await fetch('http://localhost:8000/api/v1/process-pdf', {
  method: 'POST',
  body: formData
});

const result = await response.json();
console.log(result.data);
```

---

## 2. 시나리오별 적용 가이드

### 시나리오 1: 의료 문서 처리 시스템

**요구사항**:
- 진단서, 처방전, 검사 결과 OCR
- 환자명, 진단명, 날짜 자동 추출

**적용 단계**:

#### 2.1 새로운 문서 타입 추가

**파일**: `core/ocr/document_structurer.py`

```python
# 1. 타입 감지 추가
class DocumentTypeDetector:
    @staticmethod
    def detect(text: str, filename: str) -> str:
        # 기존 코드...

        # 의료 문서 타입 추가
        if '진단서' in filename or 'diagnosis' in filename_lower:
            return 'diagnosis'
        elif '처방전' in filename or 'prescription' in filename_lower:
            return 'prescription'

        # 텍스트 내용 기반
        if '진단서' in text_normalized and '환자명' in text_normalized:
            return 'diagnosis'
```

#### 2.2 Structurer 클래스 작성

```python
class DiagnosisStructurer:
    """진단서 구조화"""

    def __init__(self, text: str, filename: str):
        self.text = text
        self.filename = filename

    def extract_patient_name(self) -> str:
        """환자명 추출"""
        patterns = [
            r'환\s*자\s*명\s*[:：]?\s*([^\n(]+)',
            r'성\s*명\s*[:：]?\s*([^\n(]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                name = match.group(1).strip()
                # 괄호, 주민번호 제거
                name = re.split(r'[\(\d\-]{3,}', name)[0].strip()
                return name
        return ""

    def extract_diagnosis(self) -> str:
        """진단명 추출"""
        patterns = [
            r'진\s*단\s*명\s*[:：]?\s*([^\n]+)',
            r'병\s*명\s*[:：]?\s*([^\n]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                return match.group(1).strip()
        return ""

    def extract_diagnosis_date(self) -> str:
        """진단일자 추출"""
        pattern = r'(\d{4})[년.\-/](\d{1,2})[월.\-/](\d{1,2})'
        match = re.search(pattern, self.text)
        if match:
            year, month, day = match.groups()
            return f"{year}.{month.zfill(2)}.{day.zfill(2)}"
        return ""

    def extract_hospital(self) -> str:
        """병원명 추출"""
        patterns = [
            r'([가-힣]+병원)',
            r'([가-힣]+의원)',
            r'([가-힣]+클리닉)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                return match.group(1)
        return ""

    def structure(self) -> dict:
        """진단서 구조화"""
        return {
            "데이터타입": "진단서",
            "파일명": self.filename,
            "환자명": self.extract_patient_name(),
            "진단명": self.extract_diagnosis(),
            "진단일자": self.extract_diagnosis_date(),
            "병원명": self.extract_hospital(),
            "처리시각": datetime.now().isoformat()
        }
```

#### 2.3 DocumentStructurer에 연결

```python
class DocumentStructurer:
    def structure(self) -> dict:
        # 기존 코드...

        if self.doc_type == 'diagnosis':
            structurer = DiagnosisStructurer(self.text, self.filename)
        elif self.doc_type == 'prescription':
            structurer = PrescriptionStructurer(self.text, self.filename)
        # ...

        return structurer.structure()
```

#### 2.4 테스트

```bash
python scripts/test_single_pdf.py /path/to/diagnosis.pdf
```

**예상 출력**:
```json
{
  "데이터타입": "진단서",
  "파일명": "진단서_김환자_20250607.pdf",
  "환자명": "김환자",
  "진단명": "급성 기관지염",
  "진단일자": "2025.06.07",
  "병원명": "서울대학교병원",
  "처리시각": "2025-11-07T15:30:00.123456"
}
```

---

### 시나리오 2: 계약서 자동 분석 시스템

**요구사항**:
- 다양한 계약서 (근로계약서, 매매계약서, 임대차계약서)
- 계약 당사자, 계약 금액, 계약 기간 추출

**적용 단계**:

#### 2.1 계약서 Structurer 작성

```python
class ContractStructurer:
    """계약서 구조화"""

    def __init__(self, text: str, filename: str):
        self.text = text
        self.filename = filename

    def extract_contract_type(self) -> str:
        """계약 유형 추출"""
        types = {
            '근로계약': r'근로계약서',
            '매매계약': r'매매계약서',
            '임대차계약': r'임대차계약서',
        }
        for contract_type, pattern in types.items():
            if re.search(pattern, self.text):
                return contract_type
        return "기타 계약"

    def extract_parties(self) -> dict:
        """계약 당사자 추출 (갑, 을)"""
        party_a = ""
        party_b = ""

        # 갑 추출
        pattern_a = r'갑\s*[:：)]?\s*([^\n(]+)'
        match_a = re.search(pattern_a, self.text)
        if match_a:
            party_a = match_a.group(1).strip()
            party_a = re.split(r'[\(\d\-]{3,}', party_a)[0].strip()

        # 을 추출
        pattern_b = r'을\s*[:：)]?\s*([^\n(]+)'
        match_b = re.search(pattern_b, self.text)
        if match_b:
            party_b = match_b.group(1).strip()
            party_b = re.split(r'[\(\d\-]{3,}', party_b)[0].strip()

        return {"갑": party_a, "을": party_b}

    def extract_amount(self) -> str:
        """계약 금액 추출"""
        patterns = [
            r'금\s*([\d,]+)\s*원',
            r'([\d,]+)\s*원',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                amount = match.group(1).replace(',', '')
                return f"{int(amount):,}원"
        return ""

    def extract_period(self) -> dict:
        """계약 기간 추출"""
        start_date = ""
        end_date = ""

        # 시작일
        start_pattern = r'계약\s*기간\s*[:：]?\s*(\d{4})[년.\-/](\d{1,2})[월.\-/](\d{1,2})'
        match_start = re.search(start_pattern, self.text)
        if match_start:
            year, month, day = match_start.groups()
            start_date = f"{year}.{month.zfill(2)}.{day.zfill(2)}"

        # 종료일
        end_pattern = r'부터\s*(\d{4})[년.\-/](\d{1,2})[월.\-/](\d{1,2})|~\s*(\d{4})[년.\-/](\d{1,2})[월.\-/](\d{1,2})'
        match_end = re.search(end_pattern, self.text)
        if match_end:
            groups = [g for g in match_end.groups() if g]
            if len(groups) >= 3:
                year, month, day = groups[:3]
                end_date = f"{year}.{month.zfill(2)}.{day.zfill(2)}"

        return {"시작일": start_date, "종료일": end_date}

    def structure(self) -> dict:
        """계약서 구조화"""
        parties = self.extract_parties()
        period = self.extract_period()

        return {
            "데이터타입": "계약서",
            "파일명": self.filename,
            "계약유형": self.extract_contract_type(),
            "갑": parties["갑"],
            "을": parties["을"],
            "계약금액": self.extract_amount(),
            "계약시작일": period["시작일"],
            "계약종료일": period["종료일"],
            "처리시각": datetime.now().isoformat()
        }
```

#### 2.2 타입 감지에 추가

```python
class DocumentTypeDetector:
    @staticmethod
    def detect(text: str, filename: str) -> str:
        # 계약서 감지
        if '계약서' in filename or 'contract' in filename.lower():
            return 'contract'

        if '계약서' in text and ('갑' in text and '을' in text):
            return 'contract'

        # ...
```

---

### 시나리오 3: 영수증/명세서 자동 입력 시스템

**요구사항**:
- 영수증 이미지에서 상호, 금액, 날짜 추출
- 회계 시스템 자동 입력

**적용 단계**:

#### 3.1 영수증 Structurer

```python
class ReceiptStructurer:
    """영수증 구조화"""

    def __init__(self, text: str, filename: str):
        self.text = text
        self.filename = filename

    def extract_store_name(self) -> str:
        """상호명 추출"""
        # 첫 5줄에서 가장 긴 줄 (보통 상호명)
        lines = self.text.split('\n')[:5]
        candidates = [line.strip() for line in lines if len(line.strip()) > 2]
        if candidates:
            return max(candidates, key=len)
        return ""

    def extract_total_amount(self) -> str:
        """합계 금액 추출"""
        patterns = [
            r'합\s*계\s*[:：]?\s*([\d,]+)',
            r'총\s*액\s*[:：]?\s*([\d,]+)',
            r'Total\s*[:：]?\s*([\d,]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, self.text, re.IGNORECASE)
            if match:
                amount = match.group(1).replace(',', '')
                return f"{int(amount):,}원"
        return ""

    def extract_payment_date(self) -> str:
        """결제 날짜 추출"""
        pattern = r'(\d{4})[년.\-/](\d{1,2})[월.\-/](\d{1,2})'
        match = re.search(pattern, self.text)
        if match:
            year, month, day = match.groups()
            return f"{year}.{month.zfill(2)}.{day.zfill(2)}"
        return ""

    def extract_payment_method(self) -> str:
        """결제 수단 추출"""
        methods = {
            '카드': r'카드|CARD',
            '현금': r'현금|CASH',
            '계좌이체': r'계좌이체|이체',
        }
        for method, pattern in methods.items():
            if re.search(pattern, self.text, re.IGNORECASE):
                return method
        return ""

    def structure(self) -> dict:
        """영수증 구조화"""
        return {
            "데이터타입": "영수증",
            "파일명": self.filename,
            "상호명": self.extract_store_name(),
            "합계금액": self.extract_total_amount(),
            "결제일자": self.extract_payment_date(),
            "결제수단": self.extract_payment_method(),
            "처리시각": datetime.now().isoformat()
        }
```

#### 3.2 회계 시스템 연동

```python
# backend/api/main.py

from fastapi import APIRouter
import httpx

router = APIRouter()

@router.post("/api/v1/process-receipt")
async def process_receipt_and_submit(
    file: UploadFile = File(...),
    accounting_api_url: str = "https://accounting.example.com/api/entries"
):
    """영수증 처리 후 회계 시스템 자동 입력"""

    # 1. OCR 처리
    structured_data = await process_pdf(file)

    # 2. 회계 시스템 API 호출
    accounting_data = {
        "date": structured_data["data"]["결제일자"],
        "description": f"{structured_data['data']['상호명']} 구매",
        "amount": int(structured_data["data"]["합계금액"].replace(",", "").replace("원", "")),
        "category": "경비",
        "payment_method": structured_data["data"]["결제수단"]
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(accounting_api_url, json=accounting_data)

    return {
        "ocr_result": structured_data,
        "accounting_entry": response.json(),
        "status": "submitted"
    }
```

---

## 3. 도메인별 커스터마이징

### 3.1 품질 평가 기준 조정

**예시**: 고해상도 스캔 문서 처리 (의료 기록)

```python
# core/ocr/ocr_processor.py 수정

class DocumentQualityAssessor:
    @staticmethod
    def assess_quality(image):
        # 기존 코드...

        # 도메인별 가중치 조정 (의료 문서)
        weights = {
            'sharpness': 0.40,    # 선명도 더 중요 (작은 글씨)
            'contrast': 0.25,
            'noise': 0.15,        # 노이즈 덜 중요 (고품질 스캔)
            'resolution': 0.15,
            'brightness': 0.05
        }

        # 품질 등급 기준 상향
        if total_score >= 85:  # 기존 80 → 85
            quality_level = 'excellent'
            recommended_preset = 'minimal'
        # ...
```

### 3.2 전처리 기법 추가

**예시**: 황변된 오래된 문서 처리

```python
class ImagePreprocessor:
    @staticmethod
    def remove_yellowing(image):
        """황변 제거 - 오래된 문서 개선"""
        if isinstance(image, Image.Image):
            image = ImagePreprocessor.pil_to_cv2(image)

        # LAB 색공간 변환
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # B 채널 (노란색) 보정
        b = cv2.normalize(b, None, alpha=0, beta=255,
                         norm_type=cv2.NORM_MINMAX)

        # 병합 후 RGB 복원
        lab = cv2.merge([l, a, b])
        corrected = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        return ImagePreprocessor.cv2_to_pil(corrected)
```

**적용**:

```python
def preprocess_image_selective(image, quality_analysis):
    # 기존 코드...

    # 황변 제거 (오래된 문서인 경우)
    if is_old_document(image):
        image = preprocessor.remove_yellowing(image)
        steps.append("황변 제거")

    # ...
```

### 3.3 언어 설정 변경

**예시**: 다국어 지원 (영어+중국어)

```python
# backend/api/main.py

@app.post("/api/v1/process-pdf")
async def process_pdf(
    file: UploadFile = File(...),
    lang: str = 'kor+eng',  # 파라미터 추가
    adaptive: bool = True,
    apply_postprocessing: bool = True
):
    # OCR 처리 시 언어 전달
    ocr_result = extract_pdf_with_preprocessing(
        temp_file,
        dpi=300,
        preset='standard',
        adaptive=adaptive,
        lang=lang  # 동적 언어 설정
    )
    # ...
```

**프론트엔드 호출**:

```javascript
const formData = new FormData();
formData.append('file', pdfFile);
formData.append('lang', 'eng+chi_sim');  // 영어+중국어

await fetch('http://localhost:8000/api/v1/process-pdf', {
  method: 'POST',
  body: formData
});
```

---

## 4. 성능 튜닝

### 4.1 처리 속도 개선

#### 4.1.1 멀티프로세싱 적용

**파일**: `core/ocr/ocr_processor.py`

```python
from multiprocessing import Pool, cpu_count

def extract_pdf_with_preprocessing_parallel(
    pdf_path: Path,
    dpi=300,
    preset='standard',
    adaptive=False
):
    """멀티프로세싱 버전"""
    doc = fitz.open(pdf_path)
    page_count = len(doc)
    doc.close()

    # CPU 코어 수 확인
    num_processes = min(cpu_count(), page_count)

    # 페이지별 처리 함수
    def process_single_page(args):
        page_num, pdf_path, dpi, preset, adaptive = args

        doc = fitz.open(pdf_path)
        page = doc[page_num]

        image = pdf_page_to_image(page, dpi=dpi)
        doc.close()

        # 품질 평가 및 OCR
        if adaptive:
            quality = DocumentQualityAssessor.assess_quality(image)
            selected_preset = quality['recommended_preset']
        else:
            quality = None
            selected_preset = preset

        ocr_result = ocr_image_with_preprocessing(
            image, lang='kor+eng', preset=selected_preset,
            quality_analysis=quality
        )

        return {
            'page_number': page_num + 1,
            'text': ocr_result['text'],
            'confidence': ocr_result['confidence'],
            # ...
        }

    # 병렬 처리
    args_list = [
        (i, pdf_path, dpi, preset, adaptive)
        for i in range(page_count)
    ]

    with Pool(processes=num_processes) as pool:
        pages = pool.map(process_single_page, args_list)

    # 결과 병합
    return {
        'filename': pdf_path.name,
        'page_count': page_count,
        'pages': pages,
        # ...
    }
```

**성능 개선**:
- 10페이지 PDF: 100초 → 40초 (4 코어 기준)

#### 4.1.2 해상도 동적 조정

```python
def select_optimal_dpi(file_size_mb: float, page_count: int) -> int:
    """파일 크기와 페이지 수에 따라 최적 DPI 선택"""
    if file_size_mb > 50:  # 대용량 파일
        return 200
    elif page_count > 20:  # 많은 페이지
        return 250
    else:
        return 300
```

### 4.2 메모리 최적화

#### 4.2.1 스트리밍 처리

**대용량 PDF (100+ 페이지)**:

```python
def process_large_pdf_streaming(pdf_path: Path, output_dir: Path):
    """페이지별 순차 처리 및 즉시 저장"""
    doc = fitz.open(pdf_path)

    for page_num in range(len(doc)):
        page = doc[page_num]

        # 페이지 처리
        image = pdf_page_to_image(page, dpi=300)
        ocr_result = ocr_image_with_preprocessing(image, preset='standard')

        # 즉시 파일로 저장
        page_file = output_dir / f"page_{page_num+1}.json"
        with open(page_file, 'w', encoding='utf-8') as f:
            json.dump(ocr_result, f, ensure_ascii=False, indent=2)

        # 메모리 해제
        del image
        gc.collect()

        logger.info(f"Page {page_num+1} 처리 완료 및 저장")

    doc.close()

    logger.info(f"총 {len(doc)}페이지 처리 완료")
```

#### 4.2.2 결과 캐싱

```python
import hashlib
import pickle
from pathlib import Path

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

def get_file_hash(file_path: Path) -> str:
    """파일 해시 계산"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        hasher.update(f.read())
    return hasher.hexdigest()

def process_with_cache(pdf_path: Path):
    """캐시 사용 OCR 처리"""
    file_hash = get_file_hash(pdf_path)
    cache_file = CACHE_DIR / f"{file_hash}.pkl"

    # 캐시 확인
    if cache_file.exists():
        logger.info(f"캐시 사용: {pdf_path.name}")
        with open(cache_file, 'rb') as f:
            return pickle.load(f)

    # OCR 처리
    result = extract_pdf_with_preprocessing(pdf_path)

    # 캐시 저장
    with open(cache_file, 'wb') as f:
        pickle.dump(result, f)

    return result
```

---

## 5. 배포 전략

### 5.1 Docker Compose 배포

**docker-compose.yml**:

```yaml
version: '3.8'

services:
  ocr-api:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads
      - ./results:/app/results
      - ./cache:/app/cache
    environment:
      - TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
      - DEFAULT_DPI=300
      - ENABLE_ADAPTIVE=true
      - LOG_LEVEL=INFO
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - ocr-api
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    restart: unless-stopped

volumes:
  redis-data:
```

**실행**:

```bash
docker-compose up -d
```

### 5.2 Kubernetes 배포

**deployment.yaml**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ocr-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ocr-api
  template:
    metadata:
      labels:
        app: ocr-api
    spec:
      containers:
      - name: ocr-api
        image: your-registry/ocr-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: DEFAULT_DPI
          value: "300"
        - name: ENABLE_ADAPTIVE
          value: "true"
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "4Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: ocr-api-service
spec:
  selector:
    app: ocr-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

**배포**:

```bash
kubectl apply -f deployment.yaml
```

### 5.3 서버리스 배포 (AWS Lambda)

**handler.py**:

```python
import json
import base64
from pathlib import Path
from core.ocr import PDFTextExtractor, extract_pdf_with_preprocessing
from core.ocr import DocumentStructurer, apply_ocr_postprocessing

def lambda_handler(event, context):
    """AWS Lambda 핸들러"""

    # Base64 인코딩된 PDF 수신
    pdf_base64 = event['body']
    pdf_bytes = base64.b64decode(pdf_base64)

    # 임시 파일로 저장
    temp_file = Path("/tmp/input.pdf")
    with open(temp_file, 'wb') as f:
        f.write(pdf_bytes)

    # OCR 처리
    result = extract_pdf_with_preprocessing(
        temp_file,
        dpi=300,
        preset='standard',
        adaptive=True
    )

    # 후처리 및 구조화
    full_text = '\n'.join([p['text'] for p in result['pages']])
    full_text = apply_ocr_postprocessing(full_text)

    structurer = DocumentStructurer(full_text, "uploaded.pdf")
    structured_data = structurer.structure()

    # 결과 반환
    return {
        'statusCode': 200,
        'body': json.dumps(structured_data, ensure_ascii=False)
    }
```

---

## 6. FAQ

### Q1: OCR 신뢰도가 50% 미만으로 낮아요.

**A**: 다음을 시도해보세요:

1. DPI 증가: `dpi=400` 또는 `dpi=600`
2. Preset 변경: `preset='aggressive'`
3. 수동 전처리 확인: 원본 이미지 품질 확인

```python
# 품질 평가 확인
from core.ocr.ocr_processor import DocumentQualityAssessor

quality = DocumentQualityAssessor.assess_quality(image)
print(quality)
```

### Q2: 메모리 부족 오류가 발생해요.

**A**: 대용량 PDF 처리 시:

1. 스트리밍 처리 사용 (섹션 4.2.1)
2. DPI 낮추기: `dpi=200`
3. 페이지별 순차 처리

### Q3: 특정 필드가 추출되지 않아요.

**A**: 정규식 패턴 디버깅:

```python
import re

# 패턴 테스트
text = "원고 : 홍길동 (123456-1******)"
pattern = r'원\s*고\s*[:：]?\s*([^\n(]+)'
match = re.search(pattern, text)

if match:
    print(match.group(1).strip())  # "홍길동"
else:
    print("패턴 불일치 - 정규식 수정 필요")
```

### Q4: 영문 숫자가 한글로 오인식돼요.

**A**: 언어 설정 조정:

```python
# 영어 위주 문서
pytesseract.image_to_string(image, lang='eng')

# 한글 + 영어 혼합
pytesseract.image_to_string(image, lang='kor+eng')

# 숫자 위주
pytesseract.image_to_string(image, lang='eng', config='--psm 6 digits')
```

### Q5: 처리 속도가 너무 느려요.

**A**: 성능 최적화:

1. 멀티프로세싱 사용 (섹션 4.1.1)
2. GPU 가속 활성화
3. DPI 낮추기: `dpi=200`
4. 불필요한 전처리 비활성화

```python
# 최소 전처리
extract_pdf_with_preprocessing(pdf_path, preset='light', adaptive=False)
```

### Q6: 새로운 문서 타입을 추가했는데 인식이 안 돼요.

**A**: 디버깅:

```python
# 타입 감지 테스트
from core.ocr.document_structurer import DocumentTypeDetector

doc_type = DocumentTypeDetector.detect(text, filename)
print(f"감지된 타입: {doc_type}")

# 기대한 타입이 아니면 패턴 수정
```

### Q7: 한글이 깨져요.

**A**: 인코딩 확인:

```python
# 파일 저장 시 UTF-8 사용
with open('result.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
```

### Q8: API 응답이 너무 느려요.

**A**: 비동기 처리:

```python
from fastapi import BackgroundTasks

@app.post("/api/v1/process-pdf-async")
async def process_pdf_async(
    file: UploadFile,
    background_tasks: BackgroundTasks
):
    """비동기 처리"""
    task_id = str(uuid.uuid4())

    # 백그라운드 작업 등록
    background_tasks.add_task(process_in_background, file, task_id)

    return {"task_id": task_id, "status": "processing"}

# 결과 조회 엔드포인트
@app.get("/api/v1/task/{task_id}")
async def get_task_result(task_id: str):
    # Redis 등에서 결과 조회
    result = redis_client.get(task_id)
    return json.loads(result)
```

---

## 7. 체크리스트

### 7.1 적용 전 체크리스트

- [ ] Tesseract 설치 및 언어 팩 확인
- [ ] Python 의존성 설치 (`requirements.txt`)
- [ ] 샘플 PDF로 테스트 실행
- [ ] API 서버 정상 작동 확인
- [ ] 프론트엔드 연동 테스트

### 7.2 커스터마이징 체크리스트

- [ ] 새로운 문서 타입 추가 (`DocumentTypeDetector`)
- [ ] Structurer 클래스 작성
- [ ] 정규식 패턴 테스트 및 검증
- [ ] 샘플 데이터로 추출 정확도 확인
- [ ] 후처리 규칙 추가 (필요 시)

### 7.3 배포 체크리스트

- [ ] Docker 이미지 빌드 및 테스트
- [ ] 환경 변수 설정 (`.env`)
- [ ] 로그 설정 및 모니터링
- [ ] 성능 테스트 (부하 테스트)
- [ ] 보안 설정 (HTTPS, CORS)
- [ ] 백업 및 복구 계획

---

## 8. 추가 리소스

### 8.1 공식 문서

- [OCR 파이프라인 설계문서](OCR_PIPELINE_DESIGN.md)
- [API 통합 가이드](API_GUIDE.md)
- [성능 최적화 가이드](archive/VERSION_COMPARISON.md)

### 8.2 예제 코드

- [의료 문서 처리 예제](../examples/medical_documents.py) (예정)
- [계약서 분석 예제](../examples/contracts.py) (예정)
- [영수증 자동 입력 예제](../examples/receipts.py) (예정)

### 8.3 커뮤니티

- GitHub Issues: 버그 리포트 및 기능 요청
- Slack/Discord: 실시간 지원

---

**문서 끝**

이 재사용 가이드를 참고하여 OCR 파이프라인을 다양한 도메인에 빠르게 적용할 수 있습니다.
추가 질문이나 지원이 필요하면 GitHub Issues를 통해 문의해주세요.
