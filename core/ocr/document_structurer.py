"""
문서 타입별 맞춤 구조화
"""

import json
import re
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DocumentTypeDetector:
    """문서 타입 자동 인식"""

    @staticmethod
    def detect(text: str, filename: str) -> str:
        """
        문서 타입 자동 인식

        Returns:
            - 'judgment': 판결문
            - 'complaint': 소장
            - 'notice': 내용증명
            - 'settlement': 합의서
            - 'other': 기타
        """
        # 공백 제거한 텍스트 (띄어쓰기 무시)
        text_normalized = re.sub(r'\s+', '', text)

        # 파일명 기반 1차 판단 (우선순위 높음)
        filename_lower = filename.lower()

        if '판결' in filename or 'judgment' in filename_lower:
            return 'judgment'
        elif '소장' in filename or 'complaint' in filename_lower:
            return 'complaint'
        elif '내용증명' in filename or 'notice' in filename_lower:
            return 'notice'
        elif '합의서' in filename or 'settlement' in filename_lower:
            return 'settlement'

        # 텍스트 내용 기반 2차 판단 (공백 무시)
        if '판결' in text_normalized and '주문' in text_normalized:
            return 'judgment'
        elif '소장' in text_normalized and ('청구취지' in text_normalized or '청구원인' in text_normalized):
            return 'complaint'
        elif '내용증명' in text_normalized or ('수신' in text_normalized and '발신' in text_normalized):
            return 'notice'
        elif '합의서' in text_normalized and '갑' in text_normalized and '을' in text_normalized:
            return 'settlement'

        return 'other'


