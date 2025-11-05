"""
Criminal Law Data Parser
04.형사법 LLM 데이터를 파싱하여 Colab 임베딩용 JSONL 생성

Usage:
    python scripts/parse_criminal_law_data.py
"""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PrecedentParser:
    """HS_P_*.csv (판례) 파일 파서"""

    def __init__(self, max_chunk_size: int = 500):
        self.max_chunk_size = max_chunk_size

    def parse_file(self, file_path: Path) -> List[Dict]:
        """
        판례 CSV 파일 파싱

        Format: 판례일련번호,구분,문장번호,내용
        """
        try:
            chunks = []
            precedent_id = file_path.stem  # HS_P_314016

            # CSV 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                return []

            # 메타데이터 추출
            metadata = self._extract_metadata(rows, precedent_id)

            # 전체 텍스트 구성
            full_text = "\n".join([row['내용'] for row in rows if row.get('내용')])

            # 청킹 (500자 단위로 분할)
            text_chunks = self._chunk_text(full_text, self.max_chunk_size)

            # 각 청크에 메타데이터 추가
            for i, text_chunk in enumerate(text_chunks):
                chunk = {
                    "id": f"{precedent_id}_{i}",
                    "text": text_chunk,
                    "metadata": {
                        **metadata,
                        "chunk_index": i,
                        "total_chunks": len(text_chunks)
                    }
                }
                chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []

    def _extract_metadata(self, rows: List[Dict], precedent_id: str) -> Dict:
        """판례 메타데이터 추출"""
        metadata = {
            "source": precedent_id,
            "type": "precedent",
            "case_number": None,
            "court": None,
            "decision_date": None
        }

        # 첫 20줄에서 메타데이터 추출
        for row in rows[:20]:
            content = row.get('내용', '')

            # 법원명 추출
            if '법원' in content and not metadata['court']:
                metadata['court'] = content.strip()

            # 사건번호 추출 (예: 2023노7795)
            if not metadata['case_number']:
                case_match = re.search(r'\d{4}[가-힣]+\d+', content)
                if case_match:
                    metadata['case_number'] = case_match.group()

            # 판결선고일 추출 (예: 2024.5.24)
            if not metadata['decision_date']:
                date_match = re.search(r'\d{4}\.\d{1,2}\.\d{1,2}', content)
                if date_match:
                    metadata['decision_date'] = date_match.group()

        return metadata

    def _chunk_text(self, text: str, max_size: int) -> List[str]:
        """텍스트를 문장 단위로 청킹"""
        # 문장 단위로 분리 (마침표, 줄바꿈 기준)
        sentences = re.split(r'(?<=[.?!])\s+|\n', text)

        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # 현재 청크에 추가했을 때 크기 확인
            if len(current_chunk) + len(sentence) <= max_size:
                current_chunk += sentence + " "
            else:
                # 현재 청크 저장하고 새 청크 시작
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        # 마지막 청크 추가
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks


class LawParser:
    """HS_B_*.csv (법령) 파일 파서"""

    def parse_file(self, file_path: Path) -> List[Dict]:
        """
        법령 CSV 파일 파싱

        Format: 법령일련번호,MST,구분,문장번호,내용
        """
        try:
            chunks = []
            law_id = file_path.stem  # HS_B_011153

            # CSV 읽기
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            if not rows:
                return []

            # 법령명 추출 (첫 번째 조문에서)
            law_name = self._extract_law_name(rows)

            # 조문별로 그룹화
            article_groups = self._group_by_article(rows)

            # 각 조문을 하나의 청크로
            for i, (article_name, article_text) in enumerate(article_groups.items()):
                chunk = {
                    "id": f"{law_id}_{i}",
                    "text": f"{article_name}\n{article_text}",
                    "metadata": {
                        "source": law_id,
                        "type": "law",
                        "law_name": law_name,
                        "article": article_name,
                        "chunk_index": i,
                        "total_chunks": len(article_groups)
                    }
                }
                chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            return []

    def _extract_law_name(self, rows: List[Dict]) -> str:
        """법령명 추출"""
        # 첫 번째 '조문' 구분에서 법령명 추출
        for row in rows[:10]:
            if row.get('구분') == '조문':
                content = row.get('내용', '')
                if '장' in content or '목적' in content:
                    return content.strip()
        return "법령"

    def _group_by_article(self, rows: List[Dict]) -> Dict[str, str]:
        """조문별로 내용 그룹화"""
        articles = {}
        current_article = None
        current_text = []

        for row in rows:
            content = row.get('내용', '').strip()
            section_type = row.get('구분', '')

            # 새로운 조문 시작
            if section_type == '조문' and '제' in content and '조' in content:
                # 이전 조문 저장
                if current_article and current_text:
                    articles[current_article] = "\n".join(current_text)

                # 새 조문 시작
                current_article = content
                current_text = []
            elif current_article:
                # 현재 조문에 내용 추가
                if content:
                    current_text.append(content)

        # 마지막 조문 저장
        if current_article and current_text:
            articles[current_article] = "\n".join(current_text)

        return articles


