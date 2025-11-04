# 주기적 크롤링 데이터 업데이트 워크플로우

## 📋 개요

법제처 OpenAPI에서 주기적으로 새로운 판례를 크롤링하여 전체 DB에 추가하는 자동화 시스템

---

## 🔄 전체 워크플로우

```
1. 주기적 크롤링 (매일/매주)
   ↓
2. 신규 데이터 식별
   ↓
3. 데이터 검증 및 중복 제거
   ↓
4. 통합 JSON 파일 업데이트
   ↓
5. 임베딩 생성 (신규 데이터만)
   ↓
6. Vector DB 업데이트
   ↓
7. PostgreSQL DB 동기화
   ↓
8. 알림 및 로그
```

---

## 🏗️ 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    스케줄러 (Cron/Celery)                     │
│                  매일 오전 2시 자동 실행                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              1. 크롤링 스크립트 실행                          │
│  scripts/crawl_legal_cases.py                                │
│  → 법제처 API 호출                                           │
│  → 교통 관련 키워드로 검색                                     │
│  → 신규 판례 수집                                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              2. 신규 데이터 식별                              │
│  scripts/identify_new_cases.py                               │
│  → 기존 DB와 비교                                            │
│  → 판례일련번호로 중복 체크                                    │
│  → 신규 케이스만 추출                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              3. 데이터 병합 및 검증                           │
│  scripts/merge_new_data.py                                   │
│  → 데이터 형식 검증                                          │
│  → 통합 JSON에 추가                                          │
│  → 백업 생성                                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              4. 임베딩 생성 (신규만)                          │
│  scripts/create_embeddings_incremental.py                    │
│  → OpenAI API로 임베딩 생성                                   │
│  → 신규 데이터만 처리                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              5. Vector DB 업데이트                            │
│  Qdrant/Pinecone                                             │
│  → 신규 벡터 추가                                            │
│  → 인덱스 자동 갱신                                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              6. PostgreSQL 동기화                             │
│  → documents 테이블 추가                                      │
│  → document_ai_labels 추가                                   │
│  → 통계 업데이트                                              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              7. 알림 및 로그                                  │
│  → Slack/Email 알림                                          │
│  → 업데이트 로그 기록                                         │
│  → 모니터링 대시보드 갱신                                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 파일 구조

```
ai-camp-1st-llm-agent-service-project-2/
├── data/
│   ├── unified_traffic_data_latest.json        # 최신 통합 데이터
│   ├── unified_traffic_data_20251103.json      # 백업 (날짜별)
│   └── crawled_raw/                            # 크롤링 원본
│       ├── traffic_legal_data_20251103.json
│       └── traffic_legal_data_20251104.json
│
├── scripts/
│   ├── crawl_legal_cases.py                    # 크롤링
│   ├── identify_new_cases.py                   # 신규 식별 ✅ 새로 작성
│   ├── merge_new_data.py                       # 데이터 병합 ✅ 새로 작성
│   ├── create_embeddings_incremental.py        # 증분 임베딩 ✅ 새로 작성
│   ├── update_vector_db.py                     # Vector DB 업데이트 ✅ 새로 작성
│   └── schedule_daily_update.py                # 스케줄러 ✅ 새로 작성
│
└── logs/
    └── update_20251103.log                     # 업데이트 로그
```

---

## 🔧 구현 스크립트

### 1. 신규 케이스 식별

