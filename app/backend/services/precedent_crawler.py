"""
Precedent Crawler Service
대법원 판례 크롤링 및 DB 저장 서비스
"""

import logging
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime

from app.backend.services.scourt_scraper import SCourtScraper
from app.backend.services.scourt_client import ScourtClient
from app.backend.models.precedent import Precedent
from app.backend.models.user import User

logger = logging.getLogger(__name__)


class PrecedentCrawler:
    """
    판례 크롤러 - 사법정보공개포털에서 판례를 가져와 DB에 저장
    """

    def __init__(self, scraper: SCourtScraper, scourt_client: Optional[ScourtClient] = None):
        """
        Initialize precedent crawler

        Args:
            scraper: Law.go.kr API client
            scourt_client: Supreme Court portal web scraping client (optional)
        """
        self.scraper = scraper
        self.scourt_client = scourt_client or ScourtClient()

    async def fetch_and_store_latest(
        self,
        db: AsyncSession,
        limit: int = 10,
        case_type: str = "형사"
    ) -> int:
        """
        최신 대법원 판례 조회 및 저장

        Args:
            db: Database session
            limit: 조회할 판례 수
            case_type: 사건 종류 (키워드로 사용)

        Returns:
            저장된 판례 수
        """
        logger.info(f"Fetching latest {limit} {case_type} precedents...")

        try:
            # 웹 스크래핑으로 판례 목록 가져오기
            precedents_data = self.scraper.fetch_recent_precedents(
                limit=limit,
                keyword=case_type
            )

            if not precedents_data:
                logger.warning("No precedents fetched from scraper")
                return 0

            stored_count = 0

            for prec_data in precedents_data:
                try:
                    # 중복 체크 (사건번호로)
                    existing = await db.execute(
                        select(Precedent).where(
                            Precedent.case_number == prec_data["case_number"]
                        )
                    )
                    if existing.scalars().first():
                        logger.debug(f"Precedent {prec_data['case_number']} already exists, skipping")
                        continue

                    # 스크래핑한 데이터에서 정보 가져오기
                    summary = prec_data.get("summary")
                    title = prec_data.get("title", "")

                    # 전문분야 태그 자동 추출 (간단한 키워드 기반)
                    specialization_tags = self._extract_specialization_tags(
                        title,
                        summary or ""
                    )

                    # Precedent 객체 생성
                    precedent = Precedent(
                        case_number=prec_data["case_number"],
                        title=title,
                        summary=summary,
                        full_text=None,  # 스크래핑에서는 전문 가져오지 않음
                        court=prec_data.get("court", "대법원"),
                        decision_date=prec_data["decision_date"],
                        case_type=case_type,
                        specialization_tags=specialization_tags,
                        citation=None,
                        case_link=prec_data.get("case_link"),
                    )

                    db.add(precedent)
                    stored_count += 1
                    logger.info(f"Stored precedent: {precedent.case_number}")

                except Exception as e:
                    logger.error(f"Error storing precedent {prec_data.get('case_number')}: {e}")
                    continue

            # 커밋
            await db.commit()

            logger.info(f"Successfully stored {stored_count} new precedents")
            return stored_count

        except Exception as e:
            logger.error(f"Error in fetch_and_store_latest: {e}")
            await db.rollback()
            return 0

    async def fetch_by_user_specializations(
        self,
        db: AsyncSession,
        user_id: str,
        limit: int = 20
    ) -> int:
        """
        사용자의 전문분야에 맞는 판례 조회 및 저장

        Args:
            db: Database session
            user_id: User UUID
            limit: 조회할 판례 수

        Returns:
            저장된 판례 수
        """
        try:
            # 사용자 정보 조회
            result = await db.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalars().first()

            if not user or not user.specializations:
                logger.warning(f"User {user_id} has no specializations")
                return 0

            stored_count = 0

            # 각 전문분야별로 판례 조회
            for specialization in user.specializations:
                try:
                    # 전문분야 키워드로 스크래핑
                    precedents_data = self.scraper.fetch_recent_precedents(
                        limit=limit // len(user.specializations),
                        keyword=specialization
                    )

                    for prec_data in precedents_data:
                        # 중복 체크
                        existing = await db.execute(
                            select(Precedent).where(
                                Precedent.case_number == prec_data["case_number"]
                            )
                        )
                        if existing.scalars().first():
                            continue

                        # 스크래핑한 데이터에서 정보 가져오기
                        summary = prec_data.get("summary")
                        title = prec_data.get("title", "")

                        # 전문분야 태그 추출
                        specialization_tags = self._extract_specialization_tags(
                            title,
                            summary or ""
                        )
                        # 사용자의 전문분야 추가
                        if specialization not in specialization_tags:
                            specialization_tags.append(specialization)

                        # Precedent 객체 생성
                        precedent = Precedent(
                            case_number=prec_data["case_number"],
                            title=title,
                            summary=summary,
                            full_text=None,  # 스크래핑에서는 전문 가져오지 않음
                            court=prec_data.get("court", "대법원"),
                            decision_date=prec_data["decision_date"],
                            case_type="형사",
                            specialization_tags=specialization_tags,
                            case_link=prec_data.get("case_link"),
                        )

                        db.add(precedent)
                        stored_count += 1

                except Exception as e:
                    logger.error(f"Error fetching precedents for {specialization}: {e}")
                    continue

            await db.commit()

            logger.info(f"Stored {stored_count} precedents for user {user_id}")
            return stored_count

        except Exception as e:
            logger.error(f"Error in fetch_by_user_specializations: {e}")
            await db.rollback()
            return 0

    def _extract_specialization_tags(self, title: str, summary: str) -> List[str]:
        """
        제목과 요약에서 전문분야 태그 추출

        Args:
            title: 판례 제목
            summary: 판례 요약

        Returns:
            List of specialization tags
        """
        tags = []
        text = f"{title} {summary}".lower()

        # 형사법 전문분야 키워드 매핑
        specialization_keywords = {
            "형사일반": ["형법", "형사", "범죄", "처벌"],
            "성범죄": ["성폭력", "성범죄", "강간", "추행", "성매매"],
            "교통사고": ["교통사고", "교통", "음주운전", "무면허"],
            "마약": ["마약", "향정", "대마"],
            "경제범죄": ["사기", "횡령", "배임", "금융"],
            "폭력": ["폭력", "폭행", "상해", "협박", "공갈"],
            "절도강도": ["절도", "강도", "재물"],
            "살인": ["살인", "존속"],
        }

        for spec, keywords in specialization_keywords.items():
            if any(keyword in text for keyword in keywords):
                tags.append(spec)

        # 태그가 없으면 기본값
        if not tags:
            tags.append("형사일반")

        return tags

    async def fetch_from_scourt_portal(
        self,
        db: AsyncSession,
        limit: int = 10,
        case_type: Optional[str] = None,
        keyword: Optional[str] = None
    ) -> int:
        """
        대법원 포털에서 판례 조회 및 저장

        Args:
            db: Database session
            limit: 조회할 판례 수
            case_type: 사건 종류 (형사, 민사 등)
            keyword: 검색 키워드

        Returns:
            저장된 판례 수
        """
        logger.info(f"Fetching {limit} precedents from Supreme Court Portal...")

        try:
            # 대법원 포털에서 판례 검색
            precedents_data = self.scourt_client.search_precedents(
                keyword=keyword,
                case_type=case_type,
                limit=limit
            )

            if not precedents_data:
                logger.warning("No precedents fetched from Supreme Court Portal")
                return 0

            stored_count = 0

            for prec_data in precedents_data:
                try:
                    # 중복 체크 (사건번호로)
                    existing = await db.execute(
                        select(Precedent).where(
                            Precedent.case_number == prec_data["case_number"]
                        )
                    )
                    if existing.scalars().first():
                        logger.debug(f"Precedent {prec_data['case_number']} already exists, updating...")
                        # 업데이트 로직 추가 가능
                        continue

                    # 상세 정보 조회
                    precedent_id = prec_data.get("precedent_id")
                    detail = None
                    if precedent_id:
                        detail = self.scourt_client.fetch_precedent_detail(precedent_id)

                    # 전문분야 태그 자동 추출
                    title = prec_data.get("title", "")
                    summary = prec_data.get("summary", "")
                    specialization_tags = self._extract_specialization_tags(title, summary)

                    # Precedent 객체 생성
                    precedent = Precedent(
                        case_number=prec_data["case_number"],
                        title=title,
                        summary=summary,
                        full_text=detail.get("full_text") if detail else None,
                        judgment_summary=detail.get("judgment_summary") if detail else None,
                        reference_statutes=detail.get("reference_statutes", []) if detail else [],
                        reference_precedents=detail.get("reference_precedents", []) if detail else [],
                        precedent_id=precedent_id,
                        court=prec_data.get("court", "대법원"),
                        decision_date=prec_data["decision_date"],
                        case_type=case_type or "형사",
                        specialization_tags=specialization_tags,
                        case_link=f"https://portal.scourt.go.kr/pgp/main.on?jisCntntsSrno={precedent_id}" if precedent_id else None,
                    )

                    db.add(precedent)
                    stored_count += 1
                    logger.info(f"Stored precedent: {precedent.case_number}")

                except Exception as e:
                    logger.error(f"Error storing precedent {prec_data.get('case_number')}: {e}")
                    continue

            # 커밋
            await db.commit()

            logger.info(f"Successfully stored {stored_count} new precedents from Supreme Court Portal")
            return stored_count

        except Exception as e:
            logger.error(f"Error in fetch_from_scourt_portal: {e}")
            await db.rollback()
            return 0
