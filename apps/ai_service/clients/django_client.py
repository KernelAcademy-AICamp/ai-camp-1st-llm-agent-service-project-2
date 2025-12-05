"""
Django Backend API Client

AI 서비스에서 Django 백엔드 API를 호출하는 클라이언트입니다.
Agent Hub에서 사용자 문서, 분석 결과 등을 조회할 때 사용합니다.
"""

import os
import logging
from typing import Dict, Any, Optional, List
import httpx

logger = logging.getLogger(__name__)


class DjangoClient:
    """
    Django Backend API 클라이언트

    사용법:
        client = DjangoClient()

        # 사용자 문서 목록 조회
        documents = await client.list_documents(user_id="...", auth_token="...")

        # 문서 상세 조회
        document = await client.get_document(document_id="...", user_id="...", auth_token="...")
    """

    def __init__(
        self,
        base_url: str = None,
        timeout: float = 30.0,
    ):
        """
        DjangoClient 초기화

        Args:
            base_url: Django 백엔드 URL (기본: 환경변수 또는 localhost:8000)
            timeout: 요청 타임아웃 (초)
        """
        self.base_url = base_url or os.getenv("DJANGO_API_URL", "http://localhost:8000")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """HTTP 클라이언트 반환 (지연 생성)"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
            )
        return self._client

    async def close(self):
        """클라이언트 종료"""
        if self._client:
            await self._client.aclose()
            self._client = None

    def _get_headers(self, auth_token: str = None, user_id: str = None) -> Dict[str, str]:
        """
        요청 헤더 생성

        Args:
            auth_token: JWT 토큰 (Bearer 토큰)
            user_id: 사용자 ID (내부 서비스 호출용)
        """
        headers = {
            "Content-Type": "application/json",
        }

        if auth_token:
            # 클라이언트 인증 (JWT 토큰)
            headers["Authorization"] = f"Bearer {auth_token}"
        else:
            # 내부 서비스 인증
            headers["X-Service-Auth"] = "agent-hub-internal"
            if user_id:
                headers["X-User-Id"] = user_id

        return headers

    # =========================================================================
    # 문서 관련 API
    # =========================================================================

    async def list_documents(
        self,
        user_id: str,
        auth_token: str = None,
        doc_type: str = None,
        status: str = None,
        search: str = None,
        has_risk_analysis: bool = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        사용자 문서 목록 조회

        Args:
            user_id: 사용자 UUID
            auth_token: JWT 토큰 (선택)
            doc_type: 문서 유형 필터 (CASE, CONTRACT, etc.)
            status: 상태 필터 (UPLOADED, PREPROCESSED, EMBEDDED)
            search: 제목 검색어
            has_risk_analysis: 리스크 분석 유무 필터
            limit: 결과 수 제한

        Returns:
            {
                "success": True,
                "count": int,
                "documents": [
                    {
                        "id": str,
                        "title": str,
                        "doc_type": str,
                        "status": str,
                        "created_at": str,
                        ...
                    }
                ]
            }
        """
        try:
            client = await self._get_client()
            headers = self._get_headers(auth_token, user_id)

            # 쿼리 파라미터 구성
            params = {}
            if doc_type:
                params["doc_type"] = doc_type
            if status:
                params["status"] = status
            if search:
                params["search"] = search
            if has_risk_analysis is not None:
                params["has_risk_analysis"] = str(has_risk_analysis).lower()
            if limit:
                params["page_size"] = limit

            response = await client.get(
                "/api/v1/documents/",
                headers=headers,
                params=params,
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "count": data.get("count", 0),
                    "documents": data.get("results", []),
                }
            elif response.status_code == 401:
                return {
                    "success": False,
                    "error": "인증이 필요합니다",
                    "documents": [],
                }
            else:
                logger.warning(f"Django API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API 오류: {response.status_code}",
                    "documents": [],
                }

        except httpx.RequestError as e:
            logger.error(f"Django API request error: {e}")
            return {
                "success": False,
                "error": f"연결 오류: {str(e)}",
                "documents": [],
            }
        except Exception as e:
            logger.error(f"Django API error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "documents": [],
            }

    async def get_document(
        self,
        document_id: str,
        user_id: str,
        auth_token: str = None,
    ) -> Dict[str, Any]:
        """
        문서 상세 조회

        Args:
            document_id: 문서 UUID
            user_id: 사용자 UUID
            auth_token: JWT 토큰 (선택)

        Returns:
            {
                "success": True,
                "document": {...}
            }
        """
        try:
            client = await self._get_client()
            headers = self._get_headers(auth_token, user_id)

            response = await client.get(
                f"/api/v1/documents/{document_id}/",
                headers=headers,
            )

            if response.status_code == 200:
                return {
                    "success": True,
                    "document": response.json(),
                }
            elif response.status_code == 404:
                return {
                    "success": False,
                    "error": "문서를 찾을 수 없습니다",
                    "document": None,
                }
            else:
                return {
                    "success": False,
                    "error": f"API 오류: {response.status_code}",
                    "document": None,
                }

        except Exception as e:
            logger.error(f"get_document error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "document": None,
            }

    async def get_document_summary(
        self,
        document_id: str,
        user_id: str,
        auth_token: str = None,
    ) -> Dict[str, Any]:
        """
        문서 요약 조회

        Args:
            document_id: 문서 UUID
            user_id: 사용자 UUID
            auth_token: JWT 토큰 (선택)

        Returns:
            {
                "success": True,
                "summary": {...}
            }
        """
        try:
            client = await self._get_client()
            headers = self._get_headers(auth_token, user_id)

            response = await client.get(
                f"/api/v1/documents/{document_id}/summary/",
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "document_id": data.get("document_id"),
                    "document_title": data.get("document_title"),
                    "summary": data.get("summary"),
                }
            else:
                return {
                    "success": False,
                    "error": f"API 오류: {response.status_code}",
                    "summary": None,
                }

        except Exception as e:
            logger.error(f"get_document_summary error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "summary": None,
            }

    async def get_document_risk_analysis(
        self,
        document_id: str,
        user_id: str,
        auth_token: str = None,
    ) -> Dict[str, Any]:
        """
        문서 리스크 분석 결과 조회

        Args:
            document_id: 문서 UUID
            user_id: 사용자 UUID
            auth_token: JWT 토큰 (선택)

        Returns:
            {
                "success": True,
                "risk_analysis": {...}
            }
        """
        try:
            client = await self._get_client()
            headers = self._get_headers(auth_token, user_id)

            response = await client.get(
                f"/api/v1/documents/{document_id}/risk_analysis/",
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "document_id": data.get("document_id"),
                    "document_title": data.get("document_title"),
                    "risk_analysis": data.get("risk_analysis"),
                }
            else:
                return {
                    "success": False,
                    "error": f"API 오류: {response.status_code}",
                    "risk_analysis": None,
                }

        except Exception as e:
            logger.error(f"get_document_risk_analysis error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "risk_analysis": None,
            }

    async def get_document_case_analysis(
        self,
        document_id: str,
        user_id: str,
        auth_token: str = None,
    ) -> Dict[str, Any]:
        """
        문서 사건 분석 결과 조회

        Args:
            document_id: 문서 UUID
            user_id: 사용자 UUID
            auth_token: JWT 토큰 (선택)

        Returns:
            {
                "success": True,
                "case_analysis": {...}
            }
        """
        try:
            client = await self._get_client()
            headers = self._get_headers(auth_token, user_id)

            response = await client.get(
                f"/api/v1/documents/{document_id}/case-analysis/",
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "document_id": data.get("document_id"),
                    "document_title": data.get("document_title"),
                    "case_analysis": data.get("case_analysis"),
                }
            else:
                return {
                    "success": False,
                    "error": f"API 오류: {response.status_code}",
                    "case_analysis": None,
                }

        except Exception as e:
            logger.error(f"get_document_case_analysis error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "case_analysis": None,
            }

    async def list_documents_with_risk(
        self,
        user_id: str,
        auth_token: str = None,
        severity: str = None,
        min_score: int = None,
        max_score: int = None,
        sort_by: str = "risk_score",
        order: str = "desc",
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        리스크 분석이 있는 문서 목록 조회 (정렬 가능)

        Args:
            user_id: 사용자 UUID
            auth_token: JWT 토큰 (선택)
            severity: 심각도 필터 (CRITICAL, HIGH, MEDIUM, LOW, INFO)
            min_score: 최소 리스크 점수
            max_score: 최대 리스크 점수
            sort_by: 정렬 기준 (risk_score, created_at, title)
            order: 정렬 순서 (asc, desc)
            limit: 결과 수 제한

        Returns:
            {
                "success": True,
                "count": int,
                "documents": [
                    {
                        "document": {...},
                        "risk_analysis": {...}
                    }
                ]
            }
        """
        try:
            client = await self._get_client()
            headers = self._get_headers(auth_token, user_id)

            # 쿼리 파라미터 구성
            params = {
                "sort_by": sort_by,
                "order": order,
                "page_size": limit,
            }
            if severity:
                params["severity"] = severity
            if min_score is not None:
                params["min_score"] = min_score
            if max_score is not None:
                params["max_score"] = max_score

            response = await client.get(
                "/api/v1/documents/with-risk/",
                headers=headers,
                params=params,
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "count": data.get("count", 0),
                    "documents": data.get("results", []),
                }
            else:
                return {
                    "success": False,
                    "error": f"API 오류: {response.status_code}",
                    "documents": [],
                }

        except Exception as e:
            logger.error(f"list_documents_with_risk error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "documents": [],
            }

    async def get_risk_overview(
        self,
        user_id: str,
        auth_token: str = None,
    ) -> Dict[str, Any]:
        """
        리스크 분석 통계 개요 조회

        Args:
            user_id: 사용자 UUID
            auth_token: JWT 토큰 (선택)

        Returns:
            {
                "success": True,
                "total_documents": int,
                "documents_with_risk": int,
                "avg_risk_score": float,
                "high_risk_count": int,
                "severity_distribution": {...},
                ...
            }
        """
        try:
            client = await self._get_client()
            headers = self._get_headers(auth_token, user_id)

            response = await client.get(
                "/api/v1/documents/risk-overview/",
                headers=headers,
            )

            if response.status_code == 200:
                data = response.json()
                data["success"] = True
                return data
            else:
                return {
                    "success": False,
                    "error": f"API 오류: {response.status_code}",
                }

        except Exception as e:
            logger.error(f"get_risk_overview error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # 형사 사건 관련 API (criminal_cases)
    # =========================================================================

    async def list_criminal_cases(
        self,
        user_id: str,
        auth_token: str = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        사용자의 형사 사건 목록 조회

        Args:
            user_id: 사용자 UUID
            auth_token: JWT 토큰 (선택)
            limit: 결과 수 제한

        Returns:
            {
                "success": True,
                "count": int,
                "cases": [...]
            }
        """
        try:
            # 형사 사건은 ai_service 내부 DB에 저장됨
            # CriminalCaseService를 사용하여 조회
            from apps.ai_service.services.criminal_case_service import CriminalCaseService
            from apps.ai_service.models.database import get_db

            async for db in get_db():
                service = CriminalCaseService(db)
                cases = await service.list_cases(user_id, limit=limit)

                return {
                    "success": True,
                    "count": len(cases),
                    "cases": [
                        {
                            "id": str(case.id),
                            "case_name": case.case_name,
                            "crime_type": case.crime_type,
                            "summary": case.summary,
                            "expected_sentence": case.expected_sentence,
                            "created_at": case.created_at.isoformat() if case.created_at else None,
                        }
                        for case in cases
                    ],
                }

        except Exception as e:
            logger.error(f"list_criminal_cases error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "cases": [],
            }

    async def get_criminal_case(
        self,
        case_id: str,
        user_id: str,
        auth_token: str = None,
    ) -> Dict[str, Any]:
        """
        형사 사건 상세 조회

        Args:
            case_id: 사건 UUID
            user_id: 사용자 UUID
            auth_token: JWT 토큰 (선택)

        Returns:
            {
                "success": True,
                "case": {...}
            }
        """
        try:
            from apps.ai_service.services.criminal_case_service import CriminalCaseService
            from apps.ai_service.models.database import get_db

            async for db in get_db():
                service = CriminalCaseService(db)
                case = await service.get_case(case_id, user_id)

                if case:
                    return {
                        "success": True,
                        "case": {
                            "id": str(case.id),
                            "case_name": case.case_name,
                            "crime_type": case.crime_type,
                            "summary": case.summary,
                            "crime_elements": case.crime_elements,
                            "sentencing_factors": case.sentencing_factors,
                            "expected_sentence": case.expected_sentence,
                            "defense_strategies": case.defense_strategies,
                            "related_precedents": case.related_precedents,
                            "created_at": case.created_at.isoformat() if case.created_at else None,
                        },
                    }
                else:
                    return {
                        "success": False,
                        "error": "사건을 찾을 수 없습니다",
                        "case": None,
                    }

        except Exception as e:
            logger.error(f"get_criminal_case error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "case": None,
            }

    async def get_criminal_case_with_highest_sentence(
        self,
        user_id: str,
        auth_token: str = None,
    ) -> Dict[str, Any]:
        """
        예상 양형이 가장 높은 형사 사건 조회

        Args:
            user_id: 사용자 UUID
            auth_token: JWT 토큰 (선택)

        Returns:
            {
                "success": True,
                "case": {...},
                "reason": str
            }
        """
        try:
            from apps.ai_service.services.criminal_case_service import CriminalCaseService
            from apps.ai_service.models.database import get_db

            async for db in get_db():
                service = CriminalCaseService(db)
                cases = await service.list_cases(user_id, limit=100)

                if not cases:
                    return {
                        "success": True,
                        "case": None,
                        "reason": "저장된 형사 사건이 없습니다",
                    }

                # 양형 정보에서 가장 높은 형량을 찾음
                highest_case = None
                highest_score = -1

                for case in cases:
                    if case.expected_sentence:
                        sentence = case.expected_sentence
                        # suspended_probability가 낮을수록 (실형 가능성 높음) 높은 점수
                        # range에서 숫자 추출 시도
                        score = 0

                        # 집행유예 확률 반영 (낮을수록 심각)
                        prob = sentence.get("suspended_probability", 0.5)
                        score += (1 - prob) * 50

                        # 형량 범위에서 최대값 추출 시도
                        range_str = sentence.get("range", "")
                        import re
                        numbers = re.findall(r'\d+', range_str)
                        if numbers:
                            max_num = max(int(n) for n in numbers)
                            score += max_num

                        if score > highest_score:
                            highest_score = score
                            highest_case = case

                if highest_case:
                    return {
                        "success": True,
                        "case": {
                            "id": str(highest_case.id),
                            "case_name": highest_case.case_name,
                            "crime_type": highest_case.crime_type,
                            "summary": highest_case.summary,
                            "expected_sentence": highest_case.expected_sentence,
                            "created_at": highest_case.created_at.isoformat() if highest_case.created_at else None,
                        },
                        "reason": f"예상 형량: {highest_case.expected_sentence.get('range', '알 수 없음')}, "
                                  f"집행유예 확률: {highest_case.expected_sentence.get('suspended_probability', 0.5):.0%}",
                    }
                else:
                    return {
                        "success": True,
                        "case": None,
                        "reason": "양형 정보가 있는 사건이 없습니다",
                    }

        except Exception as e:
            logger.error(f"get_criminal_case_with_highest_sentence error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "case": None,
            }


# =============================================================================
# 싱글톤/팩토리
# =============================================================================

_client_instance: Optional[DjangoClient] = None


def get_django_client() -> DjangoClient:
    """DjangoClient 인스턴스 반환 (싱글톤)"""
    global _client_instance
    if _client_instance is None:
        _client_instance = DjangoClient()
    return _client_instance


async def cleanup_django_client():
    """DjangoClient 정리"""
    global _client_instance
    if _client_instance:
        await _client_instance.close()
        _client_instance = None