```python
# scripts/identify_new_cases.py

import json
from pathlib import Path
from typing import Set, List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_existing_case_ids(unified_file: str) -> Set[str]:
    """
    기존 통합 데이터에서 판례일련번호 추출

    Returns:
        기존 케이스 ID 집합
    """
    with open(unified_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    existing_ids = set()

    for case_type in ['판례', '결정례', '해석례', '법령']:
        for case in data.get(case_type, []):
            case_id = case.get('판례일련번호')
            if case_id:
                existing_ids.add(str(case_id))

    return existing_ids


def identify_new_cases(
    crawled_file: str,
    unified_file: str
) -> Dict[str, List[Dict]]:
    """
    크롤링 데이터에서 신규 케이스만 추출

    Args:
        crawled_file: 크롤링 데이터 파일
        unified_file: 기존 통합 데이터 파일

    Returns:
        신규 케이스 딕셔너리 {판례: [...], 결정례: [...]}
    """
    logger.info("="*60)
    logger.info("신규 케이스 식별")
    logger.info("="*60)

    # 기존 케이스 ID 로드
    existing_ids = load_existing_case_ids(unified_file)
    logger.info(f"기존 케이스: {len(existing_ids):,}건")

    # 크롤링 데이터 로드
    with open(crawled_file, 'r', encoding='utf-8') as f:
        crawled_data = json.load(f)

    new_cases = {
        '판례': [],
        '결정례': [],
        '해석례': [],
        '법령': []
    }

    total_crawled = 0
    total_new = 0

    for case_type in ['판례', '결정례', '해석례', '법령']:
        cases = crawled_data.get(case_type, [])
        total_crawled += len(cases)

        for case in cases:
            case_id = str(case.get('판례일련번호', ''))

            # 신규 케이스만 추가
            if case_id and case_id not in existing_ids:
                new_cases[case_type].append(case)
                total_new += 1

        if new_cases[case_type]:
            logger.info(f"{case_type}: {len(new_cases[case_type])}건 신규")

    logger.info(f"\n총 크롤링: {total_crawled}건")
    logger.info(f"신규 케이스: {total_new}건")
    logger.info(f"중복 제외: {total_crawled - total_new}건")

    return new_cases


def main():
    import sys
    from datetime import datetime

    if len(sys.argv) < 3:
        print("사용법: python identify_new_cases.py <crawled_file> <unified_file>")
        sys.exit(1)

    crawled_file = sys.argv[1]
    unified_file = sys.argv[2]

    # 신규 케이스 식별
    new_cases = identify_new_cases(crawled_file, unified_file)

    # 결과 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"data/new_cases_{timestamp}.json"

    output_data = {
        "수집정보": {
            "식별시각": datetime.now().isoformat(),
            "원본파일": crawled_file,
            "기준파일": unified_file,
            "신규건수": sum(len(cases) for cases in new_cases.values())
        },
        **new_cases
    }

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    logger.info(f"\n신규 케이스 저장: {output_file}")


if __name__ == "__main__":
    main()
```

---

### 2. 데이터 병합

```python
# scripts/merge_new_data.py

import json
import shutil
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def backup_unified_file(unified_file: str) -> str:
    """
    통합 파일 백업

    Returns:
        백업 파일 경로
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = unified_file.replace('.json', f'_backup_{timestamp}.json')

    shutil.copy2(unified_file, backup_file)
    logger.info(f"백업 생성: {backup_file}")

    return backup_file


def merge_new_data(
    new_cases_file: str,
    unified_file: str,
    output_file: str = None
):
    """
    신규 데이터를 통합 파일에 병합

    Args:
        new_cases_file: 신규 케이스 파일
        unified_file: 기존 통합 파일
        output_file: 출력 파일 (None이면 unified_file 덮어쓰기)
    """
    logger.info("="*60)
    logger.info("데이터 병합")
    logger.info("="*60)

    # 백업 생성
    backup_file = backup_unified_file(unified_file)

    # 기존 데이터 로드
    with open(unified_file, 'r', encoding='utf-8') as f:
        unified_data = json.load(f)

    # 신규 데이터 로드
    with open(new_cases_file, 'r', encoding='utf-8') as f:
        new_data = json.load(f)

    # 병합
    stats = {}
    for case_type in ['판례', '결정례', '해석례', '법령']:
        before = len(unified_data.get(case_type, []))
        new_cases = new_data.get(case_type, [])

        if case_type not in unified_data:
            unified_data[case_type] = []

        unified_data[case_type].extend(new_cases)
        after = len(unified_data[case_type])

        stats[case_type] = {
            '이전': before,
            '추가': len(new_cases),
            '이후': after
        }

        logger.info(f"{case_type}: {before} → {after} (+{len(new_cases)})")

    # 수집정보 업데이트
    unified_data['수집정보']['최종갱신'] = datetime.now().isoformat()
    unified_data['수집정보']['판례수'] = len(unified_data.get('판례', []))
    unified_data['수집정보']['결정례수'] = len(unified_data.get('결정례', []))
    unified_data['수집정보']['해석례수'] = len(unified_data.get('해석례', []))
    unified_data['수집정보']['법령수'] = len(unified_data.get('법령', []))
    unified_data['수집정보']['총건수'] = sum([
        unified_data['수집정보']['판례수'],
        unified_data['수집정보']['결정례수'],
        unified_data['수집정보']['해석례수'],
        unified_data['수집정보']['법령수']
    ])

    # 저장
    if output_file is None:
        output_file = unified_file

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(unified_data, f, ensure_ascii=False, indent=2)

    logger.info(f"\n병합 완료: {output_file}")
    logger.info(f"총 건수: {unified_data['수집정보']['총건수']:,}건")

    return output_file, stats


def main():
    import sys

    if len(sys.argv) < 3:
        print("사용법: python merge_new_data.py <new_cases_file> <unified_file>")
        sys.exit(1)

    new_cases_file = sys.argv[1]
    unified_file = sys.argv[2]

    merge_new_data(new_cases_file, unified_file)


if __name__ == "__main__":
    main()
```

