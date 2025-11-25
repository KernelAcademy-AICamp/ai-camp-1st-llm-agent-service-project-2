"""
Crawler Service

법률 데이터 크롤링 서비스
- 대법원 판례 API 연동
- 법령 API 연동
- 웹 크롤링
"""
import asyncio
import logging
import httpx
from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

logger = logging.getLogger(__name__)


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


class CourtPrecedentCrawler(BaseCrawler):
    """
    대법원 판례 크롤러

    대법원 판례 API를 통해 판례 데이터를 수집합니다.
    """

    # 대법원 API 기본 URL (실제 API URL로 변경 필요)
    DEFAULT_BASE_URL = "https://www.law.go.kr/DRF/lawService.do"

    def __init__(self, base_url: str = None, config: Dict[str, Any] = None):
        super().__init__(config)
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.api_key = config.get('api_key') if config else None

    async def crawl(
        self,
        filters: Dict[str, Any] = None
    ) -> CrawlResult:
        """
        판례 크롤링 실행

        Args:
            filters: 필터 조건
                - start_date: 시작 날짜 (YYYY-MM-DD)
                - end_date: 종료 날짜 (YYYY-MM-DD)
                - case_type: 사건 유형 (민사, 형사 등)
                - keyword: 검색 키워드

        Returns:
            CrawlResult: 크롤링 결과
        """
        filters = filters or {}
        documents = []
        errors = []

        try:
            logger.info(f"대법원 판례 크롤링 시작: filters={filters}")

            # 실제 API 연동 대신 Mock 데이터 생성 (개발용)
            if self.config.get('use_mock', True):
                documents = await self._generate_mock_precedents(filters)
            else:
                documents = await self._fetch_real_precedents(filters)

            logger.info(f"대법원 판례 크롤링 완료: {len(documents)}건 수집")

            return CrawlResult(
                success=True,
                documents_collected=len(documents),
                errors=errors,
                metadata={
                    'source': 'COURT_API',
                    'filters': filters,
                    'documents': [doc.model_dump() for doc in documents[:10]]  # 샘플 10개
                }
            )

        except Exception as e:
            logger.error(f"대법원 판례 크롤링 실패: {e}")
            errors.append(str(e))
            return CrawlResult(
                success=False,
                documents_collected=0,
                errors=errors,
                metadata={'error': str(e)}
            )

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
                source_url="https://www.law.go.kr/precInfoP.do?precSeq=12345",
                metadata={
                    "case_number": "2024다12345",
                    "court": "대법원",
                    "decision_date": "2024-10-15",
                    "case_type": "민사"
                }
            ),
            CrawlDocument(
                title="대법원 2024도5678 사기",
                content="【판시사항】\n[1] 사기죄에서 기망행위의 의미 및 "
                        "부작위에 의한 기망행위가 성립하기 위한 요건\n\n"
                        "【판결요지】\n[1] 사기죄의 요건인 기망은 널리 재산상 거래관계에서 "
                        "서로 지켜야 할 신의와 성실의 의무를 저버리는 모든 적극적·소극적 행위를 말한다...",
                doc_type="PRECEDENT",
                source_url="https://www.law.go.kr/precInfoP.do?precSeq=56789",
                metadata={
                    "case_number": "2024도5678",
                    "court": "대법원",
                    "decision_date": "2024-09-20",
                    "case_type": "형사"
                }
            ),
            CrawlDocument(
                title="대법원 2024두9012 세금부과처분취소",
                content="【판시사항】\n[1] 과세처분의 적법성 판단 기준 시점 및 "
                        "처분 후 사정변경의 고려 여부\n\n"
                        "【판결요지】\n[1] 과세처분의 적법 여부는 특별한 사정이 없는 한 "
                        "그 처분 당시를 기준으로 판단하여야 한다...",
                doc_type="PRECEDENT",
                source_url="https://www.law.go.kr/precInfoP.do?precSeq=90123",
                metadata={
                    "case_number": "2024두9012",
                    "court": "대법원",
                    "decision_date": "2024-08-30",
                    "case_type": "행정"
                }
            ),
        ]

        # 필터 적용
        case_type_filter = filters.get('case_type')
        if case_type_filter:
            mock_precedents = [
                p for p in mock_precedents
                if p.metadata.get('case_type') == case_type_filter
            ]

        # 지연 시뮬레이션
        await asyncio.sleep(1)

        return mock_precedents

    async def _fetch_real_precedents(
        self,
        filters: Dict[str, Any]
    ) -> List[CrawlDocument]:
        """실제 대법원 API에서 판례 수집"""
        # 실제 API 구현 시 사용
        # 현재는 빈 리스트 반환
        logger.warning("실제 API 연동이 구현되지 않았습니다. Mock 데이터 사용을 권장합니다.")
        return []


