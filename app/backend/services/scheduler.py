"""
Scheduler Service
판례 크롤링 스케줄러 - 매주 월요일 자동 크롤링
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from typing import Optional

from app.backend.database import async_session
from app.backend.services.precedent_crawler import PrecedentCrawler
from app.backend.models.user import User

logger = logging.getLogger(__name__)


class PrecedentScheduler:
    """
    판례 크롤링 스케줄러
    - 매주 월요일 오전 9시: 사용자별 맞춤 판례 크롤링
    """

    def __init__(self, crawler: PrecedentCrawler):
        """
        Initialize scheduler

        Args:
            crawler: PrecedentCrawler instance
        """
        self.crawler = crawler
        self.scheduler = AsyncIOScheduler()
        self._setup_jobs()

    def _setup_jobs(self):
        """스케줄 작업 설정"""

        # 매주 월요일 오전 9시 - 사용자별 맞춤 판례 크롤링
        self.scheduler.add_job(
            self._weekly_personalized_crawl,
            trigger=CronTrigger(day_of_week='mon', hour=9, minute=0),
            id='weekly_personalized_crawl',
            name='Weekly personalized precedent crawling',
            replace_existing=True
        )

        # 매일 자정 - 최신 판례 10건 크롤링
        self.scheduler.add_job(
            self._daily_latest_crawl,
            trigger=CronTrigger(hour=0, minute=0),
            id='daily_latest_crawl',
            name='Daily latest precedent crawling',
            replace_existing=True
        )

        logger.info("Scheduler jobs configured successfully")

    async def _weekly_personalized_crawl(self):
        """
        매주 월요일 실행: 모든 활성 사용자의 전문분야 기반 판례 크롤링
        """
        logger.info("Starting weekly personalized precedent crawling...")

        try:
            async with async_session() as db:
                # 활성 사용자 조회
                result = await db.execute(
                    select(User).where(User.is_active == True)
                )
                users = result.scalars().all()

                if not users:
                    logger.info("No active users found for personalized crawling")
                    return

                total_stored = 0

                for user in users:
                    try:
                        # 사용자별 맞춤 판례 크롤링 (20건)
                        stored = await self.crawler.fetch_by_user_specializations(
                            db=db,
                            user_id=str(user.id),
                            limit=20
                        )
                        total_stored += stored

                        logger.info(
                            f"Crawled {stored} precedents for user {user.email} "
                            f"(specializations: {user.specializations})"
                        )

                    except Exception as e:
                        logger.error(f"Error crawling for user {user.email}: {e}")
                        continue

                logger.info(
                    f"Weekly personalized crawling completed. "
                    f"Total: {total_stored} precedents for {len(users)} users"
                )

        except Exception as e:
            logger.error(f"Error in weekly personalized crawl: {e}")

    async def _daily_latest_crawl(self):
        """
        매일 자정 실행: 최신 대법원 판례 10건 크롤링
        """
        logger.info("Starting daily latest precedent crawling...")

        try:
            async with async_session() as db:
                stored = await self.crawler.fetch_and_store_latest(
                    db=db,
                    limit=10,
                    case_type="형사"
                )

                logger.info(f"Daily latest crawling completed. Stored {stored} precedents")

        except Exception as e:
            logger.error(f"Error in daily latest crawl: {e}")

    def start(self):
        """스케줄러 시작"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Precedent crawler scheduler started")
        else:
            logger.warning("Scheduler is already running")

    def shutdown(self):
        """스케줄러 종료"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Precedent crawler scheduler shut down")

    async def run_initial_crawl(self):
        """
        초기 크롤링 실행 (앱 시작 시 한 번만)
        """
        logger.info("Running initial precedent crawl...")

        try:
            async with async_session() as db:
                # 최신 판례 10건 가져오기
                stored = await self.crawler.fetch_and_store_latest(
                    db=db,
                    limit=10,
                    case_type="형사"
                )

                logger.info(f"Initial crawl completed. Stored {stored} precedents")
                return stored

        except Exception as e:
            logger.error(f"Error in initial crawl: {e}")
            return 0

    def get_job_status(self) -> dict:
        """
        스케줄러 작업 상태 조회

        Returns:
            Dictionary with job status information
        """
        jobs = self.scheduler.get_jobs()

        status = {
            "scheduler_running": self.scheduler.running,
            "jobs": []
        }

        for job in jobs:
            status["jobs"].append({
                "id": job.id,
                "name": job.name,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            })

        return status