---

### 3. 증분 임베딩 생성

```python
# scripts/create_embeddings_incremental.py

import json
from openai import OpenAI
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import logging
from typing import List, Dict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IncrementalEmbeddingService:
    def __init__(self):
        self.openai_client = OpenAI()
        self.qdrant_client = QdrantClient(host="localhost", port=6333)

    def get_existing_ids(self, collection_name: str) -> set:
        """Vector DB에서 기존 ID 조회"""
        # Qdrant에서 모든 포인트 ID 가져오기
        result = self.qdrant_client.scroll(
            collection_name=collection_name,
            limit=100000,
            with_payload=False,
            with_vectors=False
        )

        existing_ids = {str(point.id) for point in result[0]}
        return existing_ids

    def create_embedding(self, text: str) -> List[float]:
        """텍스트 임베딩 생성"""
        response = self.openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding

    def process_new_cases(
        self,
        new_cases_file: str,
        collection_name: str = "precedents"
    ):
        """
        신규 케이스만 임베딩 생성 및 저장

        Args:
            new_cases_file: 신규 케이스 JSON 파일
            collection_name: Vector DB 컬렉션 이름
        """
        logger.info("="*60)
        logger.info("증분 임베딩 생성")
        logger.info("="*60)

        # 신규 케이스 로드
        with open(new_cases_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 기존 ID 조회
        existing_ids = self.get_existing_ids(collection_name)
        logger.info(f"기존 벡터: {len(existing_ids):,}개")

        # 최대 ID 찾기 (신규 ID 생성용)
        max_id = max(map(int, existing_ids)) if existing_ids else 0

        # 신규 케이스 처리
        points = []
        new_count = 0

        for case_type in ['판례', '결정례', '해석례', '법령']:
            cases = data.get(case_type, [])

            for case in cases:
                case_id = str(case.get('판례일련번호', ''))

                # 이미 존재하면 스킵
                if case_id in existing_ids:
                    continue

                # 임베딩할 텍스트 구성
                text_to_embed = f"""
                사건번호: {case['사건번호']}
                법원: {case['법원명']}
                판결요지: {case['상세정보'].get('판결요지', '')}
                전문: {case['상세정보'].get('전문', '')[:2000]}
                """

                # 임베딩 생성
                embedding = self.create_embedding(text_to_embed)

                # Point 생성
                max_id += 1
                point = PointStruct(
                    id=max_id,
                    vector=embedding,
                    payload={
                        "판례일련번호": case_id,
                        "사건번호": case['사건번호'],
                        "법원명": case['법원명'],
                        "선고일자": case['선고일자'],
                        "검색어": case['검색어'],
                        "판결요지": case['상세정보'].get('판결요지', ''),
                        "전문": case['상세정보'].get('전문', ''),
                        "데이터타입": case['데이터타입']
                    }
                )
                points.append(point)
                new_count += 1

                # 배치 저장 (100개씩)
                if len(points) >= 100:
                    self.qdrant_client.upsert(
                        collection_name=collection_name,
                        points=points
                    )
                    logger.info(f"진행: {new_count}개 추가")
                    points = []

        # 남은 포인트 저장
        if points:
            self.qdrant_client.upsert(
                collection_name=collection_name,
                points=points
            )

        logger.info(f"\n총 {new_count}개 벡터 추가 완료")
        logger.info(f"전체 벡터: {len(existing_ids) + new_count:,}개")


def main():
    import sys

    if len(sys.argv) < 2:
        print("사용법: python create_embeddings_incremental.py <new_cases_file>")
        sys.exit(1)

    new_cases_file = sys.argv[1]

    service = IncrementalEmbeddingService()
    service.process_new_cases(new_cases_file)


if __name__ == "__main__":
    main()
```

