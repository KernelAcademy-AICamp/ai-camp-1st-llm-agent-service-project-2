"""
PostgreSQL client for legal document database operations.
법률 문서 데이터베이스 CRUD 작업을 위한 클라이언트
"""

import psycopg2
from psycopg2.extras import execute_batch, RealDictCursor
from typing import List, Dict, Any, Optional
from datetime import datetime


class PostgreSQLClient:
    """PostgreSQL database client for legal documents."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize PostgreSQL client.

        Args:
            config: Database configuration
                {
                    'host': 'localhost',
                    'port': 5432,
                    'database': 'criminal_law_db',
                    'user': 'postgres',
                    'password': 'password'
                }
        """
        self.config = config
        self.connection = None
        self.connect()

    def connect(self):
        """Establish database connection."""
        try:
            self.connection = psycopg2.connect(
                host=self.config.get('host', 'localhost'),
                port=self.config.get('port', 5432),
                database=self.config.get('database', 'criminal_law_db'),
                user=self.config.get('user', 'postgres'),
                password=self.config.get('password', '')
            )
            print("✓ Connected to PostgreSQL database")
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {e}")
            raise

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            print("✓ Database connection closed")

    # ==========================================
    # 법령 (Laws) 관련 메서드
    # ==========================================

    def insert_law(self, law_data: Dict[str, Any]) -> bool:
        """
        Insert a law document.

        Args:
            law_data: {
                'law_id': '000239',
                'title': '건설기계관리법',
                'law_class': '02',
                'ministry': '국토교통부',
                'promulg_date': '2023-04-18',
                'effect_date': '2023-10-19',
                'promulg_num': '19365',
                'full_text': '...'
            }

        Returns:
            bool: Success or failure
        """
        cursor = self.connection.cursor()
        try:
            sql = """
                INSERT INTO laws (law_id, title, law_class, ministry, promulg_date,
                                effect_date, promulg_num, full_text)
                VALUES (%(law_id)s, %(title)s, %(law_class)s, %(ministry)s,
                       %(promulg_date)s, %(effect_date)s, %(promulg_num)s, %(full_text)s)
                ON CONFLICT (law_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    law_class = EXCLUDED.law_class,
                    ministry = EXCLUDED.ministry,
                    promulg_date = EXCLUDED.promulg_date,
                    effect_date = EXCLUDED.effect_date,
                    promulg_num = EXCLUDED.promulg_num,
                    full_text = EXCLUDED.full_text
            """
            cursor.execute(sql, law_data)
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            print(f"❌ Error inserting law {law_data.get('law_id')}: {e}")
            return False
        finally:
            cursor.close()

    def insert_law_articles(self, articles: List[Dict[str, Any]]) -> int:
        """
        Insert multiple law articles.

        Args:
            articles: List of article dictionaries

        Returns:
            Number of articles inserted
        """
        if not articles:
            return 0

        cursor = self.connection.cursor()
        try:
            sql = """
                INSERT INTO law_articles (law_id, mst, article_type, article_num,
                                        sentence_num, content, parent_article_id)
                VALUES (%(law_id)s, %(mst)s, %(article_type)s, %(article_num)s,
                       %(sentence_num)s, %(content)s, %(parent_article_id)s)
                RETURNING article_id
            """
            execute_batch(cursor, sql, articles)
            self.connection.commit()
            return len(articles)
        except Exception as e:
            self.connection.rollback()
            print(f"❌ Error inserting law articles: {e}")
            return 0
        finally:
            cursor.close()

    def get_law_article(self, law_id: str, article_num: str = None) -> Optional[Dict[str, Any]]:
        """
        Get law article(s) by law_id and optionally article_num.

        Args:
            law_id: Law identifier
            article_num: Article number (e.g., '제37조')

        Returns:
            Article data or None
        """
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        try:
            if article_num:
                sql = """
                    SELECT * FROM law_articles
                    WHERE law_id = %s AND article_num = %s
                    ORDER BY sentence_num
                """
                cursor.execute(sql, (law_id, article_num))
                results = cursor.fetchall()
                if results:
                    return {
                        'article_num': article_num,
                        'content': '\n'.join([r['content'] for r in results])
                    }
            else:
                sql = """
                    SELECT * FROM law_articles
                    WHERE law_id = %s
                    ORDER BY sentence_num
                """
                cursor.execute(sql, (law_id,))
                results = cursor.fetchall()
                if results:
                    return {
                        'law_id': law_id,
                        'content': '\n'.join([r['content'] for r in results])
                    }
            return None
        finally:
            cursor.close()

    # ==========================================
    # 판결문 (Precedents) 관련 메서드
    # ==========================================

    def insert_precedent(self, precedent_data: Dict[str, Any]) -> bool:
        """Insert a precedent document."""
        cursor = self.connection.cursor()
        try:
            sql = """
                INSERT INTO precedents (precedent_id, case_name, case_num, sentence_date,
                                      court_name, court_code, case_type, full_text)
                VALUES (%(precedent_id)s, %(case_name)s, %(case_num)s, %(sentence_date)s,
                       %(court_name)s, %(court_code)s, %(case_type)s, %(full_text)s)
                ON CONFLICT (precedent_id) DO UPDATE SET
                    case_name = EXCLUDED.case_name,
                    case_num = EXCLUDED.case_num,
                    sentence_date = EXCLUDED.sentence_date,
                    court_name = EXCLUDED.court_name,
                    court_code = EXCLUDED.court_code,
                    case_type = EXCLUDED.case_type,
                    full_text = EXCLUDED.full_text
            """
            cursor.execute(sql, precedent_data)
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            print(f"❌ Error inserting precedent {precedent_data.get('precedent_id')}: {e}")
            return False
        finally:
            cursor.close()

    def insert_precedent_sections(self, sections: List[Dict[str, Any]]) -> int:
        """Insert multiple precedent sections."""
        if not sections:
            return 0

        cursor = self.connection.cursor()
        try:
            sql = """
                INSERT INTO precedent_sections (precedent_id, section_type, sentence_num, content)
                VALUES (%(precedent_id)s, %(section_type)s, %(sentence_num)s, %(content)s)
            """
            execute_batch(cursor, sql, sections)
            self.connection.commit()
            return len(sections)
        except Exception as e:
            self.connection.rollback()
            print(f"❌ Error inserting precedent sections: {e}")
            return 0
        finally:
            cursor.close()

    def get_precedent_section(self, precedent_id: str, section_type: str = None) -> Optional[str]:
        """Get precedent section(s) by type."""
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        try:
            if section_type:
                sql = """
                    SELECT content FROM precedent_sections
                    WHERE precedent_id = %s AND section_type = %s
                    ORDER BY sentence_num
                """
                cursor.execute(sql, (precedent_id, section_type))
            else:
                sql = """
                    SELECT content FROM precedent_sections
                    WHERE precedent_id = %s
                    ORDER BY sentence_num
                """
                cursor.execute(sql, (precedent_id,))

            results = cursor.fetchall()
            if results:
                return '\n'.join([r['content'] for r in results])
            return None
        finally:
            cursor.close()

    # ==========================================
    # QA 관련 메서드
    # ==========================================

    def insert_qa(self, qa_data: Dict[str, Any]) -> bool:
        """Insert a QA pair."""
        cursor = self.connection.cursor()
        try:
            sql = """
                INSERT INTO legal_qa (doc_type, doc_id, question, answer, instruction,
                                     sentence_type, origin_word_cnt, label_word_cnt, related_article)
                VALUES (%(doc_type)s, %(doc_id)s, %(question)s, %(answer)s, %(instruction)s,
                       %(sentence_type)s, %(origin_word_cnt)s, %(label_word_cnt)s, %(related_article)s)
            """
            cursor.execute(sql, qa_data)
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            print(f"❌ Error inserting QA: {e}")
            return False
        finally:
            cursor.close()

    # ==========================================
    # 교통법 특화 메서드
    # ==========================================

    def insert_traffic_case(self, traffic_data: Dict[str, Any]) -> bool:
        """Insert traffic-related case data."""
        cursor = self.connection.cursor()
        try:
            sql = """
                INSERT INTO traffic_cases (precedent_id, violation_type, blood_alcohol,
                                         sentence_type, sentence_detail, traffic_law_article)
                VALUES (%(precedent_id)s, %(violation_type)s, %(blood_alcohol)s,
                       %(sentence_type)s, %(sentence_detail)s, %(traffic_law_article)s)
            """
            cursor.execute(sql, traffic_data)
            self.connection.commit()
            return True
        except Exception as e:
            self.connection.rollback()
            print(f"❌ Error inserting traffic case: {e}")
            return False
        finally:
            cursor.close()

    # ==========================================
    # 유틸리티 메서드
    # ==========================================

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics."""
        cursor = self.connection.cursor()
        try:
            stats = {}

            tables = ['laws', 'law_articles', 'precedents', 'precedent_sections',
                     'legal_qa', 'legal_summaries', 'traffic_cases']

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]

            return stats
        finally:
            cursor.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
