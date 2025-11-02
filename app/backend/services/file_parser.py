"""
파일 파서 모듈
PDF, DOCX, TXT 파일에서 텍스트 추출
"""

from typing import Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class FileParser:
    """파일 파서 클래스"""

    @staticmethod
    def parse_pdf(file_path: str) -> str:
        """
        PDF 파일에서 텍스트 추출

        Args:
            file_path: PDF 파일 경로

        Returns:
            추출된 텍스트
        """
        try:
            import PyPDF2

            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

            logger.info(f"Successfully extracted {len(text)} characters from PDF: {file_path}")
            return text.strip()

        except Exception as e:
            logger.error(f"Failed to parse PDF {file_path}: {e}")
            raise ValueError(f"PDF 파싱 실패: {str(e)}")

    @staticmethod
    def parse_docx(file_path: str) -> str:
        """
        DOCX 파일에서 텍스트 추출

        Args:
            file_path: DOCX 파일 경로

        Returns:
            추출된 텍스트
        """
        try:
            from docx import Document

            doc = Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

            logger.info(f"Successfully extracted {len(text)} characters from DOCX: {file_path}")
            return text.strip()

        except Exception as e:
            logger.error(f"Failed to parse DOCX {file_path}: {e}")
            raise ValueError(f"DOCX 파싱 실패: {str(e)}")

    @staticmethod
    def parse_txt(file_path: str) -> str:
        """
        TXT 파일 읽기

        Args:
            file_path: TXT 파일 경로

        Returns:
            파일 내용
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            logger.info(f"Successfully read {len(text)} characters from TXT: {file_path}")
            return text.strip()

        except UnicodeDecodeError:
            # UTF-8 실패 시 CP949 시도 (한글 윈도우 파일)
            try:
                with open(file_path, 'r', encoding='cp949') as f:
                    text = f.read()
                logger.info(f"Successfully read {len(text)} characters from TXT (CP949): {file_path}")
                return text.strip()
            except Exception as e:
                logger.error(f"Failed to parse TXT {file_path}: {e}")
                raise ValueError(f"TXT 파싱 실패: {str(e)}")

        except Exception as e:
            logger.error(f"Failed to parse TXT {file_path}: {e}")
            raise ValueError(f"TXT 파싱 실패: {str(e)}")

    @classmethod
    def parse_file(cls, file_path: str) -> str:
        """
        파일 확장자에 따라 자동으로 파싱

        Args:
            file_path: 파일 경로

        Returns:
            추출된 텍스트
        """
        path = Path(file_path)
        extension = path.suffix.lower()

        if extension == '.pdf':
            return cls.parse_pdf(file_path)
        elif extension in ['.docx', '.doc']:
            return cls.parse_docx(file_path)
        elif extension == '.txt':
            return cls.parse_txt(file_path)
        else:
            raise ValueError(f"지원하지 않는 파일 형식: {extension}")