class CriminalLawDataParser:
    """형사법 데이터 전체 파서"""

    def __init__(
        self,
        data_dir: str,
        output_file: str,
        max_files: Optional[int] = None
    ):
        self.data_dir = Path(data_dir)
        self.output_file = Path(output_file)
        self.max_files = max_files

        self.precedent_parser = PrecedentParser()
        self.law_parser = LawParser()

        # 출력 디렉토리 생성
        self.output_file.parent.mkdir(parents=True, exist_ok=True)

    def parse_all(self):
        """모든 CSV 파일 파싱"""
        logger.info(f"Starting to parse files from {self.data_dir}")

        # CSV 파일 찾기
        csv_files = list(self.data_dir.glob("*.csv"))
        logger.info(f"Found {len(csv_files)} CSV files")

        if self.max_files:
            csv_files = csv_files[:self.max_files]
            logger.info(f"Limiting to {self.max_files} files for testing")

        # 파일 분류
        precedent_files = [f for f in csv_files if f.stem.startswith("HS_P_")]
        law_files = [f for f in csv_files if f.stem.startswith("HS_B_")]

        logger.info(f"Precedent files: {len(precedent_files)}")
        logger.info(f"Law files: {len(law_files)}")

        total_chunks = 0

        # JSONL 파일에 쓰기 (append 모드)
        with open(self.output_file, 'w', encoding='utf-8') as f:
            # 판례 파싱
            for i, file_path in enumerate(precedent_files):
                if i % 1000 == 0:
                    logger.info(f"Processing precedent file {i}/{len(precedent_files)}")

                chunks = self.precedent_parser.parse_file(file_path)
                for chunk in chunks:
                    f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                    total_chunks += 1

            # 법령 파싱
            for i, file_path in enumerate(law_files):
                if i % 100 == 0:
                    logger.info(f"Processing law file {i}/{len(law_files)}")

                chunks = self.law_parser.parse_file(file_path)
                for chunk in chunks:
                    f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                    total_chunks += 1

        logger.info(f"✅ Parsing complete!")
        logger.info(f"Total chunks created: {total_chunks}")
        logger.info(f"Output file: {self.output_file}")
        logger.info(f"File size: {self.output_file.stat().st_size / 1024 / 1024:.2f} MB")


def main():
    """메인 실행"""
    # 데이터 디렉토리
    DATA_DIR = Path.home() / "Downloads/04.형사법 LLM 사전학습 및 Instruction Tuning 데이터/3.개방데이터/1.데이터/Training/01.원천데이터"

    # 출력 파일
    OUTPUT_FILE = Path(__file__).parent.parent / "data/parsed/criminal_law_chunks.jsonl"

    # 테스트용으로 100개만 파싱하려면: max_files=100
    parser = CriminalLawDataParser(
        data_dir=str(DATA_DIR),
        output_file=str(OUTPUT_FILE),
        max_files=None  # None = 전체 파일 파싱
    )

    start_time = datetime.now()
    parser.parse_all()
    end_time = datetime.now()

    logger.info(f"Total time: {(end_time - start_time).total_seconds():.2f} seconds")


if __name__ == "__main__":
    main()
