"""
External API Tools

Phase 4 - Week 13: External API Tools for MCP

외부 API 호출을 위한 MCP Tools:
- fetch_court_api: 대법원 판례 API
- fetch_statute_api: 법령 API
- parse_legal_document: 법률 문서 파싱
- validate_document_structure: 문서 구조 검증

참고: LANGGRAPH_FASTMCP_INTEGRATION_PLAN.md
"""
import logging
import os
import httpx
import asyncio
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional
from datetime import datetime
from functools import wraps

logger = logging.getLogger(__name__)

# =============================================================================
# API Configuration
# =============================================================================

# 국가법령정보 Open API 기본 설정
LAW_GO_KR_API_BASE = "http://www.law.go.kr/DRF"
DEFAULT_OC = os.getenv("LAW_GO_KR_OC", "")

# 타임아웃 및 재시도 설정
DEFAULT_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds


# =============================================================================
# Retry Decorator
# =============================================================================

def with_retry(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
    """Retry decorator for API calls"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (httpx.RequestError, httpx.TimeoutException) as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {e}")
                except Exception as e:
                    # Non-retryable errors
                    logger.error(f"Non-retryable error in {func.__name__}: {e}")
                    raise
            raise last_exception
        return wrapper
    return decorator


# =============================================================================
# XML Parsing Utilities
# =============================================================================

def parse_xml_response(xml_text: str) -> Dict[str, Any]:
    """XML 응답을 딕셔너리로 파싱"""
    try:
        root = ET.fromstring(xml_text)
        return element_to_dict(root)
    except ET.ParseError as e:
        logger.error(f"XML 파싱 오류: {e}")
        return {"error": str(e), "raw_text": xml_text[:500]}


def element_to_dict(element: ET.Element) -> Dict[str, Any]:
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
            child_data = element_to_dict(child)
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


# =============================================================================
# External API Tools
# =============================================================================

@with_retry()
async def fetch_court_api(
    case_number: Optional[str] = None,
    keyword: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    court: Optional[str] = None,
    page: int = 1,
    display: int = 20,
    fetch_content: bool = True,
    oc: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """
    대법원 판례 API 호출

    국가법령정보센터 판례 API를 통해 판례 데이터를 조회합니다.

    Args:
        case_number: 사건번호 (예: "2020도1234")
        keyword: 검색 키워드
        start_date: 선고일자 시작 (YYYY-MM-DD)
        end_date: 선고일자 종료 (YYYY-MM-DD)
        court: 법원명 (예: "대법원")
        page: 페이지 번호 (기본값: 1)
        display: 결과 개수 (기본값: 20, 최대: 100)
        fetch_content: 본문 상세 조회 여부 (기본값: True)
        oc: API 사용자 키 (환경변수 LAW_GO_KR_OC에서 로드)
        timeout: 요청 타임아웃 (초)

    Returns:
        {
            "success": bool,
            "total_count": int,
            "precedents": [
                {
                    "prec_id": str,
                    "case_number": str,
                    "case_name": str,
                    "court": str,
                    "decision_date": str,
                    "case_type": str,
                    "judgment_type": str,
                    "content": str,
                    "source_url": str
                }
            ],
            "metadata": {...}
        }
    """
    api_key = oc or DEFAULT_OC
    if not api_key:
        return {
            "success": False,
            "error": "API key (OC) not configured. Set LAW_GO_KR_OC environment variable.",
            "precedents": [],
            "total_count": 0
        }

    list_url = f"{LAW_GO_KR_API_BASE}/lawSearch.do"
    detail_url = f"{LAW_GO_KR_API_BASE}/lawService.do"

    # API 파라미터 구성
    params = {
        'OC': api_key,
        'target': 'prec',
        'type': 'XML',
        'display': min(display, 100),
        'page': page,
    }

    # 검색 조건 추가
    if keyword:
        params['query'] = keyword
        params['search'] = 1  # 1=판례명, 2=본문

    if court:
        params['curt'] = court

    if case_number:
        params['nb'] = case_number

    # 선고일자 범위
    if start_date or end_date:
        start = (start_date or '').replace('-', '')
        end = (end_date or '').replace('-', '')
        if start and end:
            params['prncYd'] = f"{start}~{end}"
        elif start:
            params['prncYd'] = f"{start}~"
        elif end:
            params['prncYd'] = f"~{end}"

    logger.info(f"Calling court API: url={list_url}, params={params}")

    precedents = []

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 목록 조회
            response = await client.get(list_url, params=params)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"API returned status code {response.status_code}",
                    "precedents": [],
                    "total_count": 0
                }

            # XML 파싱
            data = parse_xml_response(response.text)

            if "error" in data:
                return {
                    "success": False,
                    "error": data.get("error"),
                    "precedents": [],
                    "total_count": 0,
                    "metadata": data
                }

            total_count = int(data.get('totalCnt', 0) if isinstance(data.get('totalCnt'), str) else data.get('totalCnt', 0))
            logger.info(f"Court API returned {total_count} total results")

            # 판례 목록 처리
            prec_list = data.get('prec', [])
            if not isinstance(prec_list, list):
                prec_list = [prec_list] if prec_list else []

            for prec in prec_list:
                if not prec:
                    continue

                prec_id = prec.get('판례일련번호', '')
                case_name = prec.get('사건명', '')
                case_num = prec.get('사건번호', '')
                decision_date = prec.get('선고일자', '')
                court_name = prec.get('법원명', '')
                case_type = prec.get('사건종류명', '')
                judgment_type = prec.get('판결유형', '')

                # 본문 조회 (선택적)
                content = ""
                if prec_id and fetch_content:
                    content = await _fetch_precedent_detail(
                        client, detail_url, prec_id, api_key, timeout
                    )

                precedent = {
                    "prec_id": prec_id,
                    "case_number": case_num,
                    "case_name": case_name,
                    "court": court_name,
                    "decision_date": decision_date,
                    "case_type": case_type,
                    "judgment_type": judgment_type,
                    "content": content or f"사건번호: {case_num}\n선고일자: {decision_date}\n법원: {court_name}",
                    "source_url": f"https://www.law.go.kr/판례/{prec_id}" if prec_id else None
                }
                precedents.append(precedent)

            return {
                "success": True,
                "total_count": total_count,
                "precedents": precedents,
                "metadata": {
                    "api_url": list_url,
                    "query_params": params,
                    "fetched_count": len(precedents),
                    "timestamp": datetime.now().isoformat()
                }
            }

    except httpx.TimeoutException as e:
        logger.error(f"Court API timeout: {e}")
        raise  # Will be caught by retry decorator
    except httpx.RequestError as e:
        logger.error(f"Court API request error: {e}")
        raise  # Will be caught by retry decorator
    except Exception as e:
        logger.error(f"Court API unexpected error: {e}")
        return {
            "success": False,
            "error": str(e),
            "precedents": [],
            "total_count": 0
        }


async def _fetch_precedent_detail(
    client: httpx.AsyncClient,
    detail_url: str,
    prec_id: str,
    api_key: str,
    timeout: int
) -> str:
    """판례 본문 상세 조회"""
    params = {
        'OC': api_key,
        'target': 'prec',
        'type': 'XML',
        'ID': prec_id,
    }

    try:
        response = await client.get(detail_url, params=params, timeout=timeout)

        if response.status_code != 200:
            return ""

        data = parse_xml_response(response.text)

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
        logger.warning(f"Failed to fetch precedent detail {prec_id}: {e}")
        return ""


@with_retry()
async def fetch_statute_api(
    law_code: Optional[str] = None,
    keyword: Optional[str] = None,
    law_type: Optional[str] = None,
    ministry: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    display: int = 20,
    fetch_content: bool = False,
    oc: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT
) -> Dict[str, Any]:
    """
    법령 API 호출

    국가법령정보센터 API를 통해 법령 데이터를 조회합니다.

    Args:
        law_code: 법령 MST 코드
        keyword: 검색 키워드
        law_type: 법령 종류 (법률, 시행령, 시행규칙 등)
        ministry: 소관부처
        start_date: 시행일자 시작 (YYYY-MM-DD)
        end_date: 시행일자 종료 (YYYY-MM-DD)
        page: 페이지 번호 (기본값: 1)
        display: 결과 개수 (기본값: 20, 최대: 100)
        fetch_content: 본문 상세 조회 여부 (기본값: False)
        oc: API 사용자 키
        timeout: 요청 타임아웃 (초)

    Returns:
        {
            "success": bool,
            "total_count": int,
            "statutes": [
                {
                    "law_id": str,
                    "law_mst": str,
                    "law_name": str,
                    "law_type": str,
                    "ministry": str,
                    "promulgation_date": str,
                    "enforcement_date": str,
                    "content": str,
                    "source_url": str
                }
            ],
            "metadata": {...}
        }
    """
    api_key = oc or DEFAULT_OC
    if not api_key:
        return {
            "success": False,
            "error": "API key (OC) not configured. Set LAW_GO_KR_OC environment variable.",
            "statutes": [],
            "total_count": 0
        }

    list_url = f"{LAW_GO_KR_API_BASE}/lawSearch.do"
    detail_url = f"{LAW_GO_KR_API_BASE}/lawService.do"

    # API 파라미터 구성
    params = {
        'OC': api_key,
        'target': 'law',
        'type': 'XML',
        'display': min(display, 100),
        'page': page,
        'sort': 'lasc',  # 법령명 오름차순 기본
    }

    # 검색 조건 추가
    if keyword:
        params['query'] = keyword
        params['search'] = 1  # 1=법령명, 2=본문

    if ministry:
        params['org'] = ministry

    if law_type:
        params['knd'] = law_type

    # 시행일자 범위
    if start_date or end_date:
        start = (start_date or '').replace('-', '')
        end = (end_date or '').replace('-', '')
        if start and end:
            params['efYd'] = f"{start}~{end}"
        elif start:
            params['efYd'] = f"{start}~"
        elif end:
            params['efYd'] = f"~{end}"

    logger.info(f"Calling statute API: url={list_url}, params={params}")

    statutes = []

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            # 목록 조회
            response = await client.get(list_url, params=params)

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"API returned status code {response.status_code}",
                    "statutes": [],
                    "total_count": 0
                }

            # XML 파싱
            data = parse_xml_response(response.text)

            if "error" in data:
                return {
                    "success": False,
                    "error": data.get("error"),
                    "statutes": [],
                    "total_count": 0,
                    "metadata": data
                }

            total_count = int(data.get('totalCnt', 0) if isinstance(data.get('totalCnt'), str) else data.get('totalCnt', 0))
            logger.info(f"Statute API returned {total_count} total results")

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
                law_ministry = law.get('소관부처명', '')
                law_type_val = law.get('법령종류', '')

                # 본문 조회 (선택적)
                content = ""
                if law_mst and fetch_content:
                    content = await _fetch_statute_detail(
                        client, detail_url, law_mst, api_key, timeout
                    )

                statute = {
                    "law_id": law_id,
                    "law_mst": law_mst,
                    "law_name": law_name,
                    "law_type": law_type_val,
                    "ministry": law_ministry,
                    "promulgation_date": promulgation_date,
                    "enforcement_date": enforcement_date,
                    "content": content or f"법령명: {law_name}\n시행일자: {enforcement_date}\n소관부처: {law_ministry}",
                    "source_url": f"https://www.law.go.kr/법령/{law_name}" if law_name else None
                }
                statutes.append(statute)

            return {
                "success": True,
                "total_count": total_count,
                "statutes": statutes,
                "metadata": {
                    "api_url": list_url,
                    "query_params": params,
                    "fetched_count": len(statutes),
                    "timestamp": datetime.now().isoformat()
                }
            }

    except httpx.TimeoutException as e:
        logger.error(f"Statute API timeout: {e}")
        raise  # Will be caught by retry decorator
    except httpx.RequestError as e:
        logger.error(f"Statute API request error: {e}")
        raise  # Will be caught by retry decorator
    except Exception as e:
        logger.error(f"Statute API unexpected error: {e}")
        return {
            "success": False,
            "error": str(e),
            "statutes": [],
            "total_count": 0
        }


async def _fetch_statute_detail(
    client: httpx.AsyncClient,
    detail_url: str,
    law_mst: str,
    api_key: str,
    timeout: int
) -> str:
    """법령 본문 상세 조회"""
    params = {
        'OC': api_key,
        'target': 'law',
        'type': 'XML',
        'MST': law_mst,
    }

    try:
        response = await client.get(detail_url, params=params, timeout=timeout)

        if response.status_code != 200:
            return ""

        data = parse_xml_response(response.text)

        # 조문 내용 추출
        content_parts = []

        # 기본 정보
        if data.get('기본정보'):
            basic = data['기본정보']
            if isinstance(basic, dict) and basic.get('법령명_한글'):
                content_parts.append(f"【법령명】{basic['법령명_한글']}")

        # 조문 목록
        articles = data.get('조문', [])
        if not isinstance(articles, list):
            articles = [articles] if articles else []

        for article in articles[:50]:  # 최대 50개 조문
            if not article or not isinstance(article, dict):
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
        logger.warning(f"Failed to fetch statute detail {law_mst}: {e}")
        return ""


async def parse_legal_document(
    content: str,
    doc_type: str = "unknown"
) -> Dict[str, Any]:
    """
    법률 문서 파싱

    법률 문서의 구조를 분석하고 주요 섹션을 추출합니다.

    Args:
        content: 문서 내용 (HTML 또는 텍스트)
        doc_type: 문서 타입 ("precedent", "statute", "contract", "unknown")

    Returns:
        {
            "success": bool,
            "doc_type": str,
            "title": str,
            "sections": [
                {
                    "name": str,
                    "content": str,
                    "order": int
                }
            ],
            "metadata": {...}
        }
    """
    if not content:
        return {
            "success": False,
            "error": "Empty content provided",
            "doc_type": doc_type,
            "sections": []
        }

    sections = []
    title = ""

    try:
        # HTML 태그 제거 (간단한 방식)
        clean_content = content
        if "<" in content and ">" in content:
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(content, 'html.parser')
                clean_content = soup.get_text(separator='\n')
            except ImportError:
                # BeautifulSoup 없으면 간단한 태그 제거
                import re
                clean_content = re.sub(r'<[^>]+>', '', content)

        lines = clean_content.strip().split('\n')

        # 판례 문서 파싱
        if doc_type == "precedent" or "【판시사항】" in content or "【판결요지】" in content:
            current_section = None
            current_content = []

            section_markers = [
                "【판시사항】", "【판결요지】", "【참조조문】",
                "【참조판례】", "【판례내용】", "【전문】"
            ]

            for line in lines:
                stripped = line.strip()

                # 제목 추출 (첫 번째 의미 있는 줄)
                if not title and stripped and not any(marker in stripped for marker in section_markers):
                    title = stripped

                # 섹션 시작 확인
                found_marker = None
                for marker in section_markers:
                    if marker in stripped:
                        found_marker = marker
                        break

                if found_marker:
                    # 이전 섹션 저장
                    if current_section:
                        sections.append({
                            "name": current_section,
                            "content": "\n".join(current_content).strip(),
                            "order": len(sections)
                        })
                    current_section = found_marker.replace("【", "").replace("】", "")
                    current_content = [stripped.replace(found_marker, "").strip()]
                elif current_section:
                    current_content.append(stripped)

            # 마지막 섹션 저장
            if current_section:
                sections.append({
                    "name": current_section,
                    "content": "\n".join(current_content).strip(),
                    "order": len(sections)
                })

        # 법령 문서 파싱
        elif doc_type == "statute" or "제1조" in content or "제2조" in content:
            import re
            article_pattern = re.compile(r'^제(\d+)조(?:\(([^)]+)\))?')

            current_article = None
            current_content = []

            for line in lines:
                stripped = line.strip()

                # 법령명 추출
                if not title and stripped and not article_pattern.match(stripped):
                    if "법" in stripped or "령" in stripped or "규칙" in stripped:
                        title = stripped

                # 조문 시작 확인
                match = article_pattern.match(stripped)
                if match:
                    # 이전 조문 저장
                    if current_article:
                        sections.append({
                            "name": current_article,
                            "content": "\n".join(current_content).strip(),
                            "order": len(sections)
                        })
                    article_num = match.group(1)
                    article_title = match.group(2) or ""
                    current_article = f"제{article_num}조" + (f"({article_title})" if article_title else "")
                    current_content = [stripped]
                elif current_article:
                    current_content.append(stripped)

            # 마지막 조문 저장
            if current_article:
                sections.append({
                    "name": current_article,
                    "content": "\n".join(current_content).strip(),
                    "order": len(sections)
                })

        # 일반 문서 파싱
        else:
            # 단순히 줄바꿈으로 분리된 단락을 섹션으로 처리
            paragraphs = clean_content.split('\n\n')
            for i, para in enumerate(paragraphs):
                if para.strip():
                    if i == 0 and not title:
                        title = para.strip()[:100]  # 첫 100자를 제목으로
                    sections.append({
                        "name": f"Section {i + 1}",
                        "content": para.strip(),
                        "order": i
                    })

        return {
            "success": True,
            "doc_type": doc_type,
            "title": title,
            "sections": sections,
            "metadata": {
                "total_sections": len(sections),
                "content_length": len(content),
                "parsed_at": datetime.now().isoformat()
            }
        }

    except Exception as e:
        logger.error(f"Document parsing error: {e}")
        return {
            "success": False,
            "error": str(e),
            "doc_type": doc_type,
            "title": title,
            "sections": sections
        }


async def validate_document_structure(
    data: Dict[str, Any],
    doc_type: str = "precedent"
) -> Dict[str, Any]:
    """
    문서 구조 검증

    법률 문서가 필수 필드를 포함하고 있는지 검증합니다.

    Args:
        data: 검증할 문서 데이터
        doc_type: 문서 타입 ("precedent", "statute", "contract")

    Returns:
        {
            "valid": bool,
            "doc_type": str,
            "missing_fields": [...],
            "warnings": [...],
            "metadata": {...}
        }
    """
    # 문서 타입별 필수 필드 정의
    required_fields = {
        "precedent": ["case_number", "title", "content"],
        "statute": ["law_name", "content"],
        "contract": ["title", "content", "parties"],
        "document": ["title", "content"]
    }

    # 문서 타입별 권장 필드 정의
    recommended_fields = {
        "precedent": ["court", "decision_date", "case_type", "prec_id"],
        "statute": ["law_type", "ministry", "enforcement_date"],
        "contract": ["date", "effective_date"],
        "document": ["doc_type", "created_at"]
    }

    fields_to_check = required_fields.get(doc_type, required_fields["document"])
    optional_fields = recommended_fields.get(doc_type, recommended_fields["document"])

    missing_fields = []
    warnings = []

    # 필수 필드 검증
    for field in fields_to_check:
        if field not in data or not data[field]:
            missing_fields.append(field)

    # 권장 필드 검증
    for field in optional_fields:
        if field not in data or not data[field]:
            warnings.append(f"Missing recommended field: {field}")

    # 내용 품질 검증
    content = data.get("content", "")
    if content:
        if len(content) < 50:
            warnings.append("Content is very short (< 50 characters)")
        if len(content) > 100000:
            warnings.append("Content is very long (> 100,000 characters)")

    # 제목 검증
    title = data.get("title", "") or data.get("case_number", "") or data.get("law_name", "")
    if title and len(title) > 500:
        warnings.append("Title is very long (> 500 characters)")

    is_valid = len(missing_fields) == 0

    return {
        "valid": is_valid,
        "doc_type": doc_type,
        "missing_fields": missing_fields,
        "warnings": warnings,
        "metadata": {
            "total_fields": len(data),
            "required_fields_count": len(fields_to_check),
            "missing_count": len(missing_fields),
            "warnings_count": len(warnings),
            "validated_at": datetime.now().isoformat()
        }
    }


# =============================================================================
# Export
# =============================================================================

__all__ = [
    "fetch_court_api",
    "fetch_statute_api",
    "parse_legal_document",
    "validate_document_structure",
]
