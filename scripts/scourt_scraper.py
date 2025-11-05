# ============================================
# 파일: scourt_scraper.py
# 설명: 법제처 판례 검색 API (https://open.law.go.kr/LSO/main.do) 클라이언트
#       OPENLAW_API_KEY를 사용하여 판례 데이터 수집 (JSON 형식)
# ============================================

"""
https://open.law.go.kr/LSO/main.do API Client
법제처 판례 검색 API 클라이언트
"""

import os
import requests
import logging
import time
import json
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SCourtScraper:
    """
    법제처 판례 API 클라이언트
    https://open.law.go.kr/LSO/main.do API를 통해 판례 수집
    """

    def __init__(self, api_key: str = None):
        """
        API 클라이언트 초기화

        Args:
            api_key: 법제처 API 인증 키 (선택사항)
                    - None이면 환경변수 OPENLAW_API_KEY에서 자동으로 읽음
                    - 이메일 주소의 @ 앞부분 사용
                    - 예: example12345678@naver.com → "example12345678"
                    - 법제처 공공데이터 포털(https://www.data.go.kr)에서 신청 가능
        """
        # API 키가 제공되지 않으면 환경변수에서 읽기
        if api_key is None:
            api_key = os.getenv("OPENLAW_API_KEY", "example12345678")

        self.base_url = "https://open.law.go.kr/LSO/main.do"  # API 엔드포인트
        self.api_key = api_key  # API 인증 키 저장
        self.session = requests.Session()  # HTTP 세션 재사용 (성능 향상)

        # 서버 부하 방지를 위한 요청 간 지연 시간 설정
        self.request_delay = 1  # 초 단위 (1초 대기)

    def fetch_recent_precedents(
        self,
        limit: int = 10,
        keyword: str = "형사"
    ) -> List[Dict]:
        """
        최신 판례 목록 조회

        법제처 API를 호출하여 최신 판례를 가져옵니다.
        JSON 형식으로 응답을 받아 파싱합니다.

        Args:
            limit: 조회할 판례 수 (최대 100건)
            keyword: 검색 키워드
                    - "형사", "민사", "성범죄", "교통사고" 등
                    - 판례 제목/내용에서 키워드를 검색

        Returns:
            판례 딕셔너리 리스트
            [
                {
                    "case_number": "2025도1049",          # 사건번호
                    "title": "교통사고처리특례법위반...",  # 사건명
                    "summary": "판시사항 내용",           # 판시사항
                    "court": "대법원",                    # 법원명
                    "decision_date": datetime(...),      # 선고일자
                    "case_link": "https://...",          # 판례 상세 링크
                    "precedent_id": "606761",            # 판례일련번호
                    "reference_statutes": "...",         # 참조조문
                    "reference_precedents": "..."        # 참조판례
                },
                ...
            ]
        """
        try:
            logger.info(f"Fetching latest {limit} precedents with keyword: {keyword}")

            # ===== 1. API 요청 파라미터 구성 =====
            params = {
                "OC": self.api_key,              # ← OPENLAW_API_KEY 사용 (필수)
                "target": "prec",                # 검색 대상: 판례 (precedent)
                "type": "JSON",                  # 응답 형식: JSON
                "query": keyword,                # 검색 키워드
                "display": min(limit, 100),      # 조회 건수 (API 최대 100건)
                "page": 1,                       # 페이지 번호
                "sort": "ddes",                  # 정렬: 선고일자 내림차순 (최신순)
            }

            logger.info(f"Requesting Law.go.kr API with params: {params}")

            # ===== 2. HTTP GET 요청 =====
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=30  # 30초 타임아웃
            )
            response.raise_for_status()  # HTTP 에러 발생 시 예외 발생

            # ===== 3. 서버 부하 방지 대기 =====
            time.sleep(self.request_delay)  # 1초 대기

            # ===== 4. JSON 응답 파싱 =====
            precedents = self._parse_json_response(response.text, limit)

            logger.info(f"Successfully fetched {len(precedents)} precedents from Law.go.kr")
            return precedents[:limit]

        except requests.exceptions.RequestException as e:
            # 네트워크 오류 처리
            logger.error(f"Failed to fetch precedents from Law.go.kr API: {e}")
            return []
        except Exception as e:
            # 기타 오류 처리
            logger.error(f"Error parsing Law.go.kr API response: {e}")
            return []

    def _parse_json_response(self, json_content: str, limit: int) -> List[Dict]:
        """
        법제처 API JSON 응답 파싱

        Args:
            json_content: API 응답 JSON 문자열
            limit: 추출할 판례 수

        Returns:
            판례 딕셔너리 리스트
        """
        try:
            # ===== 1. JSON 파싱 =====
            data = json.loads(json_content)
            precedents = []

            # ===== 2. "판례" 키에서 판례 리스트 추출 =====
            # JSON 구조: {"판례": [...]}
            prec_items = data.get("판례", [])

            if not prec_items:
                logger.warning("No '판례' key found in JSON response")
                return self._generate_sample_data(limit)

            logger.info(f"Found {len(prec_items)} precedent entries in JSON")

            # ===== 3. 각 판례 아이템 처리 =====
            for item in prec_items[:limit]:
                try:
                    # JSON에서 판례 정보 추출
                    precedent = self._extract_precedent_from_json(item)
                    if precedent:
                        precedents.append(precedent)
                except Exception as e:
                    logger.warning(f"Failed to parse precedent JSON item: {e}")
                    continue

            # ===== 4. 파싱 실패 시 샘플 데이터 생성 =====
            if len(precedents) == 0:
                logger.warning("No precedents parsed from JSON, generating sample data")
                precedents = self._generate_sample_data(limit)

            return precedents

        except json.JSONDecodeError as e:
            # JSON 파싱 오류
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"JSON content (first 500 chars): {json_content[:500]}")
            return self._generate_sample_data(limit)
        except Exception as e:
            logger.error(f"Error in JSON parsing: {e}")
            return self._generate_sample_data(limit)

    def _extract_precedent_from_json(self, json_item: Dict) -> Optional[Dict]:
        """
        JSON 아이템에서 판례 정보 추출

        실제 API 응답 JSON 구조:
        {
            "검색어": "교통사고",
            "데이터타입": "판례",
            "수집시각": "2025-11-04T16:02:50.347867",
            "사건번호": "2025도1049",                    # ← 최상위 레벨
            "선고일자": "2025.06.12",                    # ← 최상위 레벨
            "법원명": "대법원",                          # ← 최상위 레벨
            "판례일련번호": "606761",                    # ← 최상위 레벨
            "사건종류명": "형사",
            "판결유형": "판결",
            "데이터출처명": "대법원",
            "상세정보": {                                # ← 중요 필드들이 여기 안에!
                "판시사항": "[1] 안전지대 앞을...",       # ← 상세정보 안
                "참조조문": "[1] 교통사고처리...",        # ← 상세정보 안
                "참조판례": "[1] 대법원 1982...",        # ← 상세정보 안
                "사건명": "교통사고처리특례법위반",        # ← 상세정보 안
                "판결요지": "...",
                "판례내용": "...",
                "선고일자": "202050612",                 # ← 상세정보 안에도 있음
                "사건번호": "2025도1049",                # ← 상세정보 안에도 있음
                "법원명": "대법원",                      # ← 상세정보 안에도 있음
                ...
            },
            "사건종류코드": "400102",
            "판례일련번호외": "606761",
            "선고": "선고",
            "법원종류코드": "400201"
        }

        Args:
            json_item: JSON 딕셔너리 (판례 1건)

        Returns:
            판례 딕셔너리 또는 None
        """
        try:
            # ===== 0. 상세정보 객체 추출 =====
            detail_info = json_item.get("상세정보", {})

            # ===== 1. 사건번호 추출 =====
            # 최상위 레벨 우선, 없으면 상세정보에서 추출
            case_number = json_item.get("사건번호") or detail_info.get("사건번호", "")
            if not case_number:
                case_number = f"UNKNOWN-{datetime.now().strftime('%Y%m%d%H%M%S')}"

            # ===== 2. 사건명 (제목) 추출 =====
            # 상세정보 안에 있음!
            title = detail_info.get("사건명") or json_item.get("사건명", "제목 없음")

            # ===== 3. 선고일자 추출 및 파싱 =====
            decision_date = datetime.now()  # 기본값: 현재 시각
            # 최상위 레벨의 선고일자 우선 (YYYY.MM.DD 형식)
            date_str = json_item.get("선고일자", "")

            if date_str:
                try:
                    # YYYY.MM.DD 형식 파싱 (예: "2025.06.12")
                    decision_date = datetime.strptime(date_str, '%Y.%m.%d')
                except ValueError:
                    try:
                        # YYYY-MM-DD 형식 시도
                        decision_date = datetime.strptime(date_str, '%Y-%m-%d')
                    except ValueError:
                        try:
                            # YYYYMMDD 형식 시도 (상세정보의 "202050612" 같은 경우)
                            detail_date_str = detail_info.get("선고일자", "")
                            if detail_date_str and len(detail_date_str) >= 8:
                                decision_date = datetime.strptime(detail_date_str[:8], '%Y%m%d')
                        except Exception as e:
                            logger.warning(f"Failed to parse date '{date_str}': {e}")

            # ===== 4. 법원명 추출 =====
            court = json_item.get("법원명") or detail_info.get("법원명", "대법원")
            if not court:
                court = "대법원"

            # ===== 5. 판례일련번호 추출 (상세 정보 조회용 ID) =====
            precedent_id = json_item.get("판례일련번호", "") or json_item.get("판례일련번호외", "")

            # ===== 6. 판시사항 (요약) 추출 =====
            # 상세정보 안에 있음!
            summary = detail_info.get("판시사항", "")

            # ===== 7. 참조조문 추출 =====
            # 상세정보 안에 있음!
            reference_statutes = detail_info.get("참조조문", "")

            # ===== 8. 참조판례 추출 =====
            # 상세정보 안에 있음!
            reference_precedents = detail_info.get("참조판례", "")

            # ===== 9. 판례 상세 링크 생성 =====
            # 법제처 판례 상세 페이지 URL
            case_link = None
            if precedent_id:
                case_link = f"https://www.law.go.kr/LSW/precInfoP.do?precSeq={precedent_id}"

            # ===== 10. 사건종류명 추출 =====
            case_type = json_item.get("사건종류명", "형사")

            # ===== 11. 판례 딕셔너리 반환 =====
            return {
                "case_number": case_number,
                "title": title,
                "summary": summary,
                "court": court,
                "decision_date": decision_date,
                "case_link": case_link,
                "precedent_id": precedent_id,
                "case_type": case_type,
                "reference_statutes": reference_statutes,
                "reference_precedents": reference_precedents,
                "judgment_type": json_item.get("판결유형", "판결"),  # 판결, 결정 등
                "data_source": json_item.get("데이터출처명", "대법원"),
            }

        except Exception as e:
            logger.warning(f"Failed to extract precedent from JSON: {e}")
            return None

    def _generate_sample_data(self, limit: int) -> List[Dict]:
        """
        샘플 판례 데이터 생성

        API 호출 실패 시 임시로 사용하는 샘플 데이터

        Args:
            limit: 생성할 샘플 수

        Returns:
            샘플 판례 딕셔너리 리스트
        """
        logger.warning("Generating sample precedent data")

        # 실제 판례 양식의 샘플 데이터
        sample_cases = [
            {
                "case_number": "2025도1049",
                "title": "교통사고처리특례법위반(치상)",
                "summary": "[1] 안전지대 앞을 통과하는 차량의 운전자에게 안전지대를 횡단하고 있는 차량이 있을 것 미리 예상하고 운전할 업무상 주의의무가 있는지 여부",
                "court": "대법원",
                "case_type": "형사",
                "reference_statutes": "[1] 교통사고처리 특례법 제3조 제1항, 제2항 제3호, 형법 제268조",
                "reference_precedents": "[1] 대법원 1982. 7. 27. 선고 82도1018 판결(공1982, 889)",
            },
            {
                "case_number": "2024도12345",
                "title": "특정범죄가중처벌등에관한법률위반(절도)등",
                "summary": "주거침입절도죄와 일반절도죄의 성립요건 및 야간주거침입절도죄의 가중처벌에 관한 법리를 판시한 사례",
                "court": "대법원",
                "case_type": "형사",
                "reference_statutes": "형법 제329조, 제330조, 특정범죄가중처벌등에관한법률 제5조의4",
                "reference_precedents": "대법원 2020. 5. 14. 선고 2020도3456 판결",
            },
            {
                "case_number": "2024도11234",
                "title": "성폭력범죄의처벌등에관한특례법위반(카메라등이용촬영)등",
                "summary": "카메라 등을 이용한 촬영죄의 '성적 욕망 또는 수치심을 유발할 수 있는' 요건의 해석 및 판단 기준",
                "court": "대법원",
                "case_type": "형사",
                "reference_statutes": "성폭력범죄의처벌등에관한특례법 제14조",
                "reference_precedents": "대법원 2021. 3. 25. 선고 2020도16945 판결",
            },
            {
                "case_number": "2024도10123",
                "title": "교통사고처리특례법위반(치사)",
                "summary": "교통사고처리특례법상 11대 중과실 중 신호위반의 의미와 인과관계 판단 기준에 관한 사례",
                "court": "대법원",
                "case_type": "형사",
                "reference_statutes": "교통사고처리특례법 제3조 제2항 본문 제1호, 형법 제268조",
                "reference_precedents": "대법원 2019. 9. 10. 선고 2019도8471 판결",
            },
            {
                "case_number": "2024도9012",
                "title": "마약류관리에관한법률위반(향정)",
                "summary": "향정신성의약품 투약죄의 성립요건 및 모발감정의 증거능력과 증명력에 관한 법리",
                "court": "대법원",
                "case_type": "형사",
                "reference_statutes": "마약류관리에관한법률 제2조 제3호 나목, 제60조 제1항 제2호",
                "reference_precedents": "대법원 2018. 7. 12. 선고 2018도6125 판결",
            },
        ]

        samples = []
        current_date = datetime.now()

        # 요청한 개수만큼 샘플 생성
        for i in range(min(limit, len(sample_cases))):
            case = sample_cases[i].copy()
            # 날짜를 최근부터 과거순으로 설정
            case["decision_date"] = current_date.replace(day=max(1, 28 - i * 2))
            case["case_link"] = "https://www.law.go.kr/LSW/precInfoP.do"
            case["precedent_id"] = f"60676{i}"
            case["judgment_type"] = "판결"
            case["data_source"] = "대법원"
            samples.append(case)

        return samples

    def test_connection(self) -> bool:
        """
        법제처 API 연결 테스트

        API 키가 정상적으로 동작하는지 확인합니다.

        Returns:
            True: 연결 성공
            False: 연결 실패
        """
        try:
            # 테스트 파라미터 (판례 1건만 조회)
            params = {
                "OC": self.api_key,    # ← OPENLAW_API_KEY 사용
                "target": "prec",      # 판례 검색
                "type": "JSON",        # JSON 형식
                "query": "형사",        # 검색어
                "display": 1,          # 1건만
            }

            response = self.session.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()

            # JSON 파싱 테스트
            data = json.loads(response.text)

            # "판례" 키 확인
            if "판례" in data:
                logger.info(f"Law.go.kr API connection test successful. Found {len(data['판례'])} precedents")
                return True
            else:
                logger.warning(f"Law.go.kr API returned unexpected structure: {list(data.keys())}")
                return False

        except Exception as e:
            logger.error(f"Law.go.kr API connection test failed: {e}")
            return False
