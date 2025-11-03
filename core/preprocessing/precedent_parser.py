"""
Precedent CSV Parser
판결문 CSV 파일을 섹션별로 파싱
"""

import pandas as pd
import re
from pathlib import Path
from typing import Dict, List, Any, Optional


class PrecedentParser:
    """
    판결문 CSV 파서
    판시사항/판결요지/주문/이유 등 섹션별로 파싱
    """

    def __init__(self):
        """Initialize precedent parser."""
        # 섹션 타입 정의
        self.section_types = {
            '판시사항': 'summary',
            '판결요지': 'summary',
            '참조조문': 'reference',
            '판례내용': 'content',
            '주문': 'judgment',
            '이유': 'reasoning'
        }

    def parse_csv(self, csv_path: str) -> Dict[str, Any]:
        """
        Parse precedent CSV file into structured sections.

        Args:
            csv_path: Path to precedent CSV file

        Returns:
            {
                'precedent_id': '100029',
                'case_name': '...',
                'case_num': '84도2229',
                'sentence_date': '1984-12-26',
                'court_name': '대법원',
                'court_code': '...',
                'case_type': '형사',
                'sections': {
                    'summary': '판시사항 + 판결요지',
                    'judgment': '주문',
                    'reasoning': '이유',
                    ...
                },
                'full_text': '전문'
            }
        """
        try:
            df = pd.read_csv(csv_path, encoding='utf-8')
            df = df.fillna('')

            if len(df) == 0:
                return None

            # 메타데이터 추출
            precedent_id = str(df.iloc[0]['판례일련번호']) if '판례일련번호' in df.columns else Path(csv_path).stem.split('_')[-1]

            # 메타데이터 파싱
            metadata = self._extract_metadata(df)

            # 섹션별로 그룹화
            sections = self._group_by_sections(df)

            return {
                'precedent_id': precedent_id,
                **metadata,
                'sections': sections,
                'full_text': '\n'.join(df['내용'].tolist()) if '내용' in df.columns else ''
            }

        except Exception as e:
            print(f"❌ Error parsing precedent CSV {csv_path}: {e}")
            return None

    def _extract_metadata(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Extract metadata from precedent DataFrame.

        Args:
            df: Precedent DataFrame

        Returns:
            Metadata dictionary
        """
        metadata = {
            'case_name': '',
            'case_num': '',
            'sentence_date': None,
            'court_name': '',
            'court_code': '',
            'case_type': '형사'
        }

        # '내용' 컬럼에서 메타데이터 추출
        if '내용' not in df.columns:
            return metadata

        # 패턴 정의
        patterns = {
            'court_name': r'(대법원|고등법원|지방법원|.*법원)',
            'case_num': r'(\d{2,4}[가-힣]\d{3,5})',
            'sentence_date': r'(\d{4}\.\s?\d{1,2}\.\s?\d{1,2}|\d{4}-\d{2}-\d{2})'
        }

        for idx, row in df.iterrows():
            content = str(row.get('내용', '')).strip()

            # 법원명
            if not metadata['court_name'] and '법원' in content:
                match = re.search(patterns['court_name'], content)
                if match:
                    metadata['court_name'] = match.group(1)

            # 사건번호
            if not metadata['case_num']:
                match = re.search(patterns['case_num'], content)
                if match:
                    metadata['case_num'] = match.group(1)

            # 선고일
            if not metadata['sentence_date']:
                match = re.search(patterns['sentence_date'], content)
                if match:
                    date_str = match.group(1).replace('.', '-').replace(' ', '')
                    metadata['sentence_date'] = date_str

            # 첫 10줄에서 충분히 추출했으면 종료
            if idx > 10 and metadata['court_name'] and metadata['case_num']:
                break

        return metadata

    def _group_by_sections(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Group rows by sections.

        Args:
            df: Precedent DataFrame

        Returns:
            {'summary': '...', 'judgment': '...', 'reasoning': '...'}
        """
        sections = {
            'summary': [],
            'reference': [],
            'judgment': [],
            'reasoning': [],
            'other': []
        }

        current_section = 'other'

        for idx, row in df.iterrows():
            content = str(row.get('내용', '')).strip()
            gubun = str(row.get('구분', '')).strip()

            if not content:
                continue

            # 섹션 타입 결정
            if gubun in self.section_types:
                current_section = self.section_types[gubun]

            # 특수 키워드로 섹션 감지
            if '【주    문】' in content or '【주문】' in content:
                current_section = 'judgment'
                content = content.replace('【주    문】', '').replace('【주문】', '').strip()
            elif '【이    유】' in content or '【이유】' in content:
                current_section = 'reasoning'
                content = content.replace('【이    유】', '').replace('【이유】', '').strip()

            # 내용 추가
            if content:
                sections[current_section].append(content)

        # 리스트를 문자열로 변환
        return {
            section: '\n'.join(contents)
            for section, contents in sections.items()
            if contents  # 내용이 있는 섹션만
        }

    def create_sections_list(self, parsed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert sections dict to list format for database insertion.

        Args:
            parsed_data: Parsed precedent data

        Returns:
            List of section dictionaries for DB
        """
        sections_list = []
        precedent_id = parsed_data['precedent_id']

        for section_type, content in parsed_data['sections'].items():
            if content and content.strip():
                # 문장 단위로 분리 (선택사항)
                sentences = content.split('\n')

                for sentence_num, sentence in enumerate(sentences, 1):
                    if sentence.strip():
                        sections_list.append({
                            'precedent_id': precedent_id,
                            'section_type': section_type,
                            'sentence_num': sentence_num,
                            'content': sentence.strip()
                        })

        return sections_list

    def parse_batch(self, csv_paths: List[str], verbose: bool = True) -> List[Dict[str, Any]]:
        """
        Parse multiple precedent CSV files.

        Args:
            csv_paths: List of CSV file paths
            verbose: Print progress

        Returns:
            List of parsed precedent dictionaries
        """
        results = []

        for csv_path in csv_paths:
            if verbose:
                print(f"Parsing: {Path(csv_path).name}")

            parsed = self.parse_csv(csv_path)
            if parsed:
                results.append(parsed)

        return results
