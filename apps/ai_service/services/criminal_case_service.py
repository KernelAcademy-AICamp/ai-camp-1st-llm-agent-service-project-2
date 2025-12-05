"""
Criminal Case Service
형사 사건 CRUD 서비스
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from uuid import uuid4
import logging
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from ..models.criminal_case import (
    CriminalStage,
    CriminalCaseCreate,
    CriminalCaseUpdate,
    CriminalCaseResponse,
    CriminalCaseListItem,
    CriminalCaseWithAnalysis,
    ScheduleItem,
    ScheduleItemCreate,
    ScheduleItemResponse,
)

logger = logging.getLogger(__name__)


class CriminalCaseService:
    """형사 사건 CRUD 서비스"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_cases(
        self,
        user_id: str,
        stage: Optional[CriminalStage] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[CriminalCaseListItem]:
        """사용자의 형사 사건 목록 조회"""
        try:
            query = """
                SELECT
                    id::text,
                    case_name,
                    crime_type,
                    stage,
                    schedules,
                    created_at
                FROM criminal_cases
                WHERE user_id = :user_id
            """
            params = {"user_id": user_id}

            if stage:
                query += " AND stage = :stage"
                params["stage"] = stage.value

            query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            params["limit"] = limit
            params["offset"] = offset

            result = await self.db.execute(text(query), params)
            rows = result.fetchall()

            cases = []
            for row in rows:
                # 다음 일정 추출
                next_schedule = None
                schedules = row.schedules or []
                today = date.today()

                for schedule in schedules:
                    if schedule.get("is_completed"):
                        continue
                    schedule_date = schedule.get("date")
                    if schedule_date:
                        if isinstance(schedule_date, str):
                            schedule_date = date.fromisoformat(schedule_date)
                        if schedule_date >= today:
                            next_schedule = ScheduleItem(
                                date=schedule_date,
                                title=schedule.get("title", ""),
                                schedule_type=schedule.get("schedule_type", "MEETING"),
                                description=schedule.get("description"),
                                is_completed=False
                            )
                            break

                cases.append(CriminalCaseListItem(
                    id=row.id,
                    case_name=row.case_name,
                    crime_type=row.crime_type,
                    stage=CriminalStage(row.stage),
                    next_schedule=next_schedule,
                    created_at=row.created_at
                ))

            return cases

        except Exception as e:
            logger.error(f"Failed to list criminal cases: {e}")
            raise

    async def get_case(
        self,
        case_id: str,
        user_id: str
    ) -> Optional[CriminalCaseResponse]:
        """형사 사건 상세 조회"""
        try:
            query = """
                SELECT
                    id::text,
                    user_id::text,
                    case_name,
                    summary,
                    crime_type,
                    crime_elements,
                    sentencing_factors,
                    expected_sentence,
                    defense_strategies,
                    related_precedents,
                    stage,
                    schedules,
                    conditions,
                    uploaded_files,
                    created_at,
                    updated_at
                FROM criminal_cases
                WHERE id = :case_id AND user_id = :user_id
            """

            result = await self.db.execute(
                text(query),
                {"case_id": case_id, "user_id": user_id}
            )
            row = result.fetchone()

            if not row:
                return None

            return CriminalCaseResponse(
                id=row.id,
                user_id=row.user_id,
                case_name=row.case_name,
                summary=row.summary or "",
                crime_type=row.crime_type,
                crime_elements=row.crime_elements or {},
                sentencing_factors=row.sentencing_factors or {},
                expected_sentence=row.expected_sentence or {},
                defense_strategies=row.defense_strategies or [],
                related_precedents=row.related_precedents or [],
                stage=CriminalStage(row.stage),
                schedules=row.schedules or [],
                conditions=row.conditions or [],
                uploaded_files=row.uploaded_files or [],
                created_at=row.created_at,
                updated_at=row.updated_at
            )

        except Exception as e:
            logger.error(f"Failed to get criminal case {case_id}: {e}")
            raise

    async def create_case(
        self,
        user_id: str,
        data: CriminalCaseCreate
    ) -> CriminalCaseResponse:
        """형사 사건 생성"""
        try:
            case_id = str(uuid4())
            now = datetime.utcnow()

            # 일정 직렬화
            schedules_json = [
                {
                    "date": s.date.isoformat(),
                    "title": s.title,
                    "schedule_type": s.schedule_type.value,
                    "description": s.description,
                    "is_completed": s.is_completed
                }
                for s in data.schedules
            ]

            query = """
                INSERT INTO criminal_cases (
                    id, user_id, case_name, summary, crime_type,
                    crime_elements, sentencing_factors, expected_sentence,
                    defense_strategies, related_precedents, stage,
                    schedules, conditions, uploaded_files, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :case_name, :summary, :crime_type,
                    :crime_elements, :sentencing_factors, :expected_sentence,
                    :defense_strategies, :related_precedents, :stage,
                    :schedules, :conditions, :uploaded_files, :created_at, :updated_at
                )
            """

            await self.db.execute(
                text(query),
                {
                    "id": case_id,
                    "user_id": user_id,
                    "case_name": data.case_name,
                    "summary": data.summary or "",
                    "crime_type": data.crime_type,
                    "crime_elements": "{}",
                    "sentencing_factors": "{}",
                    "expected_sentence": "{}",
                    "defense_strategies": "[]",
                    "related_precedents": "[]",
                    "stage": data.stage.value,
                    "schedules": json.dumps(schedules_json, ensure_ascii=False) if schedules_json else "[]",
                    "conditions": json.dumps(data.conditions, ensure_ascii=False) if data.conditions else "[]",
                    "uploaded_files": "[]",
                    "created_at": now,
                    "updated_at": now
                }
            )
            await self.db.commit()

            return await self.get_case(case_id, user_id)

        except Exception as e:
            logger.error(f"Failed to create criminal case: {e}")
            await self.db.rollback()
            raise

    async def create_case_with_analysis(
        self,
        user_id: str,
        data: CriminalCaseWithAnalysis
    ) -> CriminalCaseResponse:
        """분석 결과와 함께 형사 사건 생성"""
        try:
            case_id = str(uuid4())
            now = datetime.utcnow()

            # 일정 직렬화
            schedules_json = [
                {
                    "date": s.date.isoformat(),
                    "title": s.title,
                    "schedule_type": s.schedule_type.value,
                    "description": s.description,
                    "is_completed": s.is_completed
                }
                for s in data.schedules
            ]

            query = """
                INSERT INTO criminal_cases (
                    id, user_id, case_name, summary, crime_type,
                    crime_elements, sentencing_factors, expected_sentence,
                    defense_strategies, related_precedents, stage,
                    schedules, conditions, uploaded_files, created_at, updated_at
                ) VALUES (
                    :id, :user_id, :case_name, :summary, :crime_type,
                    :crime_elements, :sentencing_factors, :expected_sentence,
                    :defense_strategies, :related_precedents, :stage,
                    :schedules, :conditions, :uploaded_files, :created_at, :updated_at
                )
            """

            await self.db.execute(
                text(query),
                {
                    "id": case_id,
                    "user_id": user_id,
                    "case_name": data.case_name,
                    "summary": data.summary or "",
                    "crime_type": data.crime_type,
                    "crime_elements": json.dumps(data.crime_elements, ensure_ascii=False),
                    "sentencing_factors": json.dumps(data.sentencing_factors, ensure_ascii=False),
                    "expected_sentence": json.dumps(data.expected_sentence, ensure_ascii=False),
                    "defense_strategies": json.dumps(data.defense_strategies, ensure_ascii=False),
                    "related_precedents": json.dumps(data.related_precedents, ensure_ascii=False),
                    "stage": data.stage.value,
                    "schedules": json.dumps(schedules_json, ensure_ascii=False),
                    "conditions": json.dumps(data.conditions, ensure_ascii=False),
                    "uploaded_files": json.dumps(data.uploaded_files, ensure_ascii=False),
                    "created_at": now,
                    "updated_at": now
                }
            )
            await self.db.commit()

            return await self.get_case(case_id, user_id)

        except Exception as e:
            logger.error(f"Failed to create criminal case with analysis: {e}")
            await self.db.rollback()
            raise

    async def update_case(
        self,
        case_id: str,
        user_id: str,
        data: CriminalCaseUpdate
    ) -> Optional[CriminalCaseResponse]:
        """형사 사건 수정"""
        try:
            # 먼저 기존 데이터 확인
            existing = await self.get_case(case_id, user_id)
            if not existing:
                return None

            # 업데이트할 필드 구성
            update_fields = []
            params = {"case_id": case_id, "user_id": user_id}

            if data.case_name is not None:
                update_fields.append("case_name = :case_name")
                params["case_name"] = data.case_name

            if data.summary is not None:
                update_fields.append("summary = :summary")
                params["summary"] = data.summary

            if data.stage is not None:
                update_fields.append("stage = :stage")
                params["stage"] = data.stage.value

            if data.conditions is not None:
                update_fields.append("conditions = :conditions")
                params["conditions"] = json.dumps(data.conditions, ensure_ascii=False)

            if data.schedules is not None:
                schedules_json = [
                    {
                        "date": s.date.isoformat(),
                        "title": s.title,
                        "schedule_type": s.schedule_type.value,
                        "description": s.description,
                        "is_completed": s.is_completed
                    }
                    for s in data.schedules
                ]
                update_fields.append("schedules = :schedules")
                params["schedules"] = json.dumps(schedules_json, ensure_ascii=False)

            if data.crime_elements is not None:
                update_fields.append("crime_elements = :crime_elements")
                params["crime_elements"] = json.dumps(data.crime_elements, ensure_ascii=False)

            if data.sentencing_factors is not None:
                update_fields.append("sentencing_factors = :sentencing_factors")
                params["sentencing_factors"] = json.dumps(data.sentencing_factors, ensure_ascii=False)

            if data.expected_sentence is not None:
                update_fields.append("expected_sentence = :expected_sentence")
                params["expected_sentence"] = json.dumps(data.expected_sentence, ensure_ascii=False)

            if data.defense_strategies is not None:
                update_fields.append("defense_strategies = :defense_strategies")
                params["defense_strategies"] = json.dumps(data.defense_strategies, ensure_ascii=False)

            if data.related_precedents is not None:
                update_fields.append("related_precedents = :related_precedents")
                params["related_precedents"] = json.dumps(data.related_precedents, ensure_ascii=False)

            if not update_fields:
                return existing

            update_fields.append("updated_at = :updated_at")
            params["updated_at"] = datetime.utcnow()

            query = f"""
                UPDATE criminal_cases
                SET {', '.join(update_fields)}
                WHERE id = :case_id AND user_id = :user_id
            """

            await self.db.execute(text(query), params)
            await self.db.commit()

            return await self.get_case(case_id, user_id)

        except Exception as e:
            logger.error(f"Failed to update criminal case {case_id}: {e}")
            await self.db.rollback()
            raise

    async def delete_case(
        self,
        case_id: str,
        user_id: str
    ) -> bool:
        """형사 사건 삭제"""
        try:
            # 먼저 일정 삭제
            await self.db.execute(
                text("DELETE FROM criminal_case_schedules WHERE case_id = :case_id"),
                {"case_id": case_id}
            )

            # 사건 삭제
            result = await self.db.execute(
                text("DELETE FROM criminal_cases WHERE id = :case_id AND user_id = :user_id"),
                {"case_id": case_id, "user_id": user_id}
            )
            await self.db.commit()

            return result.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to delete criminal case {case_id}: {e}")
            await self.db.rollback()
            raise

    async def add_schedule(
        self,
        case_id: str,
        user_id: str,
        schedule: ScheduleItemCreate
    ) -> Optional[CriminalCaseResponse]:
        """일정 추가"""
        try:
            # 기존 사건 조회
            existing = await self.get_case(case_id, user_id)
            if not existing:
                return None

            # 일정 추가
            schedules = existing.schedules or []
            new_schedule = {
                "date": schedule.date.isoformat(),
                "title": schedule.title,
                "schedule_type": schedule.schedule_type.value,
                "description": schedule.description,
                "is_completed": False
            }
            schedules.append(new_schedule)

            # 날짜순 정렬
            schedules.sort(key=lambda x: x.get("date", ""))

            # 업데이트
            query = """
                UPDATE criminal_cases
                SET schedules = :schedules, updated_at = :updated_at
                WHERE id = :case_id AND user_id = :user_id
            """
            await self.db.execute(
                text(query),
                {
                    "schedules": json.dumps(schedules, ensure_ascii=False),
                    "updated_at": datetime.utcnow(),
                    "case_id": case_id,
                    "user_id": user_id
                }
            )
            await self.db.commit()

            return await self.get_case(case_id, user_id)

        except Exception as e:
            logger.error(f"Failed to add schedule to case {case_id}: {e}")
            await self.db.rollback()
            raise

    async def update_schedule_status(
        self,
        case_id: str,
        user_id: str,
        schedule_index: int,
        is_completed: bool
    ) -> Optional[CriminalCaseResponse]:
        """일정 완료 상태 업데이트"""
        try:
            existing = await self.get_case(case_id, user_id)
            if not existing:
                return None

            schedules = existing.schedules or []
            if schedule_index < 0 or schedule_index >= len(schedules):
                raise ValueError(f"Invalid schedule index: {schedule_index}")

            schedules[schedule_index]["is_completed"] = is_completed

            query = """
                UPDATE criminal_cases
                SET schedules = :schedules, updated_at = :updated_at
                WHERE id = :case_id AND user_id = :user_id
            """
            await self.db.execute(
                text(query),
                {
                    "schedules": json.dumps(schedules, ensure_ascii=False),
                    "updated_at": datetime.utcnow(),
                    "case_id": case_id,
                    "user_id": user_id
                }
            )
            await self.db.commit()

            return await self.get_case(case_id, user_id)

        except Exception as e:
            logger.error(f"Failed to update schedule status: {e}")
            await self.db.rollback()
            raise

    async def list_cases_full(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[CriminalCaseResponse]:
        """대시보드용 전체 상세 정보 포함 사건 목록 조회"""
        try:
            query = """
                SELECT
                    id::text,
                    user_id::text,
                    case_name,
                    summary,
                    crime_type,
                    crime_elements,
                    sentencing_factors,
                    expected_sentence,
                    defense_strategies,
                    related_precedents,
                    stage,
                    schedules,
                    conditions,
                    uploaded_files,
                    created_at,
                    updated_at
                FROM criminal_cases
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT :limit
            """

            result = await self.db.execute(
                text(query),
                {"user_id": user_id, "limit": limit}
            )
            rows = result.fetchall()

            cases = []
            for row in rows:
                cases.append(CriminalCaseResponse(
                    id=row.id,
                    user_id=row.user_id,
                    case_name=row.case_name,
                    summary=row.summary or "",
                    crime_type=row.crime_type,
                    crime_elements=row.crime_elements or {},
                    sentencing_factors=row.sentencing_factors or {},
                    expected_sentence=row.expected_sentence or {},
                    defense_strategies=row.defense_strategies or [],
                    related_precedents=row.related_precedents or [],
                    stage=CriminalStage(row.stage),
                    schedules=row.schedules or [],
                    conditions=row.conditions or [],
                    uploaded_files=row.uploaded_files or [],
                    created_at=row.created_at,
                    updated_at=row.updated_at
                ))

            return cases

        except Exception as e:
            logger.error(f"Failed to list full criminal cases: {e}")
            raise

    async def get_cases_by_stage(
        self,
        user_id: str
    ) -> Dict[str, int]:
        """단계별 사건 수 집계"""
        try:
            query = """
                SELECT stage, COUNT(*) as count
                FROM criminal_cases
                WHERE user_id = :user_id
                GROUP BY stage
            """

            result = await self.db.execute(text(query), {"user_id": user_id})
            rows = result.fetchall()

            # 모든 단계 초기화
            counts = {stage.value: 0 for stage in CriminalStage}
            for row in rows:
                counts[row.stage] = row.count

            return counts

        except Exception as e:
            logger.error(f"Failed to get cases by stage: {e}")
            raise