---

### 4. 스케줄러 (자동화)

```python
# scripts/schedule_daily_update.py

from datetime import datetime
import subprocess
import logging
import json
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/update_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DailyUpdatePipeline:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_dir = Path(__file__).parent.parent

    def run_command(self, command: list, description: str):
        """명령어 실행"""
        logger.info(f"[{description}] 시작")

        try:
            result = subprocess.run(
                command,
                cwd=self.base_dir,
                capture_output=True,
                text=True,
                check=True
            )

            logger.info(f"[{description}] 완료")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"[{description}] 실패: {e.stderr}")
            return False

    def execute_pipeline(self):
        """전체 파이프라인 실행"""
        logger.info("="*60)
        logger.info("주기적 업데이트 파이프라인 시작")
        logger.info(f"시각: {datetime.now().isoformat()}")
        logger.info("="*60)

        # 파일 경로 설정
        crawled_file = f"data/crawled_raw/traffic_legal_data_{self.timestamp}.json"
        unified_file = "data/unified_traffic_data_latest.json"
        new_cases_file = f"data/new_cases_{self.timestamp}.json"

        # 1. 크롤링
        if not self.run_command(
            ["python3", "scripts/crawl_legal_cases.py"],
            "크롤링"
        ):
            logger.error("크롤링 실패. 파이프라인 중단")
            return False

        # 크롤링 파일 이동
        subprocess.run([
            "mv",
            "traffic_legal_data_*.json",
            crawled_file
        ], check=False)

        # 2. 신규 케이스 식별
        if not self.run_command(
            ["python3", "scripts/identify_new_cases.py", crawled_file, unified_file],
            "신규 케이스 식별"
        ):
            logger.error("신규 케이스 식별 실패. 파이프라인 중단")
            return False

        # 신규 케이스가 있는지 확인
        with open(new_cases_file, 'r', encoding='utf-8') as f:
            new_data = json.load(f)

        new_count = new_data['수집정보']['신규건수']

        if new_count == 0:
            logger.info("신규 케이스 없음. 업데이트 불필요")
            return True

        logger.info(f"신규 케이스: {new_count}건")

        # 3. 데이터 병합
        if not self.run_command(
            ["python3", "scripts/merge_new_data.py", new_cases_file, unified_file],
            "데이터 병합"
        ):
            logger.error("데이터 병합 실패")
            return False

        # 4. 임베딩 생성 (신규만)
        if not self.run_command(
            ["python3", "scripts/create_embeddings_incremental.py", new_cases_file],
            "임베딩 생성"
        ):
            logger.error("임베딩 생성 실패")
            return False

        # 5. PostgreSQL 동기화 (TODO: 구현 필요)
        logger.info("[PostgreSQL 동기화] TODO")

        logger.info("="*60)
        logger.info("업데이트 완료")
        logger.info(f"신규 추가: {new_count}건")
        logger.info("="*60)

        return True


def main():
    pipeline = DailyUpdatePipeline()
    success = pipeline.execute_pipeline()

    if success:
        logger.info("✅ 파이프라인 성공")
    else:
        logger.error("❌ 파이프라인 실패")


if __name__ == "__main__":
    main()
```

---

### 5. Crontab 설정

```bash
# crontab -e

# 매일 오전 2시에 실행
0 2 * * * cd /path/to/project && python3 scripts/schedule_daily_update.py

# 또는 Celery Beat 사용
# celery -A app.celery_app beat --loglevel=info
```