class StatuteCrawler(BaseCrawler):
    """
    법령 크롤러

    국가법령정보센터 API를 통해 법령 데이터를 수집합니다.
    """

    # 국가법령정보센터 API 기본 URL
    DEFAULT_BASE_URL = "https://www.law.go.kr/DRF/lawService.do"

    def __init__(self, base_url: str = None, config: Dict[str, Any] = None):
        super().__init__(config)
        self.base_url = base_url or self.DEFAULT_BASE_URL
        self.api_key = config.get('api_key') if config else None

    async def crawl(
        self,
        filters: Dict[str, Any] = None
    ) -> CrawlResult:
        """
        법령 크롤링 실행

        Args:
            filters: 필터 조건
                - law_type: 법령 종류 (법률, 시행령, 시행규칙 등)
                - keyword: 검색 키워드
                - ministry: 소관부처

        Returns:
            CrawlResult: 크롤링 결과
        """
        filters = filters or {}
        documents = []
        errors = []

        try:
            logger.info(f"법령 크롤링 시작: filters={filters}")

            # Mock 데이터 생성 (개발용)
            if self.config.get('use_mock', True):
                documents = await self._generate_mock_statutes(filters)
            else:
                documents = await self._fetch_real_statutes(filters)

            logger.info(f"법령 크롤링 완료: {len(documents)}건 수집")

            return CrawlResult(
                success=True,
                documents_collected=len(documents),
                errors=errors,
                metadata={
                    'source': 'STATUTE_API',
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
                        "② 권리는 남용하지 못한다...",
                doc_type="STATUTE",
                source_url="https://www.law.go.kr/법령/민법",
                metadata={
                    "law_id": "001000",
                    "law_type": "법률",
                    "ministry": "법무부",
                    "enforcement_date": "1960-01-01"
                }
            ),
            CrawlDocument(
                title="형법",
                content="제1조(범죄의 성립과 처벌) ① 범죄의 성립과 처벌은 행위시의 법률에 의한다.\n"
                        "② 범죄 후 법률이 변경되어 그 행위가 범죄를 구성하지 아니하거나 "
                        "형이 구법보다 가벼운 때에는 신법에 의한다...",
                doc_type="STATUTE",
                source_url="https://www.law.go.kr/법령/형법",
                metadata={
                    "law_id": "002000",
                    "law_type": "법률",
                    "ministry": "법무부",
                    "enforcement_date": "1953-10-03"
                }
            ),
            CrawlDocument(
                title="상법",
                content="제1조(상사에 관한 법원) 상사에 관하여 본법에 규정이 없으면 "
                        "상관습법에 의하고 상관습법이 없으면 민법의 규정에 의한다.\n\n"
                        "제2조(상행위의 영리성) 상행위는 영리를 목적으로 한다...",
                doc_type="STATUTE",
                source_url="https://www.law.go.kr/법령/상법",
                metadata={
                    "law_id": "003000",
                    "law_type": "법률",
                    "ministry": "법무부",
                    "enforcement_date": "1963-01-01"
                }
            ),
        ]

        # 지연 시뮬레이션
        await asyncio.sleep(0.5)

        return mock_statutes

    async def _fetch_real_statutes(
        self,
        filters: Dict[str, Any]
    ) -> List[CrawlDocument]:
        """실제 법령 API에서 데이터 수집"""
        logger.warning("실제 API 연동이 구현되지 않았습니다. Mock 데이터 사용을 권장합니다.")
        return []


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

            # 기본 구현: 단일 페이지 수집
            response = await self._make_request(self.base_url)

            if response.status_code == 200:
                # 간단한 텍스트 추출 (실제 구현 시 BeautifulSoup 등 사용)
                content = response.text[:5000]  # 첫 5000자만 추출

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
