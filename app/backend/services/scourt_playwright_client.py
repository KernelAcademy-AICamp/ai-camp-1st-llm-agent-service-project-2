"""
Supreme Court Portal Playwright Client
대법원 사법정보공개포털 Playwright 기반 크롤링 클라이언트
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeoutError

from app.backend.services.rate_limiter import RateLimiter, RequestCounter

logger = logging.getLogger(__name__)


class ScourtPlaywrightClient:
    """
    대법원 포털 Playwright 기반 크롤링 클라이언트

    Safety Features:
    - Rate limiting (1 request per second)
    - Timeout protection (10 seconds)
    - Maximum retry limit (2 times)
    - Maximum consecutive requests (10)
    """

    BASE_URL = "https://portal.scourt.go.kr/pgp/index.on?m=PGP1011M01&l=N&c=900"
    MAX_PRECEDENTS_PER_REQUEST = 10  # Hard limit
    TIMEOUT = 10000  # 10 seconds
    MAX_RETRIES = 2

    def __init__(self):
        """Initialize Playwright client with safety features"""
        self.rate_limiter = RateLimiter(min_interval=1.0)  # 1 second between requests
        self.request_counter = RequestCounter(max_requests=10)  # Max 10 consecutive requests
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def start(self):
        """Start browser instance"""
        try:
            logger.info("Starting Playwright browser...")
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox']
            )
            self.page = await self.browser.new_page()
            self.page.set_default_timeout(self.TIMEOUT)
            logger.info("Browser started successfully")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise

    async def close(self):
        """Close browser instance"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            logger.info("Browser closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def search_precedents_by_keyword(
        self,
        keyword: str,
        max_count: int = 10
    ) -> List[Dict]:
        """
        키워드로 판례 검색 (최대 10개)

        Args:
            keyword: 검색 키워드
            max_count: 최대 조회 건수 (10개 제한)

        Returns:
            List of precedent dictionaries
        """
        # Hard limit enforcement - maximum 10 precedents for keyword search
        if max_count > 10:
            logger.warning(f"Requested {max_count} precedents, limiting to 10 for keyword search")
            max_count = 10

        # Check request counter
        if not await self.request_counter.increment():
            logger.error("Request limit exceeded")
            return []

        retry_count = 0
        precedents = []

        while retry_count <= self.MAX_RETRIES:
            try:
                # Rate limiting
                await self.rate_limiter.wait()

                logger.info(f"Searching for precedents with keyword '{keyword}' (attempt {retry_count + 1}/{self.MAX_RETRIES + 1})")

                # Navigate to page
                await self.page.goto(self.BASE_URL, wait_until="networkidle", timeout=30000)

                # Wait for Websquare framework to initialize
                logger.info("Waiting for page to load...")
                await asyncio.sleep(5)

                # Find search input and enter keyword
                logger.info(f"Entering keyword: {keyword}")
                search_input = await self.page.wait_for_selector('input[placeholder*="검색어"]', timeout=10000)
                await search_input.fill(keyword)

                # Find and click search button
                logger.info("Clicking search button...")
                search_button = await self.page.wait_for_selector('button:has-text("검색")', timeout=10000)
                await search_button.click()

                # Wait for search results to load
                logger.info("Waiting for search results...")
                await asyncio.sleep(5)

                # Extract precedent data
                precedents = await self._extract_precedents(max_count)

                if precedents:
                    logger.info(f"Successfully fetched {len(precedents)} precedents")
                    return precedents
                else:
                    logger.warning("No precedents found")
                    return []

            except PlaywrightTimeoutError as e:
                retry_count += 1
                logger.warning(f"Timeout error (attempt {retry_count}/{self.MAX_RETRIES + 1}): {e}")

                if retry_count > self.MAX_RETRIES:
                    logger.error("Max retries exceeded")
                    return []

                # Exponential backoff
                wait_time = 2 ** retry_count
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)

            except Exception as e:
                logger.error(f"Unexpected error fetching precedents: {e}")
                return []

        return precedents

    async def _extract_precedents(self, max_count: int) -> List[Dict]:
        """
        Extract precedent data from page

        Args:
            max_count: Maximum number of precedents to extract

        Returns:
            List of precedent dictionaries
        """
        try:
            precedents = []

            # Find all precedent rows
            rows = await self.page.query_selector_all('table tbody tr')
            logger.info(f"Found {len(rows)} precedent rows")

            for i, row in enumerate(rows[:max_count]):  # Limit to max_count
                try:
                    # Get all cells
                    cells = await row.query_selector_all('td')
                    if len(cells) < 2:
                        continue

                    # First cell is just a number (NO)
                    # Second cell contains all the precedent information
                    content_cell = cells[1] if len(cells) > 1 else cells[0]

                    # Extract link and title from the anchor tag
                    link_elem = await content_cell.query_selector('a')
                    if not link_elem:
                        continue

                    # Get full text content which includes: court date case_number [charges] title
                    full_text = await link_elem.inner_text()

                    # Extract link (for precedent_id)
                    link = await link_elem.get_attribute('href')
                    precedent_id = self._extract_precedent_id(link) if link else ""

                    # Parse the text to extract components
                    # Format: "대법원 2025.09.04 선고 2025도9690 판결 [charges] title"
                    parts = full_text.strip().split(maxsplit=3)

                    court = parts[0] if len(parts) > 0 else "대법원"
                    date_str = parts[1] if len(parts) > 1 else ""
                    # Skip "선고" (parts[2])
                    case_and_rest = parts[3] if len(parts) > 3 else ""

                    # Extract case number (before "판결")
                    case_number = ""
                    title = case_and_rest
                    if "판결" in case_and_rest:
                        case_part = case_and_rest.split("판결")[0].strip()
                        # Case number is before the first [
                        if "[" in case_part:
                            case_number = case_part.split("[")[0].strip()
                        else:
                            case_number = case_part

                    decision_date = self._parse_date(date_str)

                    if case_number and title:
                        precedent = {
                            "precedent_id": precedent_id,
                            "case_number": case_number,
                            "title": title[:200],  # Limit title length
                            "court": court,
                            "decision_date": decision_date,
                            "summary": "",  # Will be fetched separately if needed
                        }
                        precedents.append(precedent)
                        logger.info(f"Extracted precedent: {case_number}")

                except Exception as e:
                    logger.warning(f"Error extracting precedent {i}: {e}")
                    continue

            return precedents

        except Exception as e:
            logger.error(f"Error in _extract_precedents: {e}")
            return []

    def _extract_precedent_id(self, link: str) -> str:
        """Extract precedent ID from link"""
        try:
            if 'jisCntntsSrno=' in link:
                return link.split('jisCntntsSrno=')[1].split('&')[0]
        except:
            pass
        return ""

    def _parse_date(self, date_str: str) -> datetime:
        """Parse date string to datetime"""
        try:
            # Try different date formats
            date_str = date_str.strip().replace('.', '-')

            if len(date_str) == 10:  # YYYY-MM-DD
                return datetime.strptime(date_str, '%Y-%m-%d')
            elif len(date_str) == 8:  # YYYYMMDD
                return datetime.strptime(date_str, '%Y%m%d')
        except:
            pass

        return datetime.now()

    async def reset_counter(self):
        """Reset request counter"""
        await self.request_counter.reset()


async def test_client():
    """Test function for Playwright client"""
    async with ScourtPlaywrightClient() as client:
        # Test keyword search
        keyword = "형사"
        precedents = await client.search_precedents_by_keyword(keyword=keyword, max_count=1)

        print(f"\nSearched for '{keyword}', fetched {len(precedents)} precedent(s):")
        for i, prec in enumerate(precedents, 1):
            print(f"{i}. {prec['case_number']} - {prec['title'][:50]}...")


if __name__ == "__main__":
    asyncio.run(test_client())
