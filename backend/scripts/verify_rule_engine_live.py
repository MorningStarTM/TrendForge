"""One-shot, manual verification of the full pipeline against live data:

ScrapeCreators (3 requests) -> Normalizer -> Data Pool -> Rule Engine.

Makes exactly 3 requests total (Instagram hashtag search, TikTok hashtag
search, YouTube search), all for the same topic so the Data Pool has a
realistic chance at cross-platform signals. Do not add more calls here
without a good reason — it spends real credits.

Logs, per platform: raw posts pulled by that single request, and how many
of those posts had zero hashtags extracted (a diagnostic for why a
candidate might under-represent a platform). Ranks the top 10 candidates
and logs each underlying post's likes/comments/views.

Run from backend/: uv run python scripts/verify_rule_engine_live.py
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.core.config import get_settings
from app.services.ingestion.data_pool import get_data_pool
from app.services.ingestion.normalizer.dead_letter import get_dead_letter_queue
from app.services.ingestion.normalizer.pipeline import normalize_and_ingest
from app.services.ingestion.normalizer.post_schema import RawPost
from app.services.ingestion.scrapers.base import ScrapeCreatorsClient
from app.services.ingestion.scrapers.instagram import InstagramScraper
from app.services.ingestion.scrapers.tiktok import TikTokScraper
from app.services.ingestion.scrapers.youtube import YouTubeScraper
from app.services.trend_engine.rule_engine.engine import run_rule_engine

TOPIC = "pizza"
TOP_N = 10
LOG_PATH = Path(__file__).resolve().parent.parent / "rule_engine_verification.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="w"), logging.StreamHandler()],
)
logger = logging.getLogger("rule_engine_verification")

platform_pull_counts: dict[str, int] = {}
platform_no_hashtag_counts: dict[str, int] = {}


def _track_hashtag_coverage(
    platform: str, pool_posts_before: int, pool_posts_after: list[RawPost]
) -> None:
    added = pool_posts_after[pool_posts_before:]
    platform_no_hashtag_counts[platform] = sum(1 for post in added if not post.hashtags)


async def main() -> None:
    settings = get_settings()
    client = ScrapeCreatorsClient(
        api_key=settings.scrapecreators_api_key,
        base_url=settings.scrapecreators_base_url,
    )
    pool = get_data_pool()
    dead_letters = get_dead_letter_queue()

    try:
        logger.info("Request 1/3: Instagram hashtag search for #%s", TOPIC)
        ig_result = InstagramScraper(client).search_hashtag(TOPIC)
        platform_pull_counts["instagram"] = len(ig_result.posts)
        logger.info(
            "Instagram: credits_remaining=%s posts_pulled=%s",
            ig_result.credits_remaining,
            len(ig_result.posts),
        )
        before = pool.size
        ig_summary = await normalize_and_ingest(
            "instagram",
            ig_result.posts,
            source_query=f"hashtag:{TOPIC}",
            pool=pool,
            dead_letters=dead_letters,
        )
        _track_hashtag_coverage("instagram", before, pool.all_posts())
        logger.info("Instagram normalized: %s", ig_summary)

        logger.info("Request 2/3: TikTok hashtag search for #%s", TOPIC)
        tt_result = TikTokScraper(client).search_hashtag(TOPIC)
        platform_pull_counts["tiktok"] = len(tt_result.aweme_list)
        logger.info("TikTok: videos_pulled=%s", len(tt_result.aweme_list))
        before = pool.size
        tt_summary = await normalize_and_ingest(
            "tiktok",
            tt_result.aweme_list,
            source_query=f"hashtag:{TOPIC}",
            pool=pool,
            dead_letters=dead_letters,
        )
        _track_hashtag_coverage("tiktok", before, pool.all_posts())
        logger.info("TikTok normalized: %s", tt_summary)

        logger.info("Request 3/3: YouTube search for %s", TOPIC)
        yt_result = YouTubeScraper(client).search(TOPIC)
        yt_items = yt_result.videos + yt_result.shorts
        platform_pull_counts["youtube"] = len(yt_items)
        logger.info("YouTube: videos+shorts_pulled=%s", len(yt_items))
        before = pool.size
        yt_summary = await normalize_and_ingest(
            "youtube",
            yt_items,
            source_query=f"keyword:{TOPIC}",
            pool=pool,
            dead_letters=dead_letters,
        )
        _track_hashtag_coverage("youtube", before, pool.all_posts())
        logger.info("YouTube normalized: %s", yt_summary)
    finally:
        client.close()

    logger.info("========== SUMMARY: raw posts pulled per platform ==========")
    for platform, count in platform_pull_counts.items():
        no_hashtag = platform_no_hashtag_counts.get(platform, 0)
        logger.info(
            "  %-10s pulled=%-4s added_to_pool_with_zero_hashtags=%s",
            platform,
            count,
            no_hashtag,
        )
    logger.info("  TOTAL pulled=%s", sum(platform_pull_counts.values()))
    logger.info("=== Data Pool size: %s ===", pool.size)
    logger.info("=== Dead Letter Queue size: %s ===", dead_letters.size)
    for record in dead_letters.all():
        logger.info("dead letter: platform=%s reason=%s", record.platform, record.reason)

    result = run_rule_engine(pool, top_n=TOP_N)
    logger.info(
        "=== Rule Engine: built=%s passed=%s blacklisted=%s not_selected=%s ===",
        result.candidates_built,
        len(result.passed),
        result.rejected_blacklisted,
        result.not_selected,
    )

    for rank, scored in enumerate(result.passed, start=1):
        c, v = scored.candidate, scored.velocity
        logger.info(
            "--- #%s hashtag=%s hashtags=%s platforms=%s post_count=%s signals=%s avg_eng=%.4f "
            "[spike=%s volume=%s accel=%s cross_platform=%s creator_tier=%s] ---",
            rank,
            c.hashtag,
            sorted(c.hashtags),
            c.platform_breakdown,
            len(c.posts),
            v.signals_passed,
            c.average_engagement_rate,
            v.spike_6hr,
            v.volume_24hr,
            v.engagement_acceleration,
            v.cross_platform,
            v.creator_tier,
        )
        for post in c.posts:
            logger.info(
                "    post platform=%s id=%s likes=%s comments=%s views=%s text=%r",
                post.platform,
                post.platform_post_id,
                post.engagement.likes,
                post.engagement.comments,
                post.engagement.views,
                post.text[:80],
            )

    print("Raw posts pulled per platform:", platform_pull_counts)
    print(f"Data Pool length: {pool.size}")
    print(f"Dead Letter Queue length: {dead_letters.size}")
    print(f"Rule Engine candidates_built: {result.candidates_built}")
    print(f"Rule Engine passed (top {TOP_N}): {len(result.passed)}")
    print(f"Full log written to: {LOG_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
