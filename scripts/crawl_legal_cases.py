"""
법제처 OpenAPI 크롤링 스크립트 (개선 버전)
교통사고 및 도로교통법 관련 판례/해석례 수집
"""

import requests
import json
import time
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from datetime import datetime
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# 설정
# ============================================================================
OC = "namwook1110"  # OpenAPI 키

# 교통사고/도로교통법 관련 확장 키워드
TRAFFIC_KEYWORDS = [
    # 기본 키워드
    "교통사고", "도로교통법", "차량", "자동차",

    # 위반 행위
    "음주운전", "무면허운전", "무면허", "신호위반",
    "속도위반", "과속", "중앙선침범", "중앙선", "차선위반",
    "안전거리미확보", "끼어들기", "난폭운전", "보복운전",
    "뺑소니", "도주", "사고후도주", "구호조치불이행",

    # 교통 관련 법규
    "교통사고처리특례법", "특정범죄가중처벌등에관한법률",
    "교통법규", "교통단속", "음주측정", "음주측정거부",

    # 운전/차량 관련
    "운전", "운전면허", "면허취소", "면허정지",
    "차량운행", "정차", "주차", "주정차위반",

    # 사고 유형
    "추돌사고", "접촉사고", "전복사고", "인명사고",
    "보행자", "횡단보도", "인도", "자전거도로",

    # 기타
    "교통체계", "도로", "고속도로", "자동차전용도로",
    "이륜차", "오토바이", "자전거", "전동킥보드"
]

# 연관성 판단을 위한 강한 키워드 (이것들이 있으면 높은 확률로 교통 관련)
STRONG_KEYWORDS = [
    "교통사고", "도로교통법", "음주운전", "뺑소니",
    "교통사고처리특례법", "무면허운전", "신호위반"
]

# 최대 페이지 수 (None이면 전체)
MAX_PAGES = 1  # 샘플 테스트용

# 상세 정보 조회 여부
FETCH_DETAILS = True

# API 요청 간격 (초)
REQUEST_DELAY = 0.5
DETAIL_REQUEST_DELAY = 0.3


# ============================================================================
# 데이터 클래스
# ============================================================================
@dataclass
class CaseMetadata:
    """판례 메타데이터"""
    case_number: str
    case_name: Optional[str]
    decision_date: Optional[str]
    court_name: Optional[str]
    case_id: str
    case_type: Optional[str]
    judgment_type: Optional[str]
    data_source: Optional[str]
    keyword: str


# ============================================================================
# 연관성 판단 함수
# ============================================================================
def is_traffic_related(case_data: Dict, threshold: int = 1) -> bool:
    """
    판례가 교통사고/도로교통법과 연관되어 있는지 판단

    Args:
        case_data: 판례 데이터
        threshold: 최소 매칭 키워드 수 (기본값: 1)

    Returns:
        연관성 여부
    """
    # 검색할 필드들
    search_fields = []

    # 기본 정보
    if "사건번호" in case_data:
        search_fields.append(case_data["사건번호"])
    if "법원명" in case_data:
        search_fields.append(case_data["법원명"])
    if "사건종류명" in case_data:
        search_fields.append(case_data["사건종류명"])

    # 상세 정보
    if "상세정보" in case_data:
        detail = case_data["상세정보"]

        if isinstance(detail, dict):
            # 판례 제목
            if "판례내용" in detail:
                content = detail["판례내용"]
                if isinstance(content, dict):
                    if "판시사항" in content:
                        search_fields.append(str(content["판시사항"]))
                    if "판결요지" in content:
                        search_fields.append(str(content["판결요지"]))
                    if "참조조문" in content:
                        search_fields.append(str(content["참조조문"]))
                elif isinstance(content, str):
                    search_fields.append(content)

            # 기타 필드
            for field in ["사건명", "사건내용", "참조조문", "판시사항"]:
                if field in detail:
                    search_fields.append(str(detail[field]))

    # 전체 텍스트 결합
    full_text = " ".join(search_fields).lower()

    # 키워드 매칭
    matched_keywords = []
    strong_match = False

    for keyword in TRAFFIC_KEYWORDS:
        if keyword.lower() in full_text:
            matched_keywords.append(keyword)

            # 강한 키워드 매칭 확인
            if keyword in STRONG_KEYWORDS:
                strong_match = True

    # 판단 로직
    # 1. 강한 키워드가 하나라도 있으면 연관 있음
    if strong_match:
        return True

    # 2. 일반 키워드가 threshold 이상이면 연관 있음
    if len(matched_keywords) >= threshold:
        return True

    return False


