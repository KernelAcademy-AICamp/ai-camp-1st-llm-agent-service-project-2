"""
JSON 포맷터
OCR 결과를 JSON 형식으로 변환 (AI 학습용 데이터)
"""

import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

from app.services.ocr_pipeline import OCRDocumentResult

logger = logging.getLogger(__name__)


@dataclass
class AILabelData:
    """AI 학습용 라벨 데이터"""
    instruction: str
    input_text: str
    output_text: str
    metadata: Dict[str, Any]


class JSONFormatter:
    """JSON 포맷터 - AI 학습용 데이터"""

    def __init__(self, indent: int = 2, ensure_ascii: bool = False):
        """
        Args:
            indent: JSON 들여쓰기
            ensure_ascii: ASCII 강제 여부 (False=한글 유지)
        """
        self.indent = indent
        self.ensure_ascii = ensure_ascii

    def format_ocr_result(
        self,
        ocr_result: OCRDocumentResult,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        OCR 결과를 JSON으로 변환

        Args:
            ocr_result: OCR 문서 결과
            output_path: JSON 출력 경로 (None이면 저장 안 함)

        Returns:
            JSON 딕셔너리
        """
        logger.info(f"JSON 포맷팅 시작: {ocr_result.document_id}")

        # JSON 구조 생성
        json_data = {
            'document_id': ocr_result.document_id,
            'file_path': ocr_result.file_path,
            'metadata': {
                'total_pages': ocr_result.total_pages,
                'processed_pages': ocr_result.processed_pages,
                'average_confidence': ocr_result.average_confidence,
                'total_word_count': ocr_result.total_word_count,
                'processing_time': ocr_result.total_processing_time,
                'created_at': ocr_result.created_at.isoformat(),
                **ocr_result.metadata
            },
            'pages': [],
            'full_text': ocr_result.total_text
        }

        # 페이지별 데이터
        for page_result in ocr_result.page_results:
            page_data = {
                'page_number': page_result.page_number,
                'text': page_result.text,
                'confidence': page_result.confidence,
                'word_count': page_result.word_count,
                'processing_time': page_result.processing_time
            }

            if page_result.error:
                page_data['error'] = page_result.error

            json_data['pages'].append(page_data)

        # JSON 저장
        if output_path:
            self.save_to_json(json_data, output_path)

        logger.info(f"JSON 포맷팅 완료")
        return json_data

    def format_for_ai_training(
        self,
        ocr_result: OCRDocumentResult,
        task_type: str = 'summarization',
        output_path: Optional[str] = None
    ) -> List[AILabelData]:
        """
        AI 학습용 데이터 형식으로 변환

        Args:
            ocr_result: OCR 문서 결과
            task_type: 작업 타입 ('summarization', 'classification', 'qa')
            output_path: JSON 출력 경로

        Returns:
            AI 라벨 데이터 리스트
        """
        logger.info(f"AI 학습 데이터 생성: {ocr_result.document_id}, 작업={task_type}")

        ai_data = []

        if task_type == 'summarization':
            # 요약 작업
            ai_data.append(AILabelData(
                instruction="다음 법률 문서를 요약하시오.",
                input_text=ocr_result.total_text,
                output_text="",  # 실제 사용 시 수동 라벨링 필요
                metadata={
                    'document_id': ocr_result.document_id,
                    'task_type': 'summarization',
                    'confidence': ocr_result.average_confidence
                }
            ))

        elif task_type == 'classification':
            # 문서 분류
            ai_data.append(AILabelData(
                instruction="다음 법률 문서의 유형을 분류하시오. (판례, 계약서, 법령 등)",
                input_text=ocr_result.total_text,
                output_text="",  # 실제 사용 시 수동 라벨링 필요
                metadata={
                    'document_id': ocr_result.document_id,
                    'task_type': 'classification',
                    'confidence': ocr_result.average_confidence
                }
            ))

        elif task_type == 'qa':
            # 질의응답 (페이지별)
            for page_result in ocr_result.page_results:
                if page_result.error:
                    continue

                ai_data.append(AILabelData(
                    instruction="다음 법률 문서의 내용에 대해 질문하시오.",
                    input_text=page_result.text,
                    output_text="",  # 실제 사용 시 수동 라벨링 필요
                    metadata={
                        'document_id': ocr_result.document_id,
                        'page_number': page_result.page_number,
                        'task_type': 'qa',
                        'confidence': page_result.confidence
                    }
                ))

        # JSON 저장
        if output_path:
            self.save_ai_training_data(ai_data, output_path)

        logger.info(f"AI 학습 데이터 생성 완료: {len(ai_data)} 샘플")
        return ai_data

    def save_to_json(self, data: Dict[str, Any], output_path: str):
        """
        JSON 파일로 저장

        Args:
            data: JSON 데이터
            output_path: 출력 경로
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(
                    data,
                    f,
                    indent=self.indent,
                    ensure_ascii=self.ensure_ascii
                )

            logger.info(f"JSON 저장 완료: {output_path}")

        except Exception as e:
            logger.error(f"JSON 저장 실패: {str(e)}")
            raise

    def save_ai_training_data(self, ai_data: List[AILabelData], output_path: str):
        """
        AI 학습 데이터 저장

        Args:
            ai_data: AI 라벨 데이터 리스트
            output_path: 출력 경로
        """
        try:
            # dataclass를 dict로 변환
            data_list = [asdict(item) for item in ai_data]

            self.save_to_json(data_list, output_path)

        except Exception as e:
            logger.error(f"AI 학습 데이터 저장 실패: {str(e)}")
            raise

    @staticmethod
    def load_from_json(json_path: str) -> Dict[str, Any]:
        """
        JSON 파일에서 로드

        Args:
            json_path: JSON 파일 경로

        Returns:
            JSON 데이터
        """
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            logger.info(f"JSON 로드 완료: {json_path}")
            return data

        except Exception as e:
            logger.error(f"JSON 로드 실패: {str(e)}")
            raise

    def create_batch_json(
        self,
        ocr_results: List[OCRDocumentResult],
        output_path: str
    ):
        """
        여러 문서를 하나의 JSON으로 통합

        Args:
            ocr_results: OCR 결과 리스트
            output_path: 출력 경로
        """
        try:
            batch_data = {
                'total_documents': len(ocr_results),
                'documents': []
            }

            for result in ocr_results:
                doc_data = self.format_ocr_result(result)
                batch_data['documents'].append(doc_data)

            self.save_to_json(batch_data, output_path)

            logger.info(f"배치 JSON 저장 완료: {len(ocr_results)} 문서")

        except Exception as e:
            logger.error(f"배치 JSON 저장 실패: {str(e)}")
            raise

    def create_jsonl(
        self,
        ocr_results: List[OCRDocumentResult],
        output_path: str
    ):
        """
        JSONL 형식으로 저장 (줄별 JSON)

        Args:
            ocr_results: OCR 결과 리스트
            output_path: 출력 경로
        """
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            with open(output_file, 'w', encoding='utf-8') as f:
                for result in ocr_results:
                    doc_data = self.format_ocr_result(result)
                    f.write(json.dumps(doc_data, ensure_ascii=self.ensure_ascii) + '\n')

            logger.info(f"JSONL 저장 완료: {len(ocr_results)} 문서")

        except Exception as e:
            logger.error(f"JSONL 저장 실패: {str(e)}")
            raise
