"""
Law CSV Parser
법령 CSV 파일을 계층적 구조로 파싱
"""

import pandas as pd
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict


class LawParser:
    """
    법령 CSV 파서
    조문/항/호/목 계층 구조를 복원하여 파싱
    """

    def __init__(self):
        """Initialize law parser."""
        self.article_pattern = re.compile(r'제(\d+)조')  # 제N조 패턴

    def parse_csv(self, csv_path: str) -> Dict[str, Any]:
        """
        Parse law CSV file into hierarchical structure.

        Args:
            csv_path: Path to law CSV file

        Returns:
            {
                'law_id': '000239',
                'title': '건설기계관리법',
                'ministry': '국토교통부',
                'articles': [
                    {
                        'article_num': '제1조',
                        'title': '목적',
                        'mst': '...',
                        'content': '전체 조문 내용',
                        'paragraphs': [...]
                    }
                ]
            }
        """
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            df = df.fillna('')

            if len(df) == 0:
                return None

            # 메타데이터 추출 (첫 행에서)
            law_id = str(df.iloc[0]['법령일련번호']) if '법령일련번호' in df.columns else Path(csv_path).stem.split('_')[-1]

            # 법령명 추출 (제1조 등 조문 시작 전 내용에서)
            title = self._extract_title(df)

            # 조문별로 그룹화
            articles = self._group_by_articles(df, law_id)

            return {
                'law_id': law_id,
                'title': title,
                'ministry': '',  # CSV에 있으면 추출
                'articles': articles,
                'full_text': '\n'.join(df['내용'].tolist()) if '내용' in df.columns else ''
            }

        except Exception as e:
            print(f"❌ Error parsing law CSV {csv_path}: {e}")
            return None

    def _extract_title(self, df: pd.DataFrame) -> str:
        """Extract law title from DataFrame."""
        # '내용' 컬럼에서 조문 시작 전 텍스트 찾기
        if '내용' not in df.columns:
            return "Unknown Law"

        for content in df['내용']:
            content = str(content).strip()
            # 제1조 이전에 나오는 법령명
            if content and not content.startswith('제') and not content.startswith('①') and len(content) < 100:
                return content

        return "Unknown Law"

    def _group_by_articles(self, df: pd.DataFrame, law_id: str) -> List[Dict[str, Any]]:
        """
        Group rows by articles (조문).

        Args:
            df: DataFrame with law content
            law_id: Law identifier

        Returns:
            List of article dictionaries
        """
        articles = []
        current_article = None
        article_content = []

        for idx, row in df.iterrows():
            content = str(row.get('내용', '')).strip()
            gubun = str(row.get('구분', '')).strip()
            mst = str(row.get('MST', ''))
            sentence_num = int(row.get('문장번호', idx)) if '문장번호' in row else idx

            # 새로운 조문 시작
            if gubun == '조문' and content.startswith('제'):
                # 이전 조문 저장
                if current_article:
                    current_article['content'] = '\n'.join(article_content)
                    articles.append(current_article)

                # 조문 번호 및 제목 추출
                article_num, article_title = self._extract_article_info(content)

                # 새 조문 시작
                current_article = {
                    'law_id': law_id,
                    'article_num': article_num,
                    'title': article_title,
                    'mst': mst,
                    'article_type': '조문',
                    'sentence_num': sentence_num,
                    'paragraphs': []
                }
                article_content = [content]

            # 조문의 하위 항목 (항/호/목)
            elif current_article and content:
                article_content.append(content)

                # 항/호/목 구조 추가
                if gubun in ['항', '호', '목']:
                    current_article['paragraphs'].append({
                        'type': gubun,
                        'content': content,
                        'sentence_num': sentence_num
                    })

        # 마지막 조문 저장
        if current_article:
            current_article['content'] = '\n'.join(article_content)
            articles.append(current_article)

        return articles

    def _extract_article_info(self, content: str) -> tuple:
        """
        Extract article number and title from content.

        Args:
            content: Article content line

        Returns:
            (article_num, title)
            예: ("제1조", "목적")
        """
        # 패턴: 제1조(목적) or 제1조 목적
        match = self.article_pattern.search(content)
        if match:
            article_num = f"제{match.group(1)}조"

            # 제목 추출
            title = ""
            if '(' in content:
                start = content.index('(')
                end = content.index(')', start)
                title = content[start+1:end]
            elif article_num in content:
                # 제1조 이후 텍스트
                rest = content.split(article_num, 1)[1].strip()
                if rest and not rest[0] in ['①', '1', '가']:
                    title = rest.split()[0] if rest else ""

            return article_num, title

        return "제?조", ""

    def parse_batch(self, csv_paths: List[str], verbose: bool = True) -> List[Dict[str, Any]]:
        """
        Parse multiple law CSV files.

        Args:
            csv_paths: List of CSV file paths
            verbose: Print progress

        Returns:
            List of parsed law dictionaries
        """
        results = []

        for csv_path in csv_paths:
            if verbose:
                print(f"Parsing: {Path(csv_path).name}")

            parsed = self.parse_csv(csv_path)
            if parsed:
                results.append(parsed)

        return results
