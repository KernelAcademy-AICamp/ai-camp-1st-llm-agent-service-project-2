"""
CSV 포맷터
OCR 결과를 CSV 형식으로 변환 (판례 데이터 구조)
"""

import csv
import logging
import re
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass

from app.services.ocr_pipeline import OCRDocumentResult

logger = logging.getLogger(__name__)


@dataclass
class StructuredRow:
    """구조화된 데이터 행"""
    source_id: str
    section_type: str
    sentence_number: int
    content: str


class CSVFormatter:
    """CSV 포맷터 - 판례 데이터 구조"""

    SECTION_KEYWORDS = {
        '판시사항': ['판시사항', 'Summary', 'Holdings'],
        '판결요지': ['판결요지', 'Key Points'],
        '이유': ['이유', 'Rationale', 'Reasoning'],
        '주문': ['주문', 'Conclusion', 'Decision'],
        '참조조문': ['참조조문', 'References', 'Articles'],
        '사건명': ['Case No', 'Case Number', '사건번호'],
    }

    def __init__(self, delimiter: str = ',', encoding: str = 'utf-8'):
        """
        Args:
            delimiter: CSV 구분자
            encoding: 파일 인코딩
        """
        self.delimiter = delimiter
        self.encoding = encoding

    def format_ocr_result(
        self,
        ocr_result: OCRDocumentResult,
        output_path: Optional[str] = None
    ) -> List[StructuredRow]:
        """
        OCR 결과를 구조화된 데이터로 변환

        Args:
            ocr_result: OCR 문서 결과
            output_path: CSV 출력 경로 (None이면 저장 안 함)

        Returns:
            구조화된 행 리스트
        """
        logger.info(f"CSV 포맷팅 시작: {ocr_result.document_id}")

        # 텍스트를 섹션으로 분류
        structured_rows = self._structure_text(
            ocr_result.document_id,
            ocr_result.total_text
        )

        # CSV 저장
        if output_path:
            self.save_to_csv(structured_rows, output_path)

        logger.info(f"CSV 포맷팅 완료: {len(structured_rows)} 행")
        return structured_rows

    def _structure_text(self, source_id: str, text: str) -> List[StructuredRow]:
        """
        텍스트를 구조화된 행으로 변환

        Args:
            source_id: 소스 문서 ID
            text: 전체 텍스트

        Returns:
            구조화된 행 리스트
        """
        rows = []

        # 텍스트를 줄 단위로 분리
        lines = [line.strip() for line in text.split('\n') if line.strip()]

        current_section = '본문'  # 기본 섹션
        sentence_number = 1

        for line in lines:
            # 섹션 감지
            detected_section = self._detect_section(line)
            if detected_section:
                current_section = detected_section
                sentence_number = 1
                continue

            # 문장 분리
            sentences = self._split_sentences(line)

            for sentence in sentences:
                if not sentence.strip():
                    continue

                rows.append(StructuredRow(
                    source_id=source_id,
                    section_type=current_section,
                    sentence_number=sentence_number,
                    content=sentence.strip()
                ))
                sentence_number += 1

        return rows

    def _detect_section(self, line: str) -> Optional[str]:
        """
        섹션 타입 감지

        Args:
            line: 텍스트 라인

        Returns:
            섹션 타입 또는 None
        """
        for section_type, keywords in self.SECTION_KEYWORDS.items():
            for keyword in keywords:
                if keyword in line and len(line) < 100:  # 짧은 라인만 제목으로 간주
                    return section_type
        return None

    def _split_sentences(self, text: str) -> List[str]:
        """
        텍스트를 문장 단위로 분리

        Args:
            text: 입력 텍스트

        Returns:
            문장 리스트
        """
        # 간단한 문장 분리 (마침표, 물음표, 느낌표 기준)
        sentences = re.split(r'[.!?]\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def save_to_csv(self, rows: List[StructuredRow], output_path: str):
        """
        CSV 파일로 저장

        Args:
            rows: 구조화된 행 리스트
            output_path: 출력 파일 경로
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', newline='', encoding=self.encoding) as f:
                writer = csv.writer(f, delimiter=self.delimiter)

                # 헤더
                writer.writerow(['source_id', 'section_type', 'sentence_number', 'content'])

                # 데이터
                for row in rows:
                    writer.writerow([
                        row.source_id,
                        row.section_type,
                        row.sentence_number,
                        row.content
                    ])

            logger.info(f"CSV 저장 완료: {output_path}")

        except Exception as e:
            logger.error(f"CSV 저장 실패: {str(e)}")
            raise

    @staticmethod
    def load_from_csv(csv_path: str) -> List[StructuredRow]:
        """
        CSV 파일에서 로드

        Args:
            csv_path: CSV 파일 경로

        Returns:
            구조화된 행 리스트
        """
        rows = []

        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row_dict in reader:
                    rows.append(StructuredRow(
                        source_id=row_dict['source_id'],
                        section_type=row_dict['section_type'],
                        sentence_number=int(row_dict['sentence_number']),
                        content=row_dict['content']
                    ))

            logger.info(f"CSV 로드 완료: {len(rows)} 행")
            return rows

        except Exception as e:
            logger.error(f"CSV 로드 실패: {str(e)}")
            raise

    def create_summary_csv(
        self,
        ocr_results: List[OCRDocumentResult],
        output_path: str
    ):
        """
        여러 문서의 요약 CSV 생성

        Args:
            ocr_results: OCR 결과 리스트
            output_path: 출력 경로
        """
        try:
            with open(output_path, 'w', newline='', encoding=self.encoding) as f:
                writer = csv.writer(f, delimiter=self.delimiter)

                # 헤더
                writer.writerow([
                    'document_id',
                    'file_name',
                    'total_pages',
                    'average_confidence',
                    'total_words',
                    'processing_time'
                ])

                # 데이터
                for result in ocr_results:
                    writer.writerow([
                        result.document_id,
                        Path(result.file_path).name,
                        result.total_pages,
                        f"{result.average_confidence:.2f}",
                        result.total_word_count,
                        f"{result.total_processing_time:.2f}"
                    ])

            logger.info(f"요약 CSV 저장 완료: {output_path}")

        except Exception as e:
            logger.error(f"요약 CSV 저장 실패: {str(e)}")
            raise
