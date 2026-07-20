"""One-shot, manual verification that a live ScrapeCreators response can flow
into the Data Pool.

Makes exactly ONE ScrapeCreators API request (Instagram hashtag search) —
do not add more calls here without a good reason, it spends real credits.

The field mapping below is a minimal, single-endpoint demo, not the full
Module 6 Data Normalizer (which still needs to handle every platform,
malformed-record handling, language detection, etc.).

Run from backend/: uv run python scripts/verify_data_pool_live.py
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.ingestion.data_pool import get_data_pool
from app.services.ingestion.normalizer.post_schema import EngagementStats, RawPost
from app.services.ingestion.scrapers.base import ScrapeCreatorsClient
from app.services.ingestion.scrapers.instagram import InstagramScraper

HASHTAG = "pizza"
LOG_PATH = Path(__file__).resolve().parent.parent / "data_pool_verification.log"
HASHTAG_PATTERN = re.compile(r"#(\w+)")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="w"), logging.StreamHandler()],
)
logger = logging.getLogger("data_pool_verification")


def to_raw_post(raw: dict[str, Any], source_hashtag: str) -> RawPost:
    taken_at = raw.get("taken_at")
    posted_at = datetime.fromisoformat(taken_at) if taken_at else datetime.now(UTC)

    caption = raw.get("caption") or ""
    owner = raw.get("owner") or {}

    return RawPost(
        platform="instagram",
        platform_post_id=raw.get("id") or raw.get("shortcode", ""),
        text=caption,
        media_url=raw.get("display_url") or raw.get("video_url"),
        media_type="video" if raw.get("is_video") else "image",
        engagement=EngagementStats(
            likes=raw.get("like_count") or 0,
            views=raw.get("video_view_count") or raw.get("video_play_count") or 0,
            comments=raw.get("comment_count") or 0,
        ),
        hashtags=HASHTAG_PATTERN.findall(caption),
        author_follower_count=owner.get("follower_count"),
        posted_at=posted_at,
        source_query=f"hashtag:{source_hashtag}",
    )


async def main() -> None:
    settings = get_settings()
    client = ScrapeCreatorsClient(
        api_key=settings.scrapecreators_api_key,
        base_url=settings.scrapecreators_base_url,
    )
    pool = get_data_pool()

    try:
        logger.info("Making ONE ScrapeCreators request: Instagram hashtag search for #%s", HASHTAG)
        scraper = InstagramScraper(client)
        result = scraper.search_hashtag(HASHTAG)
        logger.info(
            "Request succeeded — credits_remaining=%s, posts returned=%s",
            result.credits_remaining,
            len(result.posts),
        )

        raw_posts = [to_raw_post(post, HASHTAG) for post in result.posts]
        added = await pool.add_many(raw_posts)
        logger.info(
            "Added %s/%s posts to the Data Pool (rest were duplicates)", added, len(raw_posts)
        )
    finally:
        client.close()

    logger.info("=== Data Pool contents (%s posts) ===", pool.size)
    for post in pool.all_posts():
        logger.info(
            "platform=%s id=%s hashtags=%s engagement_rate=%.4f posted_at=%s text=%r",
            post.platform,
            post.platform_post_id,
            post.hashtags,
            post.engagement_rate(),
            post.posted_at.isoformat(),
            post.text[:80],
        )

    print(f"Data Pool length: {pool.size}")
    print(f"Full log written to: {LOG_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
