"""End-to-end orchestrator for the trend-detection half of the pipeline:

    pull (scrape) -> normalize -> Data Pool -> Rule Engine -> ranked trends

This is the real thing the FastAPI layer exposes to the frontend — no LLM
(Haiku) classification, which needs AWS keys and is out of scope for the
detection-only check. Trend candidates therefore carry the rule-engine
signals (velocity, engagement, platforms, source posts) but NOT the
Haiku-derived fields (category, summary, brand fit) — those come back null.

Single-process, single-user state (module globals), matching the rest of the
design. A pull replaces the previous batch.
"""

from __future__ import annotations

import asyncio
import logging
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.services.ingestion.data_pool import DataPool, get_data_pool
from app.services.ingestion.normalizer.pipeline import normalize_and_ingest
from app.services.ingestion.normalizer.post_schema import MediaType, Platform
from app.services.ingestion.scrapers.base import ScrapeCreatorsClient
from app.services.ingestion.scrapers.instagram import InstagramScraper
from app.services.ingestion.scrapers.tiktok import TikTokScraper
from app.services.ingestion.scrapers.youtube import YouTubeScraper
from app.services.trend_engine.rule_engine.clustering import GENERIC_HASHTAGS, TrendCandidate
from app.services.trend_engine.rule_engine.engine import ScoredTrendCandidate, run_rule_engine
from app.services.trend_engine.rule_engine.velocity_scorer import VelocityScore

logger = logging.getLogger(__name__)

SUPPORTED_PLATFORMS = ("instagram", "tiktok", "youtube")
DEFAULT_TARGET_POSTS = 30
MAX_TARGET_POSTS = 10_000
MAX_PAGES_PER_PLATFORM = 200  # hard safety cap regardless of target

# (cursor) -> (raw items on this page, next cursor or None). One page per call.
PageFetcher = Callable[[Any], tuple[list[dict[str, Any]], Any]]

# Module-global state (single process). A pull overwrites it.
_last_run: dict[str, Any] | None = None
_trends: list[dict[str, Any]] = []
# The scored candidates behind the trend dicts, kept so content generation can
# classify them (keyed by trend id).
_scored_by_id: dict[str, ScoredTrendCandidate] = {}
_lock = asyncio.Lock()


async def _paginate(
    platform: Platform,
    fetch: PageFetcher,
    source_query: str,
    target: int,
    allowed: set[MediaType] | None,
    pool: DataPool,
) -> tuple[int, int]:
    """Pull pages until `target` raw items are fetched (or pages run out).

    Returns (raw_pulled, added_to_pool). Each page is normalized/deduped into
    the pool as it arrives. One page ≈ one ScrapeCreators credit.
    """
    cursor: Any = None
    pulled = kept = pages = 0
    while pulled < target and pages < MAX_PAGES_PER_PLATFORM:
        items, cursor = await asyncio.to_thread(fetch, cursor)
        pages += 1
        if not items:
            break
        pulled += len(items)
        summary = await normalize_and_ingest(
            platform, items, source_query=source_query, pool=pool, allowed_media_types=allowed
        )
        kept += summary.added_to_pool
        if not cursor:
            break
    return pulled, kept


def get_credit_balance() -> int | None:
    """Live ScrapeCreators credit balance (via /v1/account/credit-balance)."""
    settings = get_settings()
    client = ScrapeCreatorsClient(
        api_key=settings.scrapecreators_api_key, base_url=settings.scrapecreators_base_url
    )
    try:
        data = client.get("/v1/account/credit-balance")
        value = data.get("creditCount", data.get("credits_remaining"))
        return int(value) if value is not None else None
    except Exception as exc:  # noqa: BLE001 - surface as "unknown" to the UI, don't crash
        logger.warning("Could not fetch credit balance: %s", exc)
        return None
    finally:
        client.close()


def _velocity_dict(v: VelocityScore) -> dict[str, bool]:
    return {
        "spike_6hr": v.spike_6hr,
        "volume_24hr": v.volume_24hr,
        "engagement_acceleration": v.engagement_acceleration,
        "cross_platform": v.cross_platform,
        "creator_tier": v.creator_tier,
    }


