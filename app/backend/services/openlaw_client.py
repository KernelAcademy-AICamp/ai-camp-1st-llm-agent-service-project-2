"""
Open Law API Client
대한민국 법제처 판례 API 연동 클라이언트
"""

import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime
import xml.etree.ElementTree as ET
import time

logger = logging.getLogger(__name__)


class OpenLawAPIClient:
    """
    법제처 판례 API 클라이언트
    https://open.law.go.kr API 연동
    """

    def __init__(self, api_key: str):
        """
        Initialize OpenLaw API client

        Args:
            api_key: API 인증키 (법제처 OPEN API 신청 후 받은 키)
        """
        self.api_key = api_key
        self.base_url = "https://www.law.go.kr/DRF"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "LawLawKR/0.1.0 (Criminal Law AI Assistant)"
        })

    def fetch_supreme_court_precedents(
        self,
        limit: int = 10,
        search_keyword: Optional[str] = None,
        case_type: str = "형사"
    ) -> List[Dict]:
        """
        대법원 판례 목록 조회

        Args:
            limit: 조회할 판례 수
            search_keyword: 검색 키워드 (None이면 최신순)
            case_type: 사건 종류 (형사, 민사, 행정 등)

        Returns:
            List of precedent dictionaries
        """
        try:
            # 판례 목록 API 엔드포인트
            endpoint = f"{self.base_url}/lawSearch.do"

            params = {
                "OC": self.api_key,
                "target": "prec",  # 판례
                "type": "XML",  # 응답 형식
                "display": str(limit),  # 조회 건수
                "sort": "ddes",  # 선고일자 내림차순
            }

            # 검색 키워드가 있으면 추가
            if search_keyword:
                params["query"] = search_keyword
            else:
                # 최신 판례 조회 (형사 관련)
                params["query"] = case_type

            logger.info(f"Fetching precedents from OpenLaw API: {params}")

            response = self.session.get(endpoint, params=params, timeout=30)
            response.raise_for_status()

            # XML 파싱
            precedents = self._parse_precedent_list_xml(response.text)

            logger.info(f"Successfully fetched {len(precedents)} precedents")
            return precedents[:limit]

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch precedents from OpenLaw API: {e}")
            return []
        except Exception as e:
            logger.error(f"Error parsing precedent data: {e}")
            return []

    def fetch_precedent_detail(self, precedent_serial: str) -> Optional[Dict]:
        """
        판례 상세 정보 조회

        Args:
            precedent_serial: 판례 일련번호

        Returns:
            Detailed precedent dictionary or None
        """
        try:
            endpoint = f"{self.base_url}/lawService.do"

            params = {
                "OC": self.api_key,
                "target": "prec",
                "type": "XML",
                "ID": precedent_serial,
            }

            logger.info(f"Fetching precedent detail: {precedent_serial}")

            response = self.session.get(endpoint, params=params, timeout=30)
            response.raise_for_status()

            detail = self._parse_precedent_detail_xml(response.text)

            if detail:
                logger.info(f"Successfully fetched detail for {precedent_serial}")
            return detail

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch precedent detail: {e}")
            return None
        except Exception as e:
            logger.error(f"Error parsing precedent detail: {e}")
            return None

    def _parse_precedent_list_xml(self, xml_text: str) -> List[Dict]:
        """
        판례 목록 XML 파싱

        Args:
            xml_text: XML 응답 텍스트

        Returns:
            List of precedent dictionaries
        """
        try:
            root = ET.fromstring(xml_text)
            precedents = []

            # prec 태그들 찾기
            for prec in root.findall('.//prec'):
                try:
                    # 기본 정보 추출
                    case_number = self._get_xml_text(prec, '판례일련번호', '사건번호')
                    title = self._get_xml_text(prec, '판례내용', '사건명')
                    summary = self._get_xml_text(prec, '판시사항', '판례요지')
                    decision_date_str = self._get_xml_text(prec, '선고일자')
                    court = self._get_xml_text(prec, '법원명', '법원종류코드명')
                    serial = self._get_xml_text(prec, '판례일련번호')

                    if not case_number or not decision_date_str:
                        continue

                    # 날짜 파싱
                    try:
                        decision_date = datetime.strptime(decision_date_str, "%Y%m%d")
                    except:
                        decision_date = datetime.now()

                    precedent = {
                        "case_number": case_number,
                        "title": title or f"판례 {case_number}",
                        "summary": summary,
                        "court": court or "대법원",
                        "decision_date": decision_date,
                        "precedent_serial": serial,
                        "case_link": f"https://www.law.go.kr/LSW/precInfoP.do?precSeq={serial}" if serial else None,
                    }

                    precedents.append(precedent)

                except Exception as e:
                    logger.warning(f"Failed to parse precedent item: {e}")
                    continue

            return precedents

        except ET.ParseError as e:
            logger.error(f"XML parsing error: {e}")
            return []

    def _parse_precedent_detail_xml(self, xml_text: str) -> Optional[Dict]:
        """
        판례 상세 정보 XML 파싱

        Args:
            xml_text: XML 응답 텍스트

        Returns:
            Precedent detail dictionary or None
        """
        try:
            root = ET.fromstring(xml_text)
            prec = root.find('.//prec')

            if prec is None:
                return None

            full_text_parts = []

            # 판시사항
            pansi = self._get_xml_text(prec, '판시사항')
            if pansi:
                full_text_parts.append(f"[판시사항]\n{pansi}")

            # 판결요지
            yoji = self._get_xml_text(prec, '판결요지', '판례요지')
            if yoji:
                full_text_parts.append(f"\n[판결요지]\n{yoji}")

            # 참조조문
            ref = self._get_xml_text(prec, '참조조문')
            if ref:
                full_text_parts.append(f"\n[참조조문]\n{ref}")

            # 전문
            full = self._get_xml_text(prec, '판례내용', '전문')
            if full:
                full_text_parts.append(f"\n[판례전문]\n{full}")

            full_text = "\n".join(full_text_parts) if full_text_parts else None

            return {
                "full_text": full_text,
                "summary": self._get_xml_text(prec, '판시사항', '판례요지'),
            }

        except ET.ParseError as e:
            logger.error(f"XML parsing error for detail: {e}")
            return None

    def _get_xml_text(self, element: ET.Element, *tag_names: str) -> Optional[str]:
        """
        XML 요소에서 텍스트 추출 (여러 태그명 시도)

        Args:
            element: XML 요소
            tag_names: 시도할 태그 이름들

        Returns:
            텍스트 내용 또는 None
        """
        for tag in tag_names:
            child = element.find(f'.//{tag}')
            if child is not None and child.text:
                return child.text.strip()
        return None

    def test_connection(self) -> bool:
        """
        API 연결 테스트

        Returns:
            True if connection successful, False otherwise
        """
        try:
            endpoint = f"{self.base_url}/lawSearch.do"
            params = {
                "OC": self.api_key,
                "target": "prec",
                "type": "XML",
                "display": "1",
                "query": "형사",
            }

            response = self.session.get(endpoint, params=params, timeout=10)
            response.raise_for_status()

            logger.info("OpenLaw API connection test successful")
            return True

        except Exception as e:
            logger.error(f"OpenLaw API connection test failed: {e}")
            return False
