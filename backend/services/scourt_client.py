"""
Supreme Court Portal Client
대법원 사법정보공개포털 판례 크롤링 클라이언트
https://portal.scourt.go.kr/pgp/index.on
"""

import requests
import logging
from typing import List, Dict, Optional
from datetime import datetime
import json
import time
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class ScourtClient:
    """
    대법원 사법정보공개포털 크롤링 클라이언트
    https://portal.scourt.go.kr/pgp/index.on 연동
    """

    def __init__(self):
        """
        Initialize Supreme Court Portal client
        """
        self.base_url = "https://portal.scourt.go.kr/pgp"
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": "https://portal.scourt.go.kr",
            "Referer": "https://portal.scourt.go.kr/pgp/index.on"
        })

    def search_precedents(
        self,
        keyword: Optional[str] = None,
        case_type: Optional[str] = None,
        court_type: str = "대법원",
        limit: int = 20,
        page: int = 1
    ) -> List[Dict]:
        """
        판례 검색

        Args:
            keyword: 검색 키워드
            case_type: 사건 종류 (형사, 민사, 행정, 가사, 조세, 특허)
            court_type: 법원 종류 (대법원, 고등법원, 하급심 등)
            limit: 조회할 판례 수 (페이지당)
            page: 페이지 번호

        Returns:
            List of precedent dictionaries
        """
        try:
            # API 엔드포인트
            search_url = f"{self.base_url}/pgp1011/selectJdcpctLst.on"

            # 검색 파라미터 구성
            # Websquare 프레임워크는 XML 형식의 데이터를 주고받음
            data = {
                "w2xPath": "/ui/pgp1000/PGP1011M01.xml",
                "srchwd": keyword if keyword else "*",  # * = 전체 검색
                "pageIdx": str(page),
                "pageSize": str(limit),
                "courtTypeCd": self._get_court_code(court_type),
                "caseTypeNm": case_type if case_type else "",
            }

            logger.info(f"Searching precedents with params: {data}")

            response = self.session.post(search_url, data=data, timeout=30)
            response.raise_for_status()

            # 응답 파싱
            precedents = self._parse_search_results(response.text)

            logger.info(f"Found {len(precedents)} precedents")
            return precedents

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to search precedents: {e}")
            return []
        except Exception as e:
            logger.error(f"Error searching precedents: {e}")
            return []

    def fetch_precedent_detail(self, precedent_id: str) -> Optional[Dict]:
        """
        판례 상세 정보 조회

        Args:
            precedent_id: 판례 일련번호 (jisCntntsSrno)

        Returns:
            Detailed precedent dictionary or None
        """
        try:
            # 상세 정보 API 엔드포인트
            detail_url = f"{self.base_url}/pgp1011/selectJdcpctDtl.on"

            data = {
                "w2xPath": "/ui/pgp1000/PGP1011M04.xml",
                "jisCntntsSrno": precedent_id,
            }

            logger.info(f"Fetching precedent detail: {precedent_id}")

            response = self.session.post(detail_url, data=data, timeout=30)
            response.raise_for_status()

            # 응답 파싱
            detail = self._parse_precedent_detail(response.text)

            if detail:
                # 본문 조회
                full_text = self.fetch_precedent_full_text(precedent_id)
                if full_text:
                    detail['full_text'] = full_text

                # 관련 데이터 조회 (참조판례, 참조조문)
                related_data = self.fetch_related_data(precedent_id)
                if related_data:
                    detail.update(related_data)

            return detail

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch precedent detail: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching precedent detail: {e}")
            return None

    def fetch_precedent_full_text(self, precedent_id: str) -> Optional[str]:
        """
        판례 전문 조회

        Args:
            precedent_id: 판례 일련번호

        Returns:
            Full text of precedent or None
        """
        try:
            # 본문 조회 API
            text_url = f"{self.base_url}/pgp1011/selectJdcpctCtxt.on"

            data = {
                "jisCntntsSrno": precedent_id,
            }

            logger.info(f"Fetching precedent full text: {precedent_id}")

            response = self.session.post(text_url, data=data, timeout=30)
            response.raise_for_status()

            # JSON 응답 파싱
            try:
                json_data = response.json()

                # 전문 추출
                if 'jdcpctCtxt' in json_data:
                    return json_data['jdcpctCtxt']
                elif 'fullText' in json_data:
                    return json_data['fullText']
                else:
                    # HTML 파싱 시도
                    soup = BeautifulSoup(response.text, 'html.parser')
                    text_elem = soup.find('div', class_='jdcpct_ctxt')
                    if text_elem:
                        return text_elem.get_text(strip=True)

            except json.JSONDecodeError:
                # HTML 응답인 경우
                soup = BeautifulSoup(response.text, 'html.parser')
                text_elem = soup.find('div', class_='jdcpct_ctxt')
                if text_elem:
                    return text_elem.get_text(strip=True)

            return None

        except Exception as e:
            logger.error(f"Error fetching precedent full text: {e}")
            return None

    def fetch_related_data(self, precedent_id: str) -> Optional[Dict]:
        """
        관련 데이터 조회 (참조판례, 참조조문 등)

        Args:
            precedent_id: 판례 일련번호

        Returns:
            Dictionary with related precedents and statutes
        """
        try:
            # 관련 데이터 API
            related_url = f"{self.base_url}/pgp1011/selectReltDataNtwk.on"

            data = {
                "jisCntntsSrno": precedent_id,
            }

            logger.info(f"Fetching related data: {precedent_id}")

            response = self.session.post(related_url, data=data, timeout=30)
            response.raise_for_status()

            # JSON 파싱
            try:
                json_data = response.json()

                return {
                    "reference_precedents": json_data.get('refcJdcpctLst', []),
                    "reference_statutes": json_data.get('refcPrvsLst', []),
                    "context_reference_precedents": json_data.get('ctxtRefcJdcpctLst', []),
                    "context_reference_statutes": json_data.get('ctxtRefcPrvsLst', []),
                }
            except json.JSONDecodeError:
                logger.warning("Failed to parse related data as JSON")
                return None

        except Exception as e:
            logger.error(f"Error fetching related data: {e}")
            return None

    def _parse_search_results(self, html_or_json: str) -> List[Dict]:
        """
        검색 결과 파싱

        Args:
            html_or_json: API 응답 (HTML 또는 JSON)

        Returns:
            List of precedent dictionaries
        """
        precedents = []

        try:
            # JSON 파싱 시도
            try:
                data = json.loads(html_or_json)

                if 'jdcpctLst' in data:
                    items = data['jdcpctLst']
                elif 'list' in data:
                    items = data['list']
                else:
                    items = data if isinstance(data, list) else []

                for item in items:
                    precedent = self._extract_precedent_from_json(item)
                    if precedent:
                        precedents.append(precedent)

            except json.JSONDecodeError:
                # HTML 파싱
                soup = BeautifulSoup(html_or_json, 'html.parser')

                # 판례 목록 테이블 찾기
                rows = soup.find_all('tr', class_='jdcpct_item')

                for row in rows:
                    precedent = self._extract_precedent_from_html(row)
                    if precedent:
                        precedents.append(precedent)

        except Exception as e:
            logger.error(f"Error parsing search results: {e}")

        return precedents

    def _parse_precedent_detail(self, html_or_json: str) -> Optional[Dict]:
        """
        판례 상세 정보 파싱

        Args:
            html_or_json: API 응답

        Returns:
            Precedent detail dictionary or None
        """
        try:
            # JSON 파싱 시도
            try:
                data = json.loads(html_or_json)
                return self._extract_detail_from_json(data)
            except json.JSONDecodeError:
                # HTML 파싱
                soup = BeautifulSoup(html_or_json, 'html.parser')
                return self._extract_detail_from_html(soup)

        except Exception as e:
            logger.error(f"Error parsing precedent detail: {e}")
            return None

    def _extract_precedent_from_json(self, item: Dict) -> Optional[Dict]:
        """JSON 데이터에서 판례 정보 추출"""
        try:
            # 선고일자 파싱
            decision_date_str = item.get('slgoYmd', item.get('decisionDate', ''))
            try:
                decision_date = datetime.strptime(decision_date_str, "%Y%m%d")
            except:
                decision_date = datetime.now()

            return {
                "precedent_id": item.get('jisCntntsSrno', ''),
                "case_number": item.get('caseNo', item.get('caseNumber', '')),
                "title": item.get('caseNm', item.get('title', '')),
                "summary": item.get('jdcpctYoji', item.get('summary', '')),
                "court": item.get('courtNm', item.get('court', '대법원')),
                "decision_date": decision_date,
                "case_type": item.get('caseTypeNm', item.get('caseType', '')),
            }
        except Exception as e:
            logger.warning(f"Failed to extract precedent from JSON: {e}")
            return None

    def _extract_precedent_from_html(self, row) -> Optional[Dict]:
        """HTML 요소에서 판례 정보 추출"""
        try:
            # 사건번호
            case_num_elem = row.find('td', class_='case_number')
            case_number = case_num_elem.get_text(strip=True) if case_num_elem else ""

            # 제목
            title_elem = row.find('td', class_='case_title')
            title = title_elem.get_text(strip=True) if title_elem else ""

            # 판례 ID
            link_elem = row.find('a', href=True)
            precedent_id = ""
            if link_elem and 'jisCntntsSrno=' in link_elem['href']:
                precedent_id = link_elem['href'].split('jisCntntsSrno=')[1].split('&')[0]

            return {
                "precedent_id": precedent_id,
                "case_number": case_number,
                "title": title,
                "summary": "",
                "court": "대법원",
                "decision_date": datetime.now(),
                "case_type": "",
            }
        except Exception as e:
            logger.warning(f"Failed to extract precedent from HTML: {e}")
            return None

    def _extract_detail_from_json(self, data: Dict) -> Optional[Dict]:
        """JSON에서 상세 정보 추출"""
        try:
            return {
                "case_number": data.get('caseNo', ''),
                "title": data.get('caseNm', ''),
                "court": data.get('courtNm', '대법원'),
                "decision_date": data.get('slgoYmd', ''),
                "case_type": data.get('caseTypeNm', ''),
                "summary": data.get('jdcpctYoji', ''),
                "judgment_summary": data.get('pansiSahang', ''),  # 판시사항
                "full_text": data.get('jdcpctCtxt', ''),
            }
        except Exception as e:
            logger.warning(f"Failed to extract detail from JSON: {e}")
            return None

    def _extract_detail_from_html(self, soup) -> Optional[Dict]:
        """HTML에서 상세 정보 추출"""
        try:
            detail = {}

            # 제목
            title_elem = soup.find('h4', class_='case_title')
            if title_elem:
                detail['title'] = title_elem.get_text(strip=True)

            # 판시사항
            pansi_elem = soup.find('div', class_='pansi_sahang')
            if pansi_elem:
                detail['judgment_summary'] = pansi_elem.get_text(strip=True)

            # 판결요지
            yoji_elem = soup.find('div', class_='jdcpct_yoji')
            if yoji_elem:
                detail['summary'] = yoji_elem.get_text(strip=True)

            return detail if detail else None

        except Exception as e:
            logger.warning(f"Failed to extract detail from HTML: {e}")
            return None

    def _get_court_code(self, court_type: str) -> str:
        """법원 종류 코드 매핑"""
        court_codes = {
            "대법원": "1",
            "고등법원": "2",
            "하급심": "3",
            "헌법재판소": "4",
        }
        return court_codes.get(court_type, "1")

    def test_connection(self) -> bool:
        """
        연결 테스트

        Returns:
            True if connection successful, False otherwise
        """
        try:
            test_results = self.search_precedents(limit=1)
            return len(test_results) > 0
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