def _generation_inputs(candidate: TrendCandidate) -> dict[str, Any]:
    """The trend's extracted content — hashtags, captions, audio — bundled as the
    inputs the Content Generation module (Module 13/14) consumes.

    Maps directly onto CaptionRequest: trending_hashtags, trending_audio,
    source_post_texts. Ready to pass through once generation is wired.
    """
    hashtag_counts: Counter[str] = Counter()
    audio: list[str] = []
    captions: list[str] = []
    for post in candidate.posts:
        for tag in post.hashtags:
            key = tag.lower().lstrip("#")
            if key not in GENERIC_HASHTAGS:  # skip #fyp/#viral/etc for cleaner gen inputs
                hashtag_counts[key] += 1
        if post.audio_title and post.audio_title not in audio:
            audio.append(post.audio_title)
        if post.text.strip():
            captions.append(post.text.strip())
    return {
        "trending_hashtags": [tag for tag, _ in hashtag_counts.most_common(15)],
        "trending_audio": audio[:5],
        "captions": captions[:5],
        "platforms": sorted(candidate.platforms),
        "market": "BOTH",
    }


def _map_candidate(scored: ScoredTrendCandidate) -> dict[str, Any]:
    candidate: TrendCandidate = scored.candidate
    velocity = scored.velocity
    top_posts = sorted(candidate.posts, key=lambda p: p.engagement_rate, reverse=True)[:5]
    return {
        "id": str(candidate.candidate_id),
        "hashtags": sorted(candidate.hashtags) or [candidate.hashtag],
        "platforms": candidate.platform_breakdown,
        "velocity": _velocity_dict(velocity),
        "signals_passed": velocity.signals_passed,
        "avg_engagement_rate": candidate.average_engagement_rate,
        "source_posts": [
            {
                "platform": p.platform,
                "text": p.text,
                "hashtags": p.hashtags,
                "likes": p.engagement.likes,
                "comments": p.engagement.comments,
                "views": p.engagement.views,
                "shares": p.engagement.shares,
                "saves": p.engagement.saves,
                "language": p.language,
                "audio_title": p.audio_title,
                "author_follower_count": p.author_follower_count,
                "engagement_rate": p.engagement_rate,
                "posted_at": p.posted_at.isoformat(),
                "thumbnail_url": p.thumbnail_url,
                "url": p.media_url,
                "media_type": p.media_type,
            }
            for p in top_posts
        ],
        # Extracted content bundle for the content-generation module.
        "generation_inputs": _generation_inputs(candidate),
        "detected_at": candidate.detected_at.isoformat(),
        "status": "pending",
        # Haiku-classification fields — not run in the detection-only pipeline.
        "category": None,
        "trend_summary": None,
        "brand_angle": None,
        "relevance_score": None,
        "brand_fit_score": None,
        "urgency": None,
        "estimated_lifespan": None,
    }


