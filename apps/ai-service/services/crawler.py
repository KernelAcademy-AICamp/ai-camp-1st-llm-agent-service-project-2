"""
Crawler Service

법률 데이터 크롤링 서비스
- 국가법령정보센터 Open API 연동
- 판례 API 연동
- 법령 API 연동
- 웹 크롤링

API 문서: https://open.law.go.kr/LSO/openApi/guideList.do
"""
import asyncio
import logging
import os
import httpx
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# 국가법령정보 Open API 기본 설정
LAW_GO_KR_API_BASE = "http://www.law.go.kr/DRF"
DEFAULT_OC = os.getenv("LAW_GO_KR_OC", "")  # 환경변수에서 API 키 로드


class CrawlResult(BaseModel):
    """크롤링 결과 모델"""
    success: bool
    documents_collected: int = 0
    errors: List[str] = []
    metadata: Dict[str, Any] = {}


class CrawlDocument(BaseModel):
    """크롤링된 문서 모델"""
    title: str
    content: str
    doc_type: str
    source_url: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseCrawler(ABC):
    """크롤러 베이스 클래스"""

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.timeout = self.config.get('timeout', 30)
        self.oc = self.config.get('oc', DEFAULT_OC)

    @abstractmethod
    async def crawl(
        self,
        filters: Dict[str, Any] = None
    ) -> CrawlResult:
        """크롤링 실행"""
        pass

    async def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Dict[str, Any] = None,
        json: Dict[str, Any] = None,
        headers: Dict[str, str] = None
    ) -> httpx.Response:
        """HTTP 요청"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json,
                headers=headers
            )
            return response

    def _parse_xml_response(self, xml_text: str) -> Dict[str, Any]:
        """XML 응답 파싱"""
        try:
            root = ET.fromstring(xml_text)
            return self._element_to_dict(root)
        except ET.ParseError as e:
            logger.error(f"XML 파싱 오류: {e}")
            return {}

    def _element_to_dict(self, element: ET.Element) -> Dict[str, Any]:
        """XML Element를 딕셔너리로 변환"""
        result = {}

        # 텍스트 콘텐츠
        if element.text and element.text.strip():
            result['_text'] = element.text.strip()

        # 자식 요소들
        children = list(element)
        if children:
            child_dict = {}
            for child in children:
                child_data = self._element_to_dict(child)
                if child.tag in child_dict:
                    # 같은 태그가 여러 개면 리스트로
                    if not isinstance(child_dict[child.tag], list):
                        child_dict[child.tag] = [child_dict[child.tag]]
                    child_dict[child.tag].append(child_data)
                else:
                    child_dict[child.tag] = child_data
            result.update(child_dict)

        # 속성
        if element.attrib:
            result['_attrib'] = element.attrib

        # 단순 텍스트 노드면 텍스트만 반환
        if len(result) == 1 and '_text' in result:
            return result['_text']

        return result


class CourtPrecedentCrawler(BaseCrawler):
    """
    대법원 판례 크롤러

    국가법령정보센터 판례 API를 통해 판례 데이터를 수집합니다.

    API Endpoints:
    - 목록 조회: http://www.law.go.kr/DRF/lawSearch.do?target=prec
    - 본문 조회: http://www.law.go.kr/DRF/lawService.do?target=prec
    """

    LIST_URL = f"{LAW_GO_KR_API_BASE}/lawSearch.do"
    DETAIL_URL = f"{LAW_GO_KR_API_BASE}/lawService.do"

    def __init__(self, base_url: str = None, config: Dict[str, Any] = None):
        super().__init__(config)
        self.base_url = base_url or self.LIST_URL

    async def crawl(
        self,
        filters: Dict[str, Any] = None
    ) -> CrawlResult:
        """
        판례 크롤링 실행

        Args:
            filters: 필터 조건
                - keyword: 검색 키워드
                - court: 법원명 (예: 대법원)
                - case_number: 사건번호
                - start_date: 선고일자 시작 (YYYYMMDD)
                - end_date: 선고일자 종료 (YYYYMMDD)
                - display: 결과 개수 (기본 20, 최대 100)
                - page: 페이지 번호

        Returns:
            CrawlResult: 크롤링 결과
        """
        filters = filters or {}
        documents = []
        errors = []

        try:
            logger.info(f"판례 크롤링 시작: filters={filters}")

            # Mock 모드 체크
            if self.config.get('use_mock', False):
                documents = await self._generate_mock_precedents(filters)
            else:
                documents = await self._fetch_precedents(filters)

            logger.info(f"판례 크롤링 완료: {len(documents)}건 수집")

            return CrawlResult(
                success=True,
                documents_collected=len(documents),
                errors=errors,
                metadata={
                    'source': 'COURT_API',
                    'api_base': self.LIST_URL,
                    'filters': filters,
                    'documents': [doc.model_dump() for doc in documents[:10]]
                }
            )

        except Exception as e:
            logger.error(f"판례 크롤링 실패: {e}")
            errors.append(str(e))
            return CrawlResult(
                success=False,
                documents_collected=0,
                errors=errors,
                metadata={'error': str(e)}
            )

    async def _fetch_precedents(
        self,
        filters: Dict[str, Any]
    ) -> List[CrawlDocument]:
        """국가법령정보센터 API에서 판례 수집"""
        documents = []

        # API 파라미터 구성
        params = {
            'OC': self.oc,
            'target': 'prec',
            'type': 'XML',
            'display': filters.get('display', 20),
            'page': filters.get('page', 1),
        }

        # 검색 키워드
        if filters.get('keyword'):
            params['query'] = filters['keyword']
            params['search'] = filters.get('search_type', 1)  # 1=판례명, 2=본문

        # 법원명 필터
        if filters.get('court'):
            params['curt'] = filters['court']

        # 사건번호 필터
        if filters.get('case_number'):
            params['nb'] = filters['case_number']

        # 선고일자 범위
        if filters.get('start_date') or filters.get('end_date'):
            start = filters.get('start_date', '').replace('-', '')
            end = filters.get('end_date', '').replace('-', '')
            if start and end:
                params['prncYd'] = f"{start}~{end}"
            elif start:
                params['prncYd'] = f"{start}~"
            elif end:
                params['prncYd'] = f"~{end}"

        # 정렬
        if filters.get('sort'):
            params['sort'] = filters['sort']

        logger.info(f"판례 목록 API 호출: {self.LIST_URL}, params={params}")

        try:
            response = await self._make_request(self.LIST_URL, params=params)

            if response.status_code != 200:
                logger.error(f"API 응답 오류: {response.status_code}")
                return documents

            # XML 파싱
            data = self._parse_xml_response(response.text)

            # 검색 결과 추출
            total_cnt = data.get('totalCnt', 0)
            logger.info(f"판례 검색 결과: 총 {total_cnt}건")

            # 판례 목록 처리
            prec_list = data.get('prec', [])
            if not isinstance(prec_list, list):
                prec_list = [prec_list] if prec_list else []

            for prec in prec_list:
                if not prec:
                    continue

                # 판례 상세 정보 조회 (선택적)
                prec_id = prec.get('판례일련번호', '')
                case_name = prec.get('사건명', '')
                case_number = prec.get('사건번호', '')
                decision_date = prec.get('선고일자', '')
                court_name = prec.get('법원명', '')
                case_type = prec.get('사건종류명', '')
                judgment_type = prec.get('판결유형', '')

                # 본문 가져오기 (상세 조회)
                content = ""
                if prec_id and filters.get('fetch_content', True):
                    content = await self._fetch_precedent_detail(prec_id)

                doc = CrawlDocument(
                    title=f"{court_name} {case_number} {case_name}" if case_number else case_name,
                    content=content or f"사건번호: {case_number}\n선고일자: {decision_date}\n법원: {court_name}",
                    doc_type="PRECEDENT",
                    source_url=f"https://www.law.go.kr/판례/{prec_id}" if prec_id else None,
                    metadata={
                        "prec_id": prec_id,
                        "case_name": case_name,
                        "case_number": case_number,
                        "court": court_name,
                        "decision_date": decision_date,
                        "case_type": case_type,
                        "judgment_type": judgment_type,
                    }
                )
                documents.append(doc)

        except httpx.RequestError as e:
            logger.error(f"API 요청 실패: {e}")
            raise

        return documents

    async def _fetch_precedent_detail(self, prec_id: str) -> str:
        """판례 본문 상세 조회"""
        params = {
            'OC': self.oc,
            'target': 'prec',
            'type': 'XML',
            'ID': prec_id,
        }

        try:
            response = await self._make_request(self.DETAIL_URL, params=params)

            if response.status_code != 200:
                return ""

            data = self._parse_xml_response(response.text)

            # 본문 내용 추출
            content_parts = []

            if data.get('판시사항'):
                content_parts.append(f"【판시사항】\n{data['판시사항']}")

            if data.get('판결요지'):
                content_parts.append(f"【판결요지】\n{data['판결요지']}")

            if data.get('참조조문'):
                content_parts.append(f"【참조조문】\n{data['참조조문']}")

            if data.get('참조판례'):
                content_parts.append(f"【참조판례】\n{data['참조판례']}")

            if data.get('판례내용'):
                content_parts.append(f"【판례내용】\n{data['판례내용']}")

            return "\n\n".join(content_parts)

        except Exception as e:
            logger.error(f"판례 상세 조회 실패: {prec_id}, {e}")
            return ""

    async def _generate_mock_precedents(
        self,
        filters: Dict[str, Any]
    ) -> List[CrawlDocument]:
        """Mock 판례 데이터 생성 (개발/테스트용)"""
        mock_precedents = [
            CrawlDocument(
                title="대법원 2024다12345 손해배상(기)",
                content="【판시사항】\n[1] 계약 체결 과정에서 신의성실의 원칙에 따른 "
                        "정보제공의무 위반으로 인한 손해배상책임의 성립 요건\n\n"
                        "【판결요지】\n[1] 계약을 체결하는 당사자는 신의성실의 원칙에 따라 "
                        "상대방이 합리적인 판단을 할 수 있도록 필요한 정보를 제공할 의무가 있다...",
                doc_type="PRECEDENT",
                source_url="https://www.law.go.kr/판례/12345",
                metadata={
                    "prec_id": "12345",
                    "case_number": "2024다12345",
                    "court": "대법원",
                    "decision_date": "2024-10-15",
                    "case_type": "민사"
                }
            ),
        ]
        await asyncio.sleep(0.5)
        return mock_precedents


class StatuteCrawler(BaseCrawler):
    """
    법령 크롤러

    국가법령정보센터 API를 통해 법령 데이터를 수집합니다.

    API Endpoints:
    - 목록 조회: http://www.law.go.kr/DRF/lawSearch.do?target=law
    - 본문 조회: http://www.law.go.kr/DRF/lawService.do?target=law
    """

    LIST_URL = f"{LAW_GO_KR_API_BASE}/lawSearch.do"
    DETAIL_URL = f"{LAW_GO_KR_API_BASE}/lawService.do"

    def __init__(self, base_url: str = None, config: Dict[str, Any] = None):
        super().__init__(config)
        self.base_url = base_url or self.LIST_URL

    async def crawl(
        self,
        filters: Dict[str, Any] = None
    ) -> CrawlResult:
        """
        법령 크롤링 실행

        Args:
            filters: 필터 조건
                - keyword: 검색 키워드
                - law_type: 법령 종류 (법률, 시행령, 시행규칙 등)
                - ministry: 소관부처
                - display: 결과 개수 (기본 20, 최대 100)
                - page: 페이지 번호
                - sort: 정렬옵션 (lasc/ldes/dasc/ddes/nasc/ndes/efasc/efdes)

        Returns:
            CrawlResult: 크롤링 결과
        """
        filters = filters or {}
        documents = []
        errors = []

        try:
            logger.info(f"법령 크롤링 시작: filters={filters}")

            # Mock 모드 체크
            if self.config.get('use_mock', False):
                documents = await self._generate_mock_statutes(filters)
            else:
                documents = await self._fetch_statutes(filters)

            logger.info(f"법령 크롤링 완료: {len(documents)}건 수집")

            return CrawlResult(
                success=True,
                documents_collected=len(documents),
                errors=errors,
                metadata={
                    'source': 'STATUTE_API',
                    'api_base': self.LIST_URL,
                    'filters': filters,
                    'documents': [doc.model_dump() for doc in documents[:10]]
                }
            )

        except Exception as e:
            logger.error(f"법령 크롤링 실패: {e}")
            errors.append(str(e))
            return CrawlResult(
                success=False,
                documents_collected=0,
                errors=errors,
                metadata={'error': str(e)}
            )

    async def _fetch_statutes(
        self,
        filters: Dict[str, Any]
    ) -> List[CrawlDocument]:
        """국가법령정보센터 API에서 법령 수집"""
        documents = []

        # API 파라미터 구성
        params = {
            'OC': self.oc,
            'target': 'law',
            'type': 'XML',
            'display': filters.get('display', 20),
            'page': filters.get('page', 1),
        }

        # 검색 키워드
        if filters.get('keyword'):
            params['query'] = filters['keyword']
            params['search'] = filters.get('search_type', 1)  # 1=법령명, 2=본문

        # 소관부처 필터
        if filters.get('ministry'):
            params['org'] = filters['ministry']

        # 법령종류 필터
        if filters.get('law_type'):
            params['knd'] = filters['law_type']

        # 시행일자 범위
        if filters.get('start_date') or filters.get('end_date'):
            start = filters.get('start_date', '').replace('-', '')
            end = filters.get('end_date', '').replace('-', '')
            if start and end:
                params['efYd'] = f"{start}~{end}"
            elif start:
                params['efYd'] = f"{start}~"
            elif end:
                params['efYd'] = f"~{end}"

        # 정렬
        if filters.get('sort'):
            params['sort'] = filters['sort']
        else:
            params['sort'] = 'lasc'  # 법령명 오름차순 기본

        logger.info(f"법령 목록 API 호출: {self.LIST_URL}, params={params}")

        try:
            response = await self._make_request(self.LIST_URL, params=params)

            if response.status_code != 200:
                logger.error(f"API 응답 오류: {response.status_code}")
                return documents

            # XML 파싱
            data = self._parse_xml_response(response.text)

            # 검색 결과 추출
            total_cnt = data.get('totalCnt', 0)
            logger.info(f"법령 검색 결과: 총 {total_cnt}건")

            # 법령 목록 처리
            law_list = data.get('law', [])
            if not isinstance(law_list, list):
                law_list = [law_list] if law_list else []

            for law in law_list:
                if not law:
                    continue

                law_id = law.get('법령일련번호', '') or law.get('법령ID', '')
                law_mst = law.get('법령MST', '')
                law_name = law.get('법령명한글', '') or law.get('법령명', '')
                promulgation_date = law.get('공포일자', '')
                enforcement_date = law.get('시행일자', '')
                ministry = law.get('소관부처명', '')
                law_type = law.get('법령종류', '')

                # 본문 가져오기 (상세 조회)
                content = ""
                if law_mst and filters.get('fetch_content', False):
                    content = await self._fetch_statute_detail(law_mst)

                doc = CrawlDocument(
                    title=law_name,
                    content=content or f"법령명: {law_name}\n시행일자: {enforcement_date}\n소관부처: {ministry}",
                    doc_type="STATUTE",
                    source_url=f"https://www.law.go.kr/법령/{law_name}" if law_name else None,
                    metadata={
                        "law_id": law_id,
                        "law_mst": law_mst,
                        "law_name": law_name,
                        "law_type": law_type,
                        "ministry": ministry,
                        "promulgation_date": promulgation_date,
                        "enforcement_date": enforcement_date,
                    }
                )
                documents.append(doc)

        except httpx.RequestError as e:
            logger.error(f"API 요청 실패: {e}")
            raise

        return documents

    async def _fetch_statute_detail(self, law_mst: str) -> str:
        """법령 본문 상세 조회"""
        params = {
            'OC': self.oc,
            'target': 'law',
            'type': 'XML',
            'MST': law_mst,
        }

        try:
            response = await self._make_request(self.DETAIL_URL, params=params)

            if response.status_code != 200:
                return ""

            data = self._parse_xml_response(response.text)

            # 조문 내용 추출
            content_parts = []

            # 기본 정보
            if data.get('기본정보'):
                basic = data['기본정보']
                if basic.get('법령명_한글'):
                    content_parts.append(f"【법령명】{basic['법령명_한글']}")

            # 조문 목록
            articles = data.get('조문', [])
            if not isinstance(articles, list):
                articles = [articles] if articles else []

            for article in articles[:50]:  # 최대 50개 조문
                if not article:
                    continue
                article_no = article.get('조문번호', '')
                article_title = article.get('조문제목', '')
                article_content = article.get('조문내용', '')

                if article_content:
                    header = f"제{article_no}조" if article_no else ""
                    if article_title:
                        header += f"({article_title})"
                    content_parts.append(f"{header}\n{article_content}")

            return "\n\n".join(content_parts)

        except Exception as e:
            logger.error(f"법령 상세 조회 실패: {law_mst}, {e}")
            return ""

    async def _generate_mock_statutes(
        self,
        filters: Dict[str, Any]
    ) -> List[CrawlDocument]:
        """Mock 법령 데이터 생성 (개발/테스트용)"""
        mock_statutes = [
            CrawlDocument(
                title="민법",
                content="제1조(법원) 민사에 관하여 법률에 규정이 없으면 관습법에 의하고 "
                        "관습법이 없으면 조리에 의한다.\n\n"
                        "제2조(신의성실) ① 권리의 행사와 의무의 이행은 신의에 좇아 성실히 하여야 한다.\n"
                        "② 권리는 남용하지 못한다.",
                doc_type="STATUTE",
                source_url="https://www.law.go.kr/법령/민법",
                metadata={
                    "law_id": "001000",
                    "law_type": "법률",
                    "ministry": "법무부",
                    "enforcement_date": "1960-01-01"
                }
            ),
        ]
        await asyncio.sleep(0.5)
        return mock_statutes


class WebCrawler(BaseCrawler):
    """
    웹 크롤러

    일반 웹 페이지에서 법률 관련 데이터를 수집합니다.
    """

    def __init__(self, base_url: str, config: Dict[str, Any] = None):
        super().__init__(config)
        self.base_url = base_url

    async def crawl(
        self,
        filters: Dict[str, Any] = None
    ) -> CrawlResult:
        """
        웹 크롤링 실행

        Args:
            filters: 필터 조건
                - url_pattern: URL 패턴
                - content_selector: 콘텐츠 CSS 선택자

        Returns:
            CrawlResult: 크롤링 결과
        """
        filters = filters or {}
        errors = []

        try:
            logger.info(f"웹 크롤링 시작: base_url={self.base_url}, filters={filters}")

            response = await self._make_request(self.base_url)

            if response.status_code == 200:
                content = response.text[:5000]

                return CrawlResult(
                    success=True,
                    documents_collected=1,
                    errors=[],
                    metadata={
                        'source': 'WEB_CRAWL',
                        'base_url': self.base_url,
                        'content_length': len(content)
                    }
                )
            else:
                errors.append(f"HTTP {response.status_code}")

        except Exception as e:
            logger.error(f"웹 크롤링 실패: {e}")
            errors.append(str(e))

        return CrawlResult(
            success=False,
            documents_collected=0,
            errors=errors,
            metadata={'error': errors[0] if errors else 'Unknown error'}
        )


def get_crawler(
    source_type: str,
    base_url: str = None,
    config: Dict[str, Any] = None
) -> BaseCrawler:
    """
    소스 타입에 따른 크롤러 인스턴스 반환

    Args:
        source_type: 소스 타입 (COURT_API, STATUTE_API, WEB_CRAWL)
        base_url: 기본 URL
        config: 크롤러 설정
            - oc: API 사용자 키 (환경변수 LAW_GO_KR_OC에서 로드)
            - use_mock: Mock 데이터 사용 여부 (기본값: False)
            - timeout: 요청 타임아웃 (기본값: 30초)

    Returns:
        BaseCrawler: 크롤러 인스턴스
    """
    crawlers = {
        'COURT_API': CourtPrecedentCrawler,
        'STATUTE_API': StatuteCrawler,
        'WEB_CRAWL': WebCrawler,
    }

    crawler_class = crawlers.get(source_type)
    if not crawler_class:
        raise ValueError(f"지원하지 않는 소스 타입: {source_type}")

    return crawler_class(base_url=base_url, config=config)