class NoticeStructurer:
    """내용증명 구조화"""

    def __init__(self, text: str, filename: str):
        self.text = text
        self.filename = filename

    def extract_receiver(self) -> str:
        """수신인 추출"""
        patterns = [
            r'수\s*신\s*인?\s*[:：]?\s*([^\n]+)',
            r'받는\s*분\s*[:：]?\s*([^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                receiver = match.group(1).strip()
                # "인:" 같은 접두어 제거
                receiver = re.sub(r'^인\s*[:：]?\s*', '', receiver)
                # 괄호 내용 제거
                receiver = re.sub(r'\(.*?\)', '', receiver).strip()
                # 주소나 연락처 앞에서 끊기 (숫자 3개 이상 연속)
                receiver = re.split(r'\d{3,}', receiver)[0].strip()
                return receiver

        return ""

    def extract_sender(self) -> str:
        """발신인 추출"""
        patterns = [
            r'발\s*신\s*인?\s*[:：]?\s*([^\n]+)',
            r'보내는\s*분\s*[:：]?\s*([^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                sender = match.group(1).strip()
                # "인:" 같은 접두어 제거
                sender = re.sub(r'^인\s*[:：]?\s*', '', sender)
                # 괄호 내용 제거
                sender = re.sub(r'\(.*?\)', '', sender).strip()
                # 주소나 연락처 앞에서 끊기
                sender = re.split(r'\d{3,}', sender)[0].strip()
                return sender

        return ""

    def extract_title(self) -> str:
        """제목 추출"""
        patterns = [
            r'제\s*목\s*[:\s]*([^\n]+)',
            r'제\s*목\s*:?\s*([^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                return match.group(1).strip()

        # 제목 없으면 첫 줄에서 추출
        lines = self.text.split('\n')
        for line in lines[:5]:
            if '내용증명' in line:
                continue
            if len(line.strip()) > 5 and len(line.strip()) < 50:
                return line.strip()

        return ""

    def extract_date(self) -> str:
        """발신일자 추출"""
        patterns = [
            r'(\d{4})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일',
            r'(\d{4})[.-](\d{1,2})[.-](\d{1,2})',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                year, month, day = match.groups()
                return f"{year}.{month.zfill(2)}.{day.zfill(2)}"

        return ""

    def extract_main_content(self) -> str:
        """주요 내용 추출 (개선: 헤더 제거 후 본문 전체 추출)"""

        lines = self.text.split('\n')
        content_start_idx = 0

        # 1단계: 헤더 정보 스킵
        # "내용증명", "제목", "수신인", "발신인", "주소", "전화" 등 헤더 정보를 지나 본문 시작점 찾기
        header_keywords = ['내용증명', '제목', '수신인', '발신인', '전화:', '전화 :', '우편번호', '주소']
        in_header = True

        for i, line in enumerate(lines):
            line_stripped = line.strip()

            # 빈 줄은 스킵
            if not line_stripped:
                continue

            # 헤더 키워드가 있으면 계속 스킵
            if any(keyword in line for keyword in header_keywords):
                in_header = True
                continue

            # 전화번호나 주소 형식 (숫자, 괄호, 하이픈만)
            if re.match(r'^[\d\s\-\(\)]+$', line_stripped):
                continue

            # 실질적 내용이 있는 첫 줄 (5자 이상)
            if len(line_stripped) > 5 and in_header:
                content_start_idx = i
                in_header = False
                break

        # 2단계: 본문 전체 추출 (제한 없음)
        content_lines = lines[content_start_idx:]

        # 3단계: 하단 서명/첨부 제거 (선택적)
        final_content = []
        for line in content_lines:
            # "(인)" 또는 "첨부:" 이후는 서명/첨부이므로 제외
            if re.search(r'\(인\)|^첨\s*부\s*[:：]', line):
                break
            final_content.append(line)

        full_content = '\n'.join(final_content).strip()

        # 글자 수 제한 제거 (전체 내용 저장)
        # 너무 길면 3000자로 제한 (선택)
        # if len(full_content) > 3000:
        #     full_content = full_content[:3000] + "...(이하 생략)"

        return full_content

    def structure(self) -> dict:
        """내용증명 구조화"""
        logger.info(f"내용증명 구조화 중: {self.filename}")

        return {
            "데이터타입": "내용증명",
            "파일명": self.filename,
            "제목": self.extract_title(),
            "수신인": self.extract_receiver(),
            "발신인": self.extract_sender(),
            "발신일자": self.extract_date(),
            "주요내용": self.extract_main_content(),
            "처리시각": datetime.now().isoformat()
        }


class ComplaintStructurer:
    """소장 구조화"""

    def __init__(self, text: str, filename: str):
        self.text = text
        self.filename = filename

    def extract_case_title(self) -> str:
        """사건명 추출"""
        # "손해배상(기)" 같은 패턴
        patterns = [
            r'([가-힣]+\([가-힣]\))',
            r'사건명[:\s]*([^\n]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                return match.group(1).strip()

        # 파일명에서 추출
        if '손해배상' in self.filename:
            return self.filename.split('_')[-1].replace('.pdf', '')

        return ""

    def extract_court(self) -> str:
        """법원 추출"""
        patterns = [
            r'([가-힣]+지방법원)',
            r'([가-힣]+법원)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                return match.group(1)

        return ""

    def extract_plaintiff(self) -> str:
        """원고 추출"""
        patterns = [
            r'원\s*고\s*[:：]?\s*([^\n(]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                plaintiff = match.group(1).strip()
                # 괄호, 주소, 연락처 제거
                plaintiff = re.split(r'[(\d\-]{3,}', plaintiff)[0].strip()
                return plaintiff

        return ""

    def extract_defendant(self) -> str:
        """피고 추출"""
        patterns = [
            r'피\s*고\s*[:：]?\s*([^\n(]+)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                defendant = match.group(1).strip()
                # 괄호, 주소, 연락처 제거
                defendant = re.split(r'[(\d\-]{3,}', defendant)[0].strip()
                return defendant

        return ""

    def extract_claim_purpose(self) -> str:
        """청구취지 추출"""
        patterns = [
            r'청\s*구\s*취\s*지\s*(.*?)(?=청\s*구\s*원\s*인|입\s*증|$)',
            r'청구취지\s*(.*?)(?=청구원인|입증|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.DOTALL)
            if match:
                purpose = match.group(1).strip()
                # 줄바꿈 정리
                purpose = re.sub(r'\n\s*\n', '\n', purpose)
                if len(purpose) > 500:
                    purpose = purpose[:500] + "..."
                return purpose

        return ""

    def extract_claim_cause(self) -> str:
        """청구원인 추출"""
        patterns = [
            r'청\s*구\s*원\s*인\s*(.*?)(?=입\s*증|부\s*속\s*서\s*류|$)',
            r'청구원인\s*(.*?)(?=입증|부속서류|$)',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text, re.DOTALL)
            if match:
                cause = match.group(1).strip()
                # 줄바꿈 정리
                cause = re.sub(r'\n\s*\n', '\n', cause)
                if len(cause) > 1000:
                    cause = cause[:1000] + "..."
                return cause

        return ""

    def extract_claim_amount(self) -> str:
        """청구금액 추출"""
        patterns = [
            r'금\s*([\d,]+)\s*원',
            r'([\d,]+)\s*원',
        ]

        for pattern in patterns:
            match = re.search(pattern, self.text)
            if match:
                amount = match.group(1).replace(',', '')
                return f"{int(amount):,}원"

        return ""

    def structure(self) -> dict:
        """소장 구조화"""
        logger.info(f"소장 구조화 중: {self.filename}")

        return {
            "데이터타입": "소장",
            "파일명": self.filename,
            "사건명": self.extract_case_title(),
            "법원": self.extract_court(),
            "원고": self.extract_plaintiff(),
            "피고": self.extract_defendant(),
            "청구금액": self.extract_claim_amount(),
            "청구취지": self.extract_claim_purpose(),
            "청구원인": self.extract_claim_cause(),
            "처리시각": datetime.now().isoformat()
        }


class JudgmentStructurer:
    """판결문 구조화 (기존 로직)"""

    def __init__(self, text: str, filename: str):
        self.text = text
        self.filename = filename

    def structure(self) -> dict:
        """판결문 구조화 - 기존 로직 사용"""
        # 기존 structure_ocr_data.py의 로직 사용
        from structure_ocr_data import OCRDataStructurer
        from parse_ocr_text import OCRTextParser

        parser = OCRTextParser(self.text, self.filename)
        parsed = parser.parse()

        structurer = OCRDataStructurer(parsed, "교통사고")
        return structurer.structure()


class DocumentStructurer:
    """문서 타입별 자동 구조화"""

    def __init__(self, text: str, filename: str):
        self.text = text
        self.filename = filename
        self.doc_type = DocumentTypeDetector.detect(text, filename)

    def structure(self) -> dict:
        """
        문서 타입에 맞는 구조화 수행

        Returns:
            구조화된 데이터 (문서 타입별로 다른 형식)
        """
        logger.info(f"문서 타입 인식: {self.doc_type}")

        if self.doc_type == 'notice':
            structurer = NoticeStructurer(self.text, self.filename)
        elif self.doc_type == 'complaint':
            structurer = ComplaintStructurer(self.text, self.filename)
        elif self.doc_type == 'judgment':
            structurer = JudgmentStructurer(self.text, self.filename)
        else:
            # 기타 문서는 기본 구조
            return {
                "데이터타입": "기타",
                "파일명": self.filename,
                "텍스트": self.text[:1000] + "..." if len(self.text) > 1000 else self.text,
                "처리시각": datetime.now().isoformat()
            }

        return structurer.structure()


def test_structurer():
    """구조화 테스트"""
    from pathlib import Path

    # 테스트 파일
    test_file = Path("/Users/nw_mac/Documents/Github_crawling/ai-camp-1st-llm-agent-service-project-2/OCR_test/내용증명1_가해자손해배상청구.pdf")

    if not test_file.exists():
        logger.error(f"테스트 파일 없음: {test_file}")
        return

    # PyMuPDF로 텍스트 추출
    import fitz
    doc = fitz.open(test_file)

    pages_text = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        pages_text.append(text)

    doc.close()

    full_text = '\n'.join(pages_text)

    # 구조화
    structurer = DocumentStructurer(full_text, test_file.name)
    result = structurer.structure()

    # 출력
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    test_structurer()
