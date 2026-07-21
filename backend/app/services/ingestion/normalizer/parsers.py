from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from app.services.ingestion.normalizer.post_schema import EngagementStats, Platform, RawPost

HASHTAG_PATTERN = re.compile(r"#(\w+)")


class MalformedPostError(Exception):
    """A raw platform record was too broken to normalize into a RawPost.

    Callers should catch this per-record and route it to the Dead Letter
    Queue instead of letting one bad record abort an entire scrape batch
    (architecture doc 2.4: "malformed records go to a dead letter table").
    """

    def __init__(self, platform: str, reason: str, raw: dict[str, Any]) -> None:
        super().__init__(f"[{platform}] {reason}")
        self.platform = platform
        self.reason = reason
        self.raw = raw


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse_unix_timestamp(value: int | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(value, tz=UTC)
    except (OSError, OverflowError, ValueError):
        return None


def parse_instagram_post(raw: dict[str, Any], source_query: str) -> RawPost:
    """Parse one item from the ScrapeCreators `/v1/instagram/search/hashtag` `posts` array."""
    try:
        post_id = raw.get("id") or raw["shortcode"]
        caption = raw.get("caption") or ""
        owner = raw.get("owner") or {}
        posted_at = _parse_iso_datetime(raw.get("taken_at")) or datetime.now(UTC)

        return RawPost(
            platform="instagram",
            platform_post_id=str(post_id),
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
            source_query=source_query,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MalformedPostError("instagram", str(exc), raw) from exc


def parse_tiktok_post(raw: dict[str, Any], source_query: str) -> RawPost:
    """Parse one item from `aweme_list` / `search_item_list`.

    Covers hashtag search, keyword search, and profile videos — they all
    share this item shape.
    """
    try:
        desc = raw.get("desc") or ""
        stats = raw.get("statistics") or {}
        author = raw.get("author") or {}
        posted_at = (
            _parse_iso_datetime(raw.get("create_time_utc"))
            or _parse_unix_timestamp(raw.get("create_time"))
            or datetime.now(UTC)
        )

        return RawPost(
            platform="tiktok",
            platform_post_id=str(raw["aweme_id"]),
            text=desc,
            media_url=raw.get("url"),
            media_type="video",
            engagement=EngagementStats(
                likes=stats.get("digg_count") or 0,
                views=stats.get("play_count") or 0,
                shares=stats.get("share_count") or 0,
                comments=stats.get("comment_count") or 0,
                saves=stats.get("collect_count") or 0,
            ),
            hashtags=HASHTAG_PATTERN.findall(desc),
            author_follower_count=author.get("follower_count"),
            posted_at=posted_at,
            source_query=source_query,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MalformedPostError("tiktok", str(exc), raw) from exc


def parse_youtube_post(raw: dict[str, Any], source_query: str) -> RawPost:
    """Parse one video/short item from search, trending shorts, or video-details responses.

    ScrapeCreators isn't fully consistent across its own YouTube endpoints —
    e.g. `search` uses `publishedTime` while trending/video-details use
    `publishDate` — so both are tried.
    """
    try:
        title = raw.get("title") or ""
        description = raw.get("description") or ""
        text = f"{title}\n{description}".strip()
        posted_at = (
            _parse_iso_datetime(raw.get("publishedTime"))
            or _parse_iso_datetime(raw.get("publishDate"))
            or datetime.now(UTC)
        )
        hashtags = HASHTAG_PATTERN.findall(text) or list(raw.get("keywords") or [])

        return RawPost(
            platform="youtube",
            platform_post_id=str(raw["id"]),
            text=text,
            media_url=raw.get("url"),
            media_type="video",
            engagement=EngagementStats(
                views=raw.get("viewCountInt") or 0,
                likes=raw.get("likeCountInt") or 0,
                comments=raw.get("commentCountInt") or 0,
            ),
            hashtags=hashtags,
            author_follower_count=None,
            posted_at=posted_at,
            source_query=source_query,
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise MalformedPostError("youtube", str(exc), raw) from exc


PLATFORM_PARSERS: dict[Platform, Any] = {
    "instagram": parse_instagram_post,
    "tiktok": parse_tiktok_post,
    "youtube": parse_youtube_post,
}
