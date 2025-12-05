"""
Criminal Dashboard Service
형사 사건 대시보드 서비스
"""

from typing import List, Dict, Optional
from datetime import date, timedelta, datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..models.criminal_case import (
    CriminalStage,
    CriminalCaseListItem,
    ScheduleItem,
    DashboardSummary,
    SimilarCaseStatistics,
)

logger = logging.getLogger(__name__)


class CriminalDashboardService:
    """형사 사건 대시보드 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_summary(
        self,
        user_id: str
    ) -> DashboardSummary:
        """
        대시보드 요약 데이터 조회

        - CriminalCase 테이블에서 사용자의 사건 조회
        - 단계별 집계, 다가오는 일정 등 계산
        """
        try:
            # 1. 사용자 사건 조회
            cases = await self._get_user_cases(user_id)

            # 2. 단계별 집계
            cases_by_stage = self._count_by_stage(cases)

            # 3. 다가오는 일정 (7일 이내)
            upcoming_schedules = self._get_upcoming_schedules(cases, days=7)

            # 4. 권장 사항 생성
            recommendations = self._generate_recommendations(cases)

            # 5. 주요 사건 (가장 최근 또는 가장 긴급)
            primary_case = self._get_primary_case(cases)

            # 6. 사건 목록 변환
            case_list_items = []
            for case in cases:
                next_schedule = self._get_next_schedule(case)
                case_list_items.append(CriminalCaseListItem(
                    id=case["id"],
                    case_name=case["case_name"],
                    crime_type=case["crime_type"],
                    stage=CriminalStage(case["stage"]),
                    next_schedule=next_schedule,
                    created_at=case["created_at"]
                ))

            return DashboardSummary(
                total_cases=len(cases),
                cases_by_stage=cases_by_stage,
                upcoming_schedules=upcoming_schedules,
                recommendations=recommendations,
                primary_case=primary_case,
                cases=case_list_items
            )

        except Exception as e:
            logger.error(f"Failed to get dashboard summary: {e}")
            raise

    async def _get_user_cases(self, user_id: str) -> List[Dict]:
        """사용자 사건 목록 조회"""
        query = """
            SELECT
                id::text,
                case_name,
                crime_type,
                stage,
                schedules,
                conditions,
                updated_at,
                created_at
            FROM criminal_cases
            WHERE user_id = :user_id
            ORDER BY created_at DESC
        """

        result = await self.db.execute(text(query), {"user_id": user_id})
        rows = result.fetchall()

        cases = []
        for row in rows:
            cases.append({
                "id": row.id,
                "case_name": row.case_name,
                "crime_type": row.crime_type,
                "stage": row.stage,
                "schedules": row.schedules or [],
                "conditions": row.conditions or [],
                "updated_at": row.updated_at,
                "created_at": row.created_at
            })

        return cases

    def _count_by_stage(self, cases: List[Dict]) -> Dict[str, int]:
        """단계별 사건 수 집계"""
        counts = {stage.value: 0 for stage in CriminalStage}
        for case in cases:
            stage = case.get("stage")
            if stage in counts:
                counts[stage] += 1
        return counts

    def _get_upcoming_schedules(
        self,
        cases: List[Dict],
        days: int = 7
    ) -> List[Dict]:
        """다가오는 일정 조회"""
        today = date.today()
        end_date = today + timedelta(days=days)

        schedules = []
        for case in cases:
            case_schedules = case.get("schedules", [])
            for schedule in case_schedules:
                if schedule.get("is_completed"):
                    continue

                schedule_date = schedule.get("date")
                if schedule_date:
                    if isinstance(schedule_date, str):
                        try:
                            schedule_date = date.fromisoformat(schedule_date)
                        except ValueError:
                            continue

                    if today <= schedule_date <= end_date:
                        schedules.append({
                            "case_id": case["id"],
                            "case_name": case["case_name"],
                            "date": schedule_date.isoformat() if isinstance(schedule_date, date) else schedule_date,
                            "title": schedule.get("title", ""),
                            "schedule_type": schedule.get("schedule_type", "MEETING"),
                            "description": schedule.get("description"),
                        })

        # 날짜순 정렬
        schedules.sort(key=lambda x: x.get("date", ""))
        return schedules

    def _generate_recommendations(self, cases: List[Dict]) -> List[Dict]:
        """권장 사항 생성"""
        recommendations = []
        today = date.today()

        for case in cases:
            conditions = case.get("conditions", [])
            stage = case.get("stage")
            updated_at = case.get("updated_at")

            # 피해회복 안 된 경우
            if "피해회복" not in conditions and stage in [
                CriminalStage.INVESTIGATION.value,
                CriminalStage.PROSECUTION.value
            ]:
                recommendations.append({
                    "case_id": case["id"],
                    "case_name": case["case_name"],
                    "priority": "HIGH",
                    "content": "피해자 합의 시도 권장"
                })

            # 수사 단계에서 오래된 경우
            if stage == CriminalStage.INVESTIGATION.value and updated_at:
                if isinstance(updated_at, datetime):
                    days_in_stage = (today - updated_at.date()).days
                    if days_in_stage > 30:
                        recommendations.append({
                            "case_id": case["id"],
                            "case_name": case["case_name"],
                            "priority": "MEDIUM",
                            "content": "수사 진행 상황 확인 필요"
                        })

            # 공판 단계에서 일정이 없는 경우
            if stage == CriminalStage.TRIAL.value:
                schedules = case.get("schedules", [])
                upcoming = [s for s in schedules if not s.get("is_completed")]
                if not upcoming:
                    recommendations.append({
                        "case_id": case["id"],
                        "case_name": case["case_name"],
                        "priority": "HIGH",
                        "content": "공판 기일 확인 및 등록 필요"
                    })

        return recommendations

    def _get_primary_case(self, cases: List[Dict]) -> Optional[Dict]:
        """주요 사건 선택 (가장 긴급한 일정이 있는 사건)"""
        if not cases:
            return None

        today = date.today()
        urgent_case = None
        min_days = float("inf")

        for case in cases:
            schedules = case.get("schedules", [])
            for schedule in schedules:
                if schedule.get("is_completed"):
                    continue

                schedule_date = schedule.get("date")
                if schedule_date:
                    if isinstance(schedule_date, str):
                        try:
                            schedule_date = date.fromisoformat(schedule_date)
                        except ValueError:
                            continue

                    days_until = (schedule_date - today).days
                    if 0 <= days_until < min_days:
                        min_days = days_until
                        urgent_case = {
                            "id": case["id"],
                            "case_name": case["case_name"],
                            "crime_type": case["crime_type"],
                            "stage": case["stage"],
                            "next_schedule": {
                                "date": schedule_date.isoformat() if isinstance(schedule_date, date) else schedule_date,
                                "title": schedule.get("title", ""),
                                "schedule_type": schedule.get("schedule_type", "MEETING"),
                            },
                            "days_until_next": days_until
                        }

        # 긴급한 일정이 없으면 가장 최근 사건 반환
        if not urgent_case and cases:
            case = cases[0]  # 이미 created_at DESC로 정렬됨
            return {
                "id": case["id"],
                "case_name": case["case_name"],
                "crime_type": case["crime_type"],
                "stage": case["stage"],
            }

        return urgent_case

    def _get_next_schedule(self, case: Dict) -> Optional[ScheduleItem]:
        """다음 일정 조회"""
        today = date.today()
        schedules = case.get("schedules", [])

        for schedule in schedules:
            if schedule.get("is_completed"):
                continue

            schedule_date = schedule.get("date")
            if schedule_date:
                if isinstance(schedule_date, str):
                    try:
                        schedule_date = date.fromisoformat(schedule_date)
                    except ValueError:
                        continue

                if schedule_date >= today:
                    return ScheduleItem(
                        date=schedule_date,
                        title=schedule.get("title", ""),
                        schedule_type=schedule.get("schedule_type", "MEETING"),
                        description=schedule.get("description"),
                        is_completed=False
                    )

        return None

    async def get_similar_case_statistics(
        self,
        crime_type: str,
        conditions: List[str]
    ) -> SimilarCaseStatistics:
        """
        유사 사건 통계 조회

        - 판례 DB(Qdrant)에서 동일 crime_type + 조건 필터
        - 양형 분포 계산

        Note: 현재는 더미 데이터 반환 (판례 DB 연동 필요)
        """
        try:
            # TODO: Qdrant 판례 DB 연동
            # 현재는 더미 통계 반환

            # 더미 데이터
            distribution = {
                "suspended": 45.0,  # 집행유예 비율
                "fine": 25.0,       # 벌금 비율
                "imprisonment": 25.0,  # 실형 비율
                "acquittal": 5.0    # 무죄 비율
            }

            # 범죄 유형별 기본 통계 조정
            if crime_type == "절도":
                distribution = {
                    "suspended": 55.0,
                    "fine": 30.0,
                    "imprisonment": 12.0,
                    "acquittal": 3.0
                }
            elif crime_type == "사기":
                distribution = {
                    "suspended": 40.0,
                    "fine": 20.0,
                    "imprisonment": 35.0,
                    "acquittal": 5.0
                }
            elif crime_type == "폭행":
                distribution = {
                    "suspended": 50.0,
                    "fine": 35.0,
                    "imprisonment": 12.0,
                    "acquittal": 3.0
                }

            # 조건에 따른 조정
            if "초범" in conditions:
                distribution["suspended"] += 10
                distribution["imprisonment"] -= 10
            if "피해회복" in conditions:
                distribution["suspended"] += 5
                distribution["imprisonment"] -= 5
            if "동종전과" in conditions:
                distribution["suspended"] -= 15
                distribution["imprisonment"] += 15

            # 합계 100% 정규화
            total = sum(distribution.values())
            for key in distribution:
                distribution[key] = round(distribution[key] / total * 100, 1)

            return SimilarCaseStatistics(
                crime_type=crime_type,
                conditions=conditions,
                total_similar_cases=150,  # 더미
                distribution=distribution
            )

        except Exception as e:
            logger.error(f"Failed to get similar case statistics: {e}")
            raise
