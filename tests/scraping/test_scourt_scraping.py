"""
Test script for Supreme Court Portal scraping
대법원 포털 웹 스크래핑 테스트 스크립트
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.backend.services.scourt_client import ScourtClient
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_connection():
    """Test connection to Supreme Court Portal"""
    logger.info("=" * 50)
    logger.info("Testing connection to Supreme Court Portal...")
    logger.info("=" * 50)

    client = ScourtClient()
    result = client.test_connection()

    if result:
        logger.info("✅ Connection test PASSED")
    else:
        logger.error("❌ Connection test FAILED")

    return result


def test_search_precedents():
    """Test searching precedents"""
    logger.info("\n" + "=" * 50)
    logger.info("Testing precedent search...")
    logger.info("=" * 50)

    client = ScourtClient()

    # Test 1: Search by keyword
    logger.info("\nTest 1: Searching for '형사' precedents...")
    results = client.search_precedents(keyword="형사", limit=5)

    if results:
        logger.info(f"✅ Found {len(results)} precedents")
        for i, prec in enumerate(results, 1):
            logger.info(f"  {i}. {prec.get('case_number', 'N/A')} - {prec.get('title', 'N/A')[:50]}...")
    else:
        logger.warning("⚠️  No precedents found")

    # Test 2: Search by case type
    logger.info("\nTest 2: Searching for criminal cases...")
    results = client.search_precedents(case_type="형사", limit=3)

    if results:
        logger.info(f"✅ Found {len(results)} criminal precedents")
    else:
        logger.warning("⚠️  No criminal precedents found")

    return len(results) > 0


def test_fetch_detail():
    """Test fetching precedent details"""
    logger.info("\n" + "=" * 50)
    logger.info("Testing precedent detail fetching...")
    logger.info("=" * 50)

    client = ScourtClient()

    # First, get a precedent to test detail fetching
    logger.info("\nFetching sample precedent...")
    precedents = client.search_precedents(limit=1)

    if not precedents:
        logger.warning("⚠️  No precedents available for detail testing")
        return False

    sample_prec = precedents[0]
    precedent_id = sample_prec.get("precedent_id")

    if not precedent_id:
        logger.warning("⚠️  Sample precedent has no ID")
        return False

    logger.info(f"\nFetching detail for: {sample_prec.get('case_number', 'N/A')}")
    detail = client.fetch_precedent_detail(precedent_id)

    if detail:
        logger.info("✅ Successfully fetched precedent detail")
        logger.info(f"  - Case Number: {detail.get('case_number', 'N/A')}")
        logger.info(f"  - Title: {detail.get('title', 'N/A')[:50]}...")
        logger.info(f"  - Court: {detail.get('court', 'N/A')}")
        logger.info(f"  - Has Full Text: {'Yes' if detail.get('full_text') else 'No'}")
        logger.info(f"  - Has Judgment Summary: {'Yes' if detail.get('judgment_summary') else 'No'}")
        return True
    else:
        logger.error("❌ Failed to fetch precedent detail")
        return False


def test_related_data():
    """Test fetching related data (reference statutes, precedents)"""
    logger.info("\n" + "=" * 50)
    logger.info("Testing related data fetching...")
    logger.info("=" * 50)

    client = ScourtClient()

    # Get a sample precedent
    precedents = client.search_precedents(limit=1)
    if not precedents:
        logger.warning("⚠️  No precedents available for related data testing")
        return False

    precedent_id = precedents[0].get("precedent_id")
    if not precedent_id:
        logger.warning("⚠️  No precedent ID available")
        return False

    logger.info(f"\nFetching related data for: {precedents[0].get('case_number', 'N/A')}")
    related = client.fetch_related_data(precedent_id)

    if related:
        logger.info("✅ Successfully fetched related data")
        logger.info(f"  - Reference Statutes: {len(related.get('reference_statutes', []))}")
        logger.info(f"  - Reference Precedents: {len(related.get('reference_precedents', []))}")
        return True
    else:
        logger.warning("⚠️  No related data found")
        return False


def main():
    """Run all tests"""
    logger.info("\n" + "=" * 70)
    logger.info("Supreme Court Portal Scraping Test Suite")
    logger.info("=" * 70)

    results = {
        "Connection Test": test_connection(),
        "Search Test": test_search_precedents(),
        "Detail Fetch Test": test_fetch_detail(),
        "Related Data Test": test_related_data(),
    }

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)

    passed = sum(1 for r in results.values() if r)
    total = len(results)

    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        logger.info(f"{test_name}: {status}")

    logger.info(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        logger.info("\n🎉 All tests passed!")
        return 0
    else:
        logger.error(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
