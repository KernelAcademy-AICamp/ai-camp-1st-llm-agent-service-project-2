"""
Crawl Job Scheduler
APScheduler 기반 크롤링 스케줄러
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
import asyncio
import uuid

from pydantic import BaseModel

logger = logging.getLogger(__name__)

# APScheduler imports (optional - graceful fallback)
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    logger.warning("APScheduler not installed. Scheduling features disabled.")
    logger.warning("Install with: pip install apscheduler")


class ScheduleType(str, Enum):
    """스케줄 타입"""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    INTERVAL = "INTERVAL"


class ScheduledJob(BaseModel):
    """스케줄된 작업 정보"""
    job_id: str
    schedule_type: ScheduleType
    keywords: List[str]
    cron_expression: Optional[str] = None
    interval_minutes: Optional[int] = None
    next_run_time: Optional[datetime] = None
    last_run_time: Optional[datetime] = None
    is_active: bool = True
    created_at: datetime = datetime.utcnow()


class CrawlJobScheduler:
    """
    크롤링 스케줄러

    APScheduler를 사용한 정기 크롤링 스케줄 관리
    """

    def __init__(self, pipeline=None):
        """
        Initialize scheduler

        Args:
            pipeline: CrawlerPipeline instance (lazy injection possible)
        """
        self.pipeline = pipeline
        self.jobs: Dict[str, ScheduledJob] = {}
        self._scheduler = None
        self._is_running = False

        if APSCHEDULER_AVAILABLE:
            self._scheduler = AsyncIOScheduler(
                timezone='Asia/Seoul',
                job_defaults={
                    'coalesce': True,  # 놓친 작업 합치기
                    'max_instances': 1,  # 동시 실행 방지
                    'misfire_grace_time': 3600  # 1시간 유예
                }
            )
        else:
            logger.warning("Scheduler initialized without APScheduler")

    def set_pipeline(self, pipeline):
        """파이프라인 설정 (지연 주입)"""
        self.pipeline = pipeline
        logger.info("Pipeline set for scheduler")

    def start(self):
        """스케줄러 시작"""
        if not APSCHEDULER_AVAILABLE:
            logger.warning("Cannot start scheduler: APScheduler not available")
            return False

        if not self._is_running and self._scheduler:
            self._scheduler.start()
            self._is_running = True
            logger.info("Scheduler started")
            return True
        return False

    def stop(self):
        """스케줄러 중지"""
        if self._is_running and self._scheduler:
            self._scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Scheduler stopped")
            return True
        return False

    def add_daily_job(
        self,
        keywords: List[str],
        hour: int = 2,
        minute: int = 0,
        job_id: Optional[str] = None
    ) -> Optional[ScheduledJob]:
        """
        매일 실행 작업 추가

        Args:
            keywords: 검색 키워드 목록
            hour: 실행 시간 (0-23, 기본 새벽 2시)
            minute: 실행 분 (0-59)
            job_id: 작업 ID (없으면 자동 생성)

        Returns:
            ScheduledJob or None
        """
        if not APSCHEDULER_AVAILABLE or not self._scheduler:
            logger.warning("Cannot add job: Scheduler not available")
            return None

        job_id = job_id or f"daily_{uuid.uuid4().hex[:8]}"
        cron_expression = f"{minute} {hour} * * *"

        try:
            trigger = CronTrigger(hour=hour, minute=minute)

            self._scheduler.add_job(
                self._run_pipeline_job,
                trigger=trigger,
                id=job_id,
                args=[keywords],
                name=f"Daily crawl: {keywords}"
            )

            scheduled_job = ScheduledJob(
                job_id=job_id,
                schedule_type=ScheduleType.DAILY,
                keywords=keywords,
                cron_expression=cron_expression,
                is_active=True
            )

            # next_run_time 설정
            apscheduler_job = self._scheduler.get_job(job_id)
            if apscheduler_job:
                scheduled_job.next_run_time = apscheduler_job.next_run_time

            self.jobs[job_id] = scheduled_job
            logger.info(f"Added daily job: {job_id} at {hour}:{minute:02d}")

            return scheduled_job

        except Exception as e:
            logger.error(f"Failed to add daily job: {e}")
            return None

    def add_weekly_job(
        self,
        keywords: List[str],
        day_of_week: str = 'mon',
        hour: int = 2,
        minute: int = 0,
        job_id: Optional[str] = None
    ) -> Optional[ScheduledJob]:
        """
        매주 실행 작업 추가

        Args:
            keywords: 검색 키워드 목록
            day_of_week: 요일 (mon, tue, wed, thu, fri, sat, sun)
            hour: 실행 시간 (0-23)
            minute: 실행 분 (0-59)
            job_id: 작업 ID

        Returns:
            ScheduledJob or None
        """
        if not APSCHEDULER_AVAILABLE or not self._scheduler:
            return None

        job_id = job_id or f"weekly_{uuid.uuid4().hex[:8]}"
        cron_expression = f"{minute} {hour} * * {day_of_week}"

        try:
            trigger = CronTrigger(day_of_week=day_of_week, hour=hour, minute=minute)

            self._scheduler.add_job(
                self._run_pipeline_job,
                trigger=trigger,
                id=job_id,
                args=[keywords],
                name=f"Weekly crawl: {keywords}"
            )

            scheduled_job = ScheduledJob(
                job_id=job_id,
                schedule_type=ScheduleType.WEEKLY,
                keywords=keywords,
                cron_expression=cron_expression,
                is_active=True
            )

            apscheduler_job = self._scheduler.get_job(job_id)
            if apscheduler_job:
                scheduled_job.next_run_time = apscheduler_job.next_run_time

            self.jobs[job_id] = scheduled_job
            logger.info(f"Added weekly job: {job_id} on {day_of_week} at {hour}:{minute:02d}")

            return scheduled_job

        except Exception as e:
            logger.error(f"Failed to add weekly job: {e}")
            return None

    def add_monthly_job(
        self,
        keywords: List[str],
        day: int = 1,
        hour: int = 2,
        minute: int = 0,
        job_id: Optional[str] = None
    ) -> Optional[ScheduledJob]:
        """
        매월 실행 작업 추가

        Args:
            keywords: 검색 키워드 목록
            day: 일 (1-28 권장)
            hour: 실행 시간 (0-23)
            minute: 실행 분 (0-59)
            job_id: 작업 ID

        Returns:
            ScheduledJob or None
        """
        if not APSCHEDULER_AVAILABLE or not self._scheduler:
            return None

        job_id = job_id or f"monthly_{uuid.uuid4().hex[:8]}"
        cron_expression = f"{minute} {hour} {day} * *"

        try:
            trigger = CronTrigger(day=day, hour=hour, minute=minute)

            self._scheduler.add_job(
                self._run_pipeline_job,
                trigger=trigger,
                id=job_id,
                args=[keywords],
                name=f"Monthly crawl: {keywords}"
            )

            scheduled_job = ScheduledJob(
                job_id=job_id,
                schedule_type=ScheduleType.MONTHLY,
                keywords=keywords,
                cron_expression=cron_expression,
                is_active=True
            )

            apscheduler_job = self._scheduler.get_job(job_id)
            if apscheduler_job:
                scheduled_job.next_run_time = apscheduler_job.next_run_time

            self.jobs[job_id] = scheduled_job
            logger.info(f"Added monthly job: {job_id} on day {day} at {hour}:{minute:02d}")

            return scheduled_job

        except Exception as e:
            logger.error(f"Failed to add monthly job: {e}")
            return None

    def add_interval_job(
        self,
        keywords: List[str],
        minutes: int = 60,
        job_id: Optional[str] = None
    ) -> Optional[ScheduledJob]:
        """
        주기적 실행 작업 추가

        Args:
            keywords: 검색 키워드 목록
            minutes: 실행 주기 (분)
            job_id: 작업 ID

        Returns:
            ScheduledJob or None
        """
        if not APSCHEDULER_AVAILABLE or not self._scheduler:
            return None

        job_id = job_id or f"interval_{uuid.uuid4().hex[:8]}"

        try:
            trigger = IntervalTrigger(minutes=minutes)

            self._scheduler.add_job(
                self._run_pipeline_job,
                trigger=trigger,
                id=job_id,
                args=[keywords],
                name=f"Interval crawl: {keywords}"
            )

            scheduled_job = ScheduledJob(
                job_id=job_id,
                schedule_type=ScheduleType.INTERVAL,
                keywords=keywords,
                interval_minutes=minutes,
                is_active=True
            )

            apscheduler_job = self._scheduler.get_job(job_id)
            if apscheduler_job:
                scheduled_job.next_run_time = apscheduler_job.next_run_time

            self.jobs[job_id] = scheduled_job
            logger.info(f"Added interval job: {job_id} every {minutes} minutes")

            return scheduled_job

        except Exception as e:
            logger.error(f"Failed to add interval job: {e}")
            return None

    def remove_job(self, job_id: str) -> bool:
        """
        스케줄된 작업 제거

        Args:
            job_id: 작업 ID

        Returns:
            성공 여부
        """
        if job_id in self.jobs:
            try:
                if self._scheduler:
                    self._scheduler.remove_job(job_id)
                del self.jobs[job_id]
                logger.info(f"Removed job: {job_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to remove job {job_id}: {e}")
        return False

    def pause_job(self, job_id: str) -> bool:
        """작업 일시 중지"""
        if job_id in self.jobs and self._scheduler:
            try:
                self._scheduler.pause_job(job_id)
                self.jobs[job_id].is_active = False
                logger.info(f"Paused job: {job_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to pause job {job_id}: {e}")
        return False

    def resume_job(self, job_id: str) -> bool:
        """작업 재개"""
        if job_id in self.jobs and self._scheduler:
            try:
                self._scheduler.resume_job(job_id)
                self.jobs[job_id].is_active = True
                logger.info(f"Resumed job: {job_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to resume job {job_id}: {e}")
        return False

    def list_jobs(self) -> List[ScheduledJob]:
        """모든 스케줄된 작업 조회"""
        # next_run_time 업데이트
        if self._scheduler:
            for job_id, scheduled_job in self.jobs.items():
                apscheduler_job = self._scheduler.get_job(job_id)
                if apscheduler_job:
                    scheduled_job.next_run_time = apscheduler_job.next_run_time

        return list(self.jobs.values())

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """특정 작업 조회"""
        return self.jobs.get(job_id)

    async def _run_pipeline_job(self, keywords: List[str]):
        """파이프라인 실행 (스케줄러에서 호출)"""
        if not self.pipeline:
            logger.error("Pipeline not set for scheduler")
            return

        try:
            logger.info(f"Running scheduled crawl job: keywords={keywords}")

            result = await self.pipeline.run_full_pipeline(
                keywords=keywords,
                page=1,
                display=50,  # 스케줄 작업은 50개씩
                fetch_content=True
            )

            logger.info(
                f"Scheduled job completed: "
                f"crawled={result.crawled_count}, "
                f"new={result.new_count}, "
                f"indexed={result.indexed_count}"
            )

        except Exception as e:
            logger.error(f"Scheduled job failed: {e}", exc_info=True)

    def get_scheduler_status(self) -> Dict[str, Any]:
        """스케줄러 상태 조회"""
        return {
            'is_running': self._is_running,
            'apscheduler_available': APSCHEDULER_AVAILABLE,
            'total_jobs': len(self.jobs),
            'active_jobs': sum(1 for j in self.jobs.values() if j.is_active),
            'jobs': [
                {
                    'job_id': j.job_id,
                    'schedule_type': j.schedule_type,
                    'keywords': j.keywords,
                    'is_active': j.is_active,
                    'next_run_time': j.next_run_time.isoformat() if j.next_run_time else None
                }
                for j in self.jobs.values()
            ]
        }
