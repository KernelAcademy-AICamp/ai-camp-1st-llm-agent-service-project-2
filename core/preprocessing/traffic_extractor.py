"""
Traffic Law Metadata Extractor
교통법 관련 메타데이터 자동 추출
"""

import re
from typing import Dict, List, Any


class TrafficMetadataExtractor:
    """
    교통법 관련 메타데이터 추출기
    텍스트에서 교통법 관련 정보 자동 추출
    """

    # 교통법 관련 키워드 정의
    KEYWORDS = {
        "법령": [
            "도로교통법", "교통사고처리특례법", "특정범죄가중처벌법",
            "자동차손해배상보장법", "교통안전법", "자동차관리법"
        ],
        "위반유형": [
            "음주운전", "무면허운전", "신호위반", "과속", "중앙선침범",
            "안전거리미확보", "보행자보호의무위반", "횡단보도", "일시정지위반"
        ],
        "사고유형": [
            "과실치사", "과실치상", "업무상과실", "교통사고",
            "뺑소니", "도주", "인피사고", "물피사고"
        ],
        "처벌": [
            "징역", "금고", "벌금", "집행유예", "보호관찰",
            "사회봉사", "준법운전강의", "면허취소", "면허정지"
        ]
    }

    def __init__(self):
        """Initialize traffic metadata extractor."""
        # 혈중알코올농도 패턴
        self.bac_pattern = re.compile(r'혈중알코올농도[가-힣\s]*(\d+\.\d+)%')

        # 숫자 포함 처벌 패턴 (징역 2년, 벌금 300만원 등)
        self.penalty_pattern = re.compile(r'(징역|금고|벌금)\s*(\d+)\s*(년|개월|만원|원)')

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Extract traffic-related metadata from text.

        Args:
            text: Legal document text

        Returns:
            {
                'is_traffic_related': True/False,
                'violation_types': ['음주운전', ...],
                'accident_types': ['과실치사', ...],
                'penalties': ['징역', ...],
                'related_laws': ['도로교통법 제44조', ...],
                'blood_alcohol': 0.192,
                'penalty_details': {'징역': '2년', ...}
            }
        """
        metadata = {
            'is_traffic_related': False,
            'violation_types': [],
            'accident_types': [],
            'penalties': [],
            'related_laws': [],
            'blood_alcohol': None,
            'penalty_details': {}
        }

        if not text:
            return metadata

        # 1. 키워드 기반 추출
        for category, keywords in self.KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    metadata['is_traffic_related'] = True

                    if category == "법령":
                        # 조문 번호도 추출 시도
                        law_with_article = self._extract_law_article(text, keyword)
                        if law_with_article:
                            metadata['related_laws'].append(law_with_article)

                    elif category == "위반유형":
                        if keyword not in metadata['violation_types']:
                            metadata['violation_types'].append(keyword)

                    elif category == "사고유형":
                        if keyword not in metadata['accident_types']:
                            metadata['accident_types'].append(keyword)

                    elif category == "처벌":
                        if keyword not in metadata['penalties']:
                            metadata['penalties'].append(keyword)

        # 2. 혈중알코올농도 추출
        bac = self.extract_blood_alcohol(text)
        if bac:
            metadata['blood_alcohol'] = bac
            metadata['is_traffic_related'] = True

        # 3. 처벌 상세 정보 추출
        penalty_details = self.extract_penalty_details(text)
        if penalty_details:
            metadata['penalty_details'] = penalty_details

        # 중복 제거
        metadata['violation_types'] = list(set(metadata['violation_types']))
        metadata['accident_types'] = list(set(metadata['accident_types']))
        metadata['penalties'] = list(set(metadata['penalties']))
        metadata['related_laws'] = list(set(metadata['related_laws']))

        return metadata

    def extract_blood_alcohol(self, text: str) -> float:
        """
        Extract blood alcohol concentration from text.

        Args:
            text: Text containing BAC information

        Returns:
            Blood alcohol concentration (e.g., 0.192)
        """
        match = self.bac_pattern.search(text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return None

    def extract_penalty_details(self, text: str) -> Dict[str, str]:
        """
        Extract detailed penalty information.

        Args:
            text: Text containing penalty information

        Returns:
            {'징역': '2년', '벌금': '300만원', ...}
        """
        penalty_details = {}

        matches = self.penalty_pattern.finditer(text)
        for match in matches:
            penalty_type = match.group(1)  # 징역/금고/벌금
            amount = match.group(2)        # 숫자
            unit = match.group(3)          # 년/개월/만원/원

            penalty_details[penalty_type] = f"{amount}{unit}"

        return penalty_details

    def _extract_law_article(self, text: str, law_name: str) -> str:
        """
        Extract law name with article number.

        Args:
            text: Text containing law reference
            law_name: Name of the law

        Returns:
            Law with article (e.g., '도로교통법 제44조')
        """
        # 패턴: 도로교통법 제44조, 도로교통법 제44조의2 등
        pattern = re.compile(rf'{law_name}\s*(제\d+조[의\d]*)')
        match = pattern.search(text)

        if match:
            return f"{law_name} {match.group(1)}"

        return law_name

    def is_traffic_related(self, text: str) -> bool:
        """
        Quick check if text is traffic-related.

        Args:
            text: Text to check

        Returns:
            True if traffic-related
        """
        if not text:
            return False

        # 빠른 체크: 주요 키워드 포함 여부
        key_terms = ["교통", "음주운전", "도로교통법", "과속", "신호위반"]

        for term in key_terms:
            if term in text:
                return True

        return False

    def extract_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """
        Extract metadata from multiple texts.

        Args:
            texts: List of texts

        Returns:
            List of metadata dictionaries
        """
        return [self.extract(text) for text in texts]

    def filter_traffic_documents(self, documents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter documents to keep only traffic-related ones.

        Args:
            documents: List of document dictionaries with 'content' key

        Returns:
            Filtered list of traffic-related documents
        """
        filtered = []

        for doc in documents:
            content = doc.get('content', '')
            metadata = self.extract(content)

            if metadata['is_traffic_related']:
                # 기존 메타데이터에 교통법 메타데이터 추가
                if 'metadata' not in doc:
                    doc['metadata'] = {}

                doc['metadata'].update({
                    'traffic_metadata': metadata
                })

                filtered.append(doc)

        return filtered
