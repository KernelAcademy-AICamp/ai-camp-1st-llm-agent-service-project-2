"""
PostgreSQL schema definitions for legal document database.
교통법 및 형사법 데이터 구조화 저장을 위한 스키마
"""

# SQL 스키마 정의
SCHEMA_SQL = """
-- ==========================================
-- 법령 테이블
-- ==========================================
CREATE TABLE IF NOT EXISTS laws (
    law_id VARCHAR(20) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    law_class VARCHAR(10),
    ministry VARCHAR(100),
    promulg_date DATE,
    effect_date DATE,
    promulg_num VARCHAR(50),
    full_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_law_title ON laws(title);
CREATE INDEX IF NOT EXISTS idx_law_class ON laws(law_class);

-- 법령 조문 테이블 (계층 구조)
CREATE TABLE IF NOT EXISTS law_articles (
    article_id SERIAL PRIMARY KEY,
    law_id VARCHAR(20) REFERENCES laws(law_id) ON DELETE CASCADE,
    mst VARCHAR(20),
    article_type VARCHAR(20),        -- 조문/항/호/목
    article_num VARCHAR(50),         -- 제N조
    sentence_num INT,
    content TEXT NOT NULL,
    parent_article_id INT REFERENCES law_articles(article_id),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_law_article ON law_articles(law_id, article_num);
CREATE INDEX IF NOT EXISTS idx_parent ON law_articles(parent_article_id);

-- ==========================================
-- 판결문 테이블
-- ==========================================
CREATE TABLE IF NOT EXISTS precedents (
    precedent_id VARCHAR(20) PRIMARY KEY,
    case_name VARCHAR(500),
    case_num VARCHAR(100),
    sentence_date DATE,
    court_name VARCHAR(100),
    court_code VARCHAR(20),
    case_type VARCHAR(50),           -- 형사/민사
    full_text TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_case_name ON precedents(case_name);
CREATE INDEX IF NOT EXISTS idx_court_date ON precedents(court_name, sentence_date);

-- 판결문 섹션 테이블
CREATE TABLE IF NOT EXISTS precedent_sections (
    section_id SERIAL PRIMARY KEY,
    precedent_id VARCHAR(20) REFERENCES precedents(precedent_id) ON DELETE CASCADE,
    section_type VARCHAR(50),        -- 판시사항/판결요지/주문/이유
    sentence_num INT,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_precedent_section ON precedent_sections(precedent_id, section_type);

-- ==========================================
-- QA 및 요약 테이블
-- ==========================================
CREATE TABLE IF NOT EXISTS legal_qa (
    qa_id SERIAL PRIMARY KEY,
    doc_type VARCHAR(20),            -- 법령/판결문/결정례/해석례
    doc_id VARCHAR(20),              -- law_id or precedent_id
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    instruction TEXT,
    sentence_type VARCHAR(20),       -- 서술형/나열형
    origin_word_cnt INT,
    label_word_cnt INT,
    related_article VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_qa_doc ON legal_qa(doc_type, doc_id);

-- Full-text search index for questions
CREATE INDEX IF NOT EXISTS idx_qa_question ON legal_qa USING gin(to_tsvector('korean', question));

CREATE TABLE IF NOT EXISTS legal_summaries (
    summary_id SERIAL PRIMARY KEY,
    doc_type VARCHAR(20),
    doc_id VARCHAR(20),
    summary TEXT NOT NULL,
    instruction TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_summary_doc ON legal_summaries(doc_type, doc_id);

-- ==========================================
-- 교통법 특화 테이블
-- ==========================================
CREATE TABLE IF NOT EXISTS traffic_cases (
    case_id SERIAL PRIMARY KEY,
    precedent_id VARCHAR(20) REFERENCES precedents(precedent_id) ON DELETE CASCADE,
    violation_type VARCHAR(100),     -- 음주운전/신호위반/과실치사 등
    blood_alcohol DECIMAL(5,4),      -- 혈중알코올농도
    sentence_type VARCHAR(100),      -- 징역/벌금/집행유예
    sentence_detail TEXT,
    traffic_law_article VARCHAR(100), -- 위반 조문
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_violation ON traffic_cases(violation_type);
CREATE INDEX IF NOT EXISTS idx_traffic_precedent ON traffic_cases(precedent_id);
"""

DROP_SCHEMA_SQL = """
DROP TABLE IF EXISTS traffic_cases CASCADE;
DROP TABLE IF EXISTS legal_summaries CASCADE;
DROP TABLE IF EXISTS legal_qa CASCADE;
DROP TABLE IF EXISTS precedent_sections CASCADE;
DROP TABLE IF EXISTS precedents CASCADE;
DROP TABLE IF EXISTS law_articles CASCADE;
DROP TABLE IF EXISTS laws CASCADE;
"""


def create_all_tables(connection):
    """
    Create all tables in the database.

    Args:
        connection: psycopg2 connection object
    """
    cursor = connection.cursor()
    try:
        cursor.execute(SCHEMA_SQL)
        connection.commit()
        print("✓ All tables created successfully")
    except Exception as e:
        connection.rollback()
        print(f"❌ Error creating tables: {e}")
        raise
    finally:
        cursor.close()


def drop_all_tables(connection):
    """
    Drop all tables in the database.

    Args:
        connection: psycopg2 connection object
    """
    cursor = connection.cursor()
    try:
        cursor.execute(DROP_SCHEMA_SQL)
        connection.commit()
        print("✓ All tables dropped successfully")
    except Exception as e:
        connection.rollback()
        print(f"❌ Error dropping tables: {e}")
        raise
    finally:
        cursor.close()