# ============================================================================
# API 함수
# ============================================================================
def get_case_list(keyword: str, page: int = 1, target: str = "prec") -> Optional[List[Dict]]:
    """
    판례/해석례 목록 조회

    Args:
        keyword: 검색 키워드
        page: 페이지 번호
        target: 검색 대상 (prec: 판례, expc: 해석례)

    Returns:
        판례 목록 또는 None
    """
    url = f"https://www.law.go.kr/DRF/lawSearch.do"
    params = {
        "OC": OC,
        "target": target,
        "query": keyword,
        "type": "JSON",
        "page": page
    }

    try:
        response = requests.get(url, params=params, timeout=30)

        if response.status_code != 200:
            logger.error(f"HTTP {response.status_code} 오류")
            return None

        if not response.text or response.text.strip() == "":
            return None

        data = response.json()

        # 판례 목록 추출
        if target == "prec":
            search_result = data.get("PrecSearch", {})
            return search_result.get("prec", [])
        elif target == "expc":
            search_result = data.get("ExpcSearch", {})
            return search_result.get("expc", [])

        return None

    except requests.exceptions.Timeout:
        logger.error(f"요청 타임아웃: {keyword}, page {page}")
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"요청 실패: {e}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패: {e}")
        return None


def get_case_detail(case_id: str, target: str = "prec") -> Optional[Dict]:
    """
    판례/해석례 상세 정보 조회

    Args:
        case_id: 판례/해석례 ID
        target: 검색 대상 (prec: 판례, expc: 해석례)

    Returns:
        상세 정보 또는 None
    """
    url = f"https://www.law.go.kr/DRF/lawService.do"
    params = {
        "OC": OC,
        "target": target,
        "ID": case_id,
        "type": "JSON"
    }

    try:
        response = requests.get(url, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()

            if target == "prec":
                return data.get("PrecService", data)
            elif target == "expc":
                return data.get("ExpcService", data)

        return None

    except Exception as e:
        logger.warning(f"상세 정보 조회 실패 (ID: {case_id}): {e}")
        return None


# ============================================================================
# 크롤링 함수
# ============================================================================
def crawl_cases(keywords: List[str], target: str = "prec") -> List[Dict]:
    """
    키워드 기반 판례/해석례 크롤링

    Args:
        keywords: 검색 키워드 리스트
        target: 검색 대상

    Returns:
        수집된 데이터 리스트
    """
    results = []
    seen_ids: Set[str] = set()  # 중복 제거용

    target_name = "판례" if target == "prec" else "해석례"

    for keyword in keywords:
        page = 1
        logger.info(f"\n{'='*60}")
        logger.info(f"[{target_name}] 검색어: {keyword}")
        logger.info(f"{'='*60}")

        while True:
            # 페이지 제한 확인
            if MAX_PAGES and page > MAX_PAGES:
                logger.info(f"  페이지 제한 도달 ({MAX_PAGES}페이지)")
                break

            # 목록 조회
            case_list = get_case_list(keyword, page, target)

            if not case_list:
                logger.info(f"  더 이상 데이터 없음")
                break

            logger.info(f"  [{page}페이지] {len(case_list)}건 발견")

            # 각 케이스 처리
            for idx, item in enumerate(case_list, 1):
                case_id = item.get("판례일련번호") if target == "prec" else item.get("해석례일련번호")

                # 중복 체크
                if case_id in seen_ids:
                    continue
                seen_ids.add(case_id)

                # 기본 데이터 구성
                case_data = {
                    "검색어": keyword,
                    "데이터타입": target_name,
                    "수집시각": datetime.now().isoformat(),
                }

                # 판례/해석례별 필드 추가
                if target == "prec":
                    case_data.update({
                        "사건번호": item.get("사건번호"),
                        "선고일자": item.get("선고일자"),
                        "법원명": item.get("법원명"),
                        "판례일련번호": case_id,
                        "사건종류명": item.get("사건종류명"),
                        "판결유형": item.get("판결유형"),
                        "데이터출처명": item.get("데이터출처명"),
                    })
                elif target == "expc":
                    case_data.update({
                        "해석례일련번호": case_id,
                        "안건명": item.get("안건명"),
                        "소관부처": item.get("소관부처"),
                        "해석일자": item.get("해석일자"),
                    })

                # 상세 정보 조회
                if FETCH_DETAILS and case_id:
                    logger.debug(f"    [{idx}/{len(case_list)}] {target_name} {case_id} 상세 조회 중...")
                    detail = get_case_detail(case_id, target)

                    if detail:
                        case_data["상세정보"] = detail

                    time.sleep(DETAIL_REQUEST_DELAY)

                # 연관성 판단
                if is_traffic_related(case_data):
                    results.append(case_data)
                    logger.debug(f"    ✓ 교통 관련: {case_id}")
                else:
                    logger.debug(f"    ✗ 연관성 없음: {case_id}")

            logger.info(f"  현재까지 수집: {len(results)}건")
            page += 1
            time.sleep(REQUEST_DELAY)

    return results


# ============================================================================
# 메인 함수
# ============================================================================
def main():
    """메인 실행 함수"""
    logger.info("="*60)
    logger.info("법제처 OpenAPI 크롤링 시작")
    logger.info("="*60)
    logger.info(f"키워드 수: {len(TRAFFIC_KEYWORDS)}")
    logger.info(f"상세 정보 조회: {'예' if FETCH_DETAILS else '아니오'}")
    logger.info(f"페이지 제한: {MAX_PAGES if MAX_PAGES else '없음'}")

    # 1. 판례 수집 (샘플 테스트: 키워드 1개만)
    logger.info("\n\n[1/2] 판례 수집 시작 (샘플 테스트)")
    precedents = crawl_cases(["교통사고"], target="prec")

    # 2. 해석례 수집 (샘플 테스트: 키워드 1개만)
    logger.info("\n\n[2/2] 해석례 수집 시작 (샘플 테스트)")
    interpretations = crawl_cases(["교통사고"], target="expc")

    # 결과 통합
    all_results = {
        "수집정보": {
            "수집시각": datetime.now().isoformat(),
            "키워드수": len(TRAFFIC_KEYWORDS),
            "키워드목록": TRAFFIC_KEYWORDS,
            "판례수": len(precedents),
            "해석례수": len(interpretations),
            "총건수": len(precedents) + len(interpretations)
        },
        "판례": precedents,
        "해석례": interpretations
    }

    # 파일 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"traffic_legal_data_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # 요약 출력
    logger.info("\n" + "="*60)
    logger.info("크롤링 완료")
    logger.info("="*60)
    logger.info(f"판례: {len(precedents)}건")
    logger.info(f"해석례: {len(interpretations)}건")
    logger.info(f"총 수집: {len(precedents) + len(interpretations)}건")
    logger.info(f"\n파일 저장: {filename}")

    # 샘플 출력
    if precedents:
        logger.info("\n" + "="*60)
        logger.info("판례 샘플 (첫 번째):")
        logger.info("="*60)
        sample = json.dumps(precedents[0], ensure_ascii=False, indent=2)
        logger.info(sample[:500] + "...")


if __name__ == "__main__":
    main()