async def run_pull_and_detect(
    platforms: list[str],
    query: str,
    static_only: bool = False,
    target_posts: int = DEFAULT_TARGET_POSTS,
    window_hours: int = 24,
) -> dict[str, Any]:
    """Scrape the given platforms for `query`, normalize into the Data Pool,
    run the Rule Engine, and store the detected trends. Returns a run summary.

    `static_only` filters out videos (keeps photos / photo-with-song). Note the
    search endpoints return reels/videos almost exclusively, so static-only
    results are typically sparse — raise `target_posts` to pull more pages and
    surface more static posts.

    `target_posts` is the TOTAL raw posts to pull across the selected platforms
    (paginated). Roughly one page (~10-30 posts) per ScrapeCreators credit, so a
    large target spends real credits.

    `window_hours` is the detection window — only posts posted within it are
    clustered into trends (search returns historical posts, so a wider window
    surfaces more). `<= 0` means all-time (no recency filter).
    """
    query = query.strip() or "pizza"
    selected = [p for p in platforms if p in SUPPORTED_PLATFORMS] or list(SUPPORTED_PLATFORMS)
    target_posts = min(max(target_posts, 1), MAX_TARGET_POSTS)
    per_platform = max(1, target_posts // len(selected))
    window = timedelta(hours=window_hours) if window_hours > 0 else timedelta(days=3650)
    settings = get_settings()

    async with _lock:
        pool = get_data_pool()
        await pool.clear()  # fresh batch per pull
        client = ScrapeCreatorsClient(
            api_key=settings.scrapecreators_api_key,
            base_url=settings.scrapecreators_base_url,
        )
        # Static posts only (no videos) when requested — photo posts with a song count.
        allowed: set[MediaType] | None = {"image", "carousel"} if static_only else None
        posts_pulled: dict[str, int] = {}
        static_kept = 0
        try:
            if "instagram" in selected:
                ig = InstagramScraper(client)

                def ig_fetch(cur: Any) -> tuple[list[dict[str, Any]], Any]:
                    r = ig.search_hashtag(query, cursor=cur)
                    return r.posts, r.cursor

                pulled, kept = await _paginate(
                    "instagram", ig_fetch, f"hashtag:{query}", per_platform, allowed, pool
                )
                posts_pulled["instagram"] = pulled
                static_kept += kept
            if "tiktok" in selected:
                tt = TikTokScraper(client)

                def tt_fetch(cur: Any) -> tuple[list[dict[str, Any]], Any]:
                    r = tt.search_hashtag(query, cursor=cur)
                    return r.aweme_list, r.cursor

                pulled, kept = await _paginate(
                    "tiktok", tt_fetch, f"hashtag:{query}", per_platform, allowed, pool
                )
                posts_pulled["tiktok"] = pulled
                static_kept += kept
            if "youtube" in selected:
                yt = YouTubeScraper(client)

                def yt_fetch(cur: Any) -> tuple[list[dict[str, Any]], Any]:
                    r = yt.search(query, continuation_token=cur)
                    return r.videos + r.shorts, r.continuationToken

                pulled, kept = await _paginate(
                    "youtube", yt_fetch, f"keyword:{query}", per_platform, allowed, pool
                )
                posts_pulled["youtube"] = pulled
                static_kept += kept
        finally:
            client.close()

        # Exclude the query hashtag from clustering too — it's on every pulled
        # post, so it would chain-merge everything into one blob.
        ignore = GENERIC_HASHTAGS | frozenset({query.lower().lstrip("#")})
        result = run_rule_engine(pool, window=window, ignore_hashtags=ignore)
        global _trends, _last_run, _scored_by_id
        _trends = [_map_candidate(sc) for sc in result.passed]
        _scored_by_id = {str(sc.candidate.candidate_id): sc for sc in result.passed}
        _last_run = {
            "id": f"run-{int(datetime.now(UTC).timestamp())}",
            "query": query,
            "platforms": selected,
            "posts_pulled": posts_pulled,
            "total_posts": sum(posts_pulled.values()),
            "target_posts": target_posts,
            "static_only": static_only,
            "static_posts": static_kept if static_only else None,
            # Debug: how many pulled posts survived (deduped / media-filtered) into
            # the pool, and how many of those fall in the detection window
            # (what the rule engine actually clustered on).
            "window_hours": window_hours,
            "pool_posts": pool.size,
            "posts_in_window": len(pool.get_since(window)),
            "trends_detected": len(_trends),
            "candidates_built": result.candidates_built,
            "rejected_blacklisted": result.rejected_blacklisted,
            "ran_at": datetime.now(UTC).isoformat(),
        }
        logger.info(
            "Pull+detect: %s posts -> %s candidates -> %s trends (%s blacklisted)",
            _last_run["total_posts"],
            result.candidates_built,
            len(_trends),
            result.rejected_blacklisted,
        )
        return _last_run


def get_last_run() -> dict[str, Any] | None:
    return _last_run


def get_trends() -> list[dict[str, Any]]:
    return _trends


def get_trend(trend_id: str) -> dict[str, Any] | None:
    return next((t for t in _trends if t["id"] == trend_id), None)


def get_scored(trend_id: str) -> ScoredTrendCandidate | None:
    return _scored_by_id.get(trend_id)
