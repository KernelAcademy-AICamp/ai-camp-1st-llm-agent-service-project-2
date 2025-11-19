# Data Pipeline

데이터 수집, 전처리, 임베딩, 인덱싱 배치 작업

## 구조

```
data-pipeline/
├── main.py              # CLI 엔트리포인트
├── loaders/             # 데이터 로더 (기존 scripts/)
│   ├── criminal_law_data_loader.py
│   ├── traffic_law_data_loader.py
│   └── setup_postgres.py
├── processors/          # 임베딩/청킹 처리 (기존 embed/)
│   ├── embed_to_qdrant.py
│   └── embed_to_qdrant_with_chunking.py
└── uploaders/           # DB 업로더 (향후 추가)
```

## 사용법

### 1. 데이터 로드

```bash
# 형사법 데이터 로드
python main.py load --source criminal --output-dir /path/to/output

# 교통법 데이터 로드
python main.py load --source traffic --output-dir /path/to/output

# 전체 데이터 로드
python main.py load --source all
```

### 2. 벡터 인덱싱

```bash
# Qdrant에 인덱싱
python main.py index --input-dir /path/to/data --vector-db qdrant --batch-size 64

# pgvector에 인덱싱
python main.py index --vector-db pgvector
```

### 3. 데이터베이스 스키마 설정

```bash
python main.py setup --db-url postgresql://user:pass@localhost:5432/legal_db
```

## 의존성

- libs/rag-core (청킹, 임베딩)
- libs/domain-model (데이터 모델)

## 배포

Docker 컨테이너로 배치 작업 실행:

```bash
docker build -t legal-rag-data-pipeline .
docker run legal-rag-data-pipeline load --source all
```
