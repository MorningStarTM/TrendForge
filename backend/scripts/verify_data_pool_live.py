"""One-shot, manual verification that a live ScrapeCreators response can flow
through the real Data Normalizer pipeline into the Data Pool.

Makes exactly ONE ScrapeCreators API request (Instagram hashtag search) —
do not add more calls here without a good reason, it spends real credits.

Run from backend/: uv run python scripts/verify_data_pool_live.py
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.core.config import get_settings
from app.services.ingestion.data_pool import get_data_pool
from app.services.ingestion.normalizer.dead_letter import get_dead_letter_queue
from app.services.ingestion.normalizer.pipeline import normalize_and_ingest
from app.services.ingestion.scrapers.base import ScrapeCreatorsClient
from app.services.ingestion.scrapers.instagram import InstagramScraper

HASHTAG = "pizza"
LOG_PATH = Path(__file__).resolve().parent.parent / "data_pool_verification.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="w"), logging.StreamHandler()],
)
logger = logging.getLogger("data_pool_verification")


async def main() -> None:
    settings = get_settings()
    client = ScrapeCreatorsClient(
        api_key=settings.scrapecreators_api_key,
        base_url=settings.scrapecreators_base_url,
    )
    pool = get_data_pool()
    dead_letters = get_dead_letter_queue()

    try:
        logger.info("Making ONE ScrapeCreators request: Instagram hashtag search for #%s", HASHTAG)
        scraper = InstagramScraper(client)
        result = scraper.search_hashtag(HASHTAG)
        logger.info(
            "Request succeeded — credits_remaining=%s, posts returned=%s",
            result.credits_remaining,
            len(result.posts),
        )

        summary = await normalize_and_ingest(
            "instagram",
            result.posts,
            source_query=f"hashtag:{HASHTAG}",
            pool=pool,
            dead_letters=dead_letters,
        )
        logger.info(
            "Normalized: received=%s malformed=%s added_to_pool=%s duplicates=%s",
            summary.received,
            summary.malformed,
            summary.added_to_pool,
            summary.duplicates,
        )
    finally:
        client.close()

    logger.info("=== Data Pool contents (%s posts) ===", pool.size)
    for post in pool.all_posts():
        logger.info(
            "platform=%s id=%s language=%s hashtags=%s engagement_rate=%.4f posted_at=%s text=%r",
            post.platform,
            post.platform_post_id,
            post.language,
            post.hashtags,
            post.engagement_rate,
            post.posted_at.isoformat(),
            post.text[:80],
        )

    if dead_letters.size:
        logger.info("=== Dead Letter Queue contents (%s records) ===", dead_letters.size)
        for record in dead_letters.all():
            logger.info("platform=%s reason=%s raw=%r", record.platform, record.reason, record.raw)

    print(f"Data Pool length: {pool.size}")
    print(f"Dead Letter Queue length: {dead_letters.size}")
    print(f"Full log written to: {LOG_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