---

## 📊 데이터 흐름 예시

### Day 1 (초기)
```
통합 DB: 11,769건
Vector DB: 11,769개 벡터
```

### Day 2 (크롤링 후)
```
크롤링: 50건 (판례 45 + 해석례 5)
신규 식별: 12건 (38건 중복 제외)
    ↓
통합 DB: 11,781건 (+12)
Vector DB: 11,781개 벡터 (+12)
```

### Week 1 (7일 후)
```
누적 신규: 84건
통합 DB: 11,853건
Vector DB: 11,853개 벡터
```

---

## 🔍 중복 제거 로직

```python
# 판례일련번호로 중복 체크
existing_ids = {
    "78434",
    "79038",
    "173284",
    ...
}

# 크롤링 데이터
crawled_case = {
    "판례일련번호": "79038"  # 이미 존재
}

if crawled_case['판례일련번호'] in existing_ids:
    # 스킵
    pass
else:
    # 신규로 추가
    new_cases.append(crawled_case)
```

---

## 📋 모니터링 및 알림

### 로그 예시

```
logs/update_20251103.log:

2025-11-03 02:00:00 - INFO - 주기적 업데이트 파이프라인 시작
2025-11-03 02:00:01 - INFO - [크롤링] 시작
2025-11-03 02:05:30 - INFO - [크롤링] 완료
2025-11-03 02:05:31 - INFO - [신규 케이스 식별] 시작
2025-11-03 02:05:35 - INFO - 기존 케이스: 11,769건
2025-11-03 02:05:35 - INFO - 신규 케이스: 12건
2025-11-03 02:05:35 - INFO - [신규 케이스 식별] 완료
2025-11-03 02:05:36 - INFO - [데이터 병합] 시작
2025-11-03 02:05:40 - INFO - 판례: 9198 → 9210 (+12)
2025-11-03 02:05:40 - INFO - [데이터 병합] 완료
2025-11-03 02:05:41 - INFO - [임베딩 생성] 시작
2025-11-03 02:06:10 - INFO - 총 12개 벡터 추가 완료
2025-11-03 02:06:10 - INFO - [임베딩 생성] 완료
2025-11-03 02:06:10 - INFO - ✅ 파이프라인 성공
```

### Slack 알림 (선택)

```python
# scripts/schedule_daily_update.py에 추가

import requests

def send_slack_notification(message: str):
    webhook_url = "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"

    payload = {
        "text": message,
        "username": "판례 업데이트 봇",
        "icon_emoji": ":robot_face:"
    }

    requests.post(webhook_url, json=payload)

# 파이프라인 완료 후
send_slack_notification(f"""
✅ 판례 DB 업데이트 완료

• 신규 추가: {new_count}건
• 전체 건수: {total_count:,}건
• 업데이트 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
```

---

## 🎯 요약

### 자동화 워크플로우

```
1. Cron (매일 오전 2시)
   ↓
2. 크롤링 (5분)
   ↓
3. 신규 식별 (10초)
   ↓
4. 병합 (10초)
   ↓
5. 임베딩 (신규 × 2초)
   ↓
6. Vector DB 업데이트 (즉시)
   ↓
7. 알림 발송
```

**총 소요 시간:** 약 5~10분 (신규 데이터 양에 따라)

---

## 📝 체크리스트

- [ ] 스크립트 작성
  - [ ] `identify_new_cases.py`
  - [ ] `merge_new_data.py`
  - [ ] `create_embeddings_incremental.py`
  - [ ] `schedule_daily_update.py`

- [ ] 인프라 설정
  - [ ] Qdrant 설치 및 실행
  - [ ] Cron 설정

- [ ] 테스트
  - [ ] 수동 실행 테스트
  - [ ] 중복 제거 검증
  - [ ] 롤백 테스트

- [ ] 모니터링
  - [ ] 로그 확인
  - [ ] 알림 설정
  - [ ] 대시보드 구성

---

**작성일:** 2025-11-03
**시스템:** 주기적 크롤링 → 증분 업데이트 자동화
