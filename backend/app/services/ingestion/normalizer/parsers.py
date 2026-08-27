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


def _tiktok_cover_url(video: dict[str, Any]) -> str | None:
    """Static cover-frame image URL from a TikTok `video` object (usable for vision)."""
    for key in ("cover", "origin_cover", "dynamic_cover"):
        cover = video.get(key)
        if isinstance(cover, dict):
            url_list = cover.get("url_list") or []
            if url_list:
                return str(url_list[0])
    return None


def _url_from_image_obj(img: Any) -> str | None:
    if isinstance(img, str):
        return img
    if isinstance(img, dict):
        for key in ("display_image", "owner_watermark_image", "thumbnail"):
            sub = img.get(key)
            if isinstance(sub, dict) and sub.get("url_list"):
                return str(sub["url_list"][0])
        if img.get("url_list"):
            return str(img["url_list"][0])
    return None


def _tiktok_photo_thumbnail(raw: dict[str, Any]) -> str | None:
    """First image URL if this TikTok item is a PHOTO post (slideshow), else None.

    TikTok photo posts appear under a few inconsistent fields depending on the
    item; we check the common ones. A photo post = static content (with a song),
    which is what we keep; a plain video has none of these and stays a video.
    """
    image_post_info = raw.get("image_post_info")
    candidates: list[Any] = []
    if isinstance(image_post_info, dict):
        candidates += image_post_info.get("images") or []
    candidates += raw.get("images") or []
    candidates += raw.get("image_infos") or []
    for img in candidates:
        url = _url_from_image_obj(img)
        if url:
            return url
    return None


def _instagram_audio(raw: dict[str, Any]) -> tuple[str | None, str | None]:
    """(audio_id, audio_title) for an Instagram post, if it has attributed music."""
    info = raw.get("clips_music_attribution_info")
    if isinstance(info, dict):
        song = info.get("song_name") or info.get("title")
        artist = info.get("artist_name")
        title = f"{song} - {artist}" if song and artist else (song or artist)
        audio_id = info.get("audio_id") or info.get("music_id")
        return (str(audio_id) if audio_id else None, title)
    return (None, None)


def _tiktok_audio(raw: dict[str, Any]) -> tuple[str | None, str | None]:
    """(audio_id, audio_title) for a TikTok post from its `music` object."""
    music = raw.get("music")
    if isinstance(music, dict):
        audio_id = music.get("id")
        title = music.get("title")
        author = music.get("author")
        full = f"{title} - {author}" if title and author else title
        return (str(audio_id) if audio_id else None, full)
    return (None, None)


def parse_instagram_post(raw: dict[str, Any], source_query: str) -> RawPost:
    """Parse one item from the ScrapeCreators `/v1/instagram/search/hashtag` `posts` array."""
    try:
        post_id = raw.get("id") or raw["shortcode"]
        caption = raw.get("caption") or ""
        owner = raw.get("owner") or {}
        posted_at = _parse_iso_datetime(raw.get("taken_at")) or datetime.now(UTC)
        audio_id, audio_title = _instagram_audio(raw)

        return RawPost(
            platform="instagram",
            platform_post_id=str(post_id),
            text=caption,
            media_url=raw.get("display_url") or raw.get("video_url"),
            thumbnail_url=raw.get("thumbnail_src") or raw.get("display_url"),
            media_type="video" if raw.get("is_video") else "image",
            engagement=EngagementStats(
                likes=raw.get("like_count") or 0,
                views=raw.get("video_view_count") or raw.get("video_play_count") or 0,
                comments=raw.get("comment_count") or 0,
            ),
            hashtags=HASHTAG_PATTERN.findall(caption),
            audio_id=audio_id,
            audio_title=audio_title,
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

        # Photo posts (slideshows) are static content — keep them as images.
        photo_thumb = _tiktok_photo_thumbnail(raw)
        media_type = "image" if photo_thumb else "video"
        thumbnail = photo_thumb or _tiktok_cover_url(raw.get("video") or {})
        audio_id, audio_title = _tiktok_audio(raw)

        return RawPost(
            platform="tiktok",
            platform_post_id=str(raw["aweme_id"]),
            text=desc,
            media_url=raw.get("url"),
            thumbnail_url=thumbnail,
            media_type=media_type,
            engagement=EngagementStats(
                likes=stats.get("digg_count") or 0,
                views=stats.get("play_count") or 0,
                shares=stats.get("share_count") or 0,
                comments=stats.get("comment_count") or 0,
                saves=stats.get("collect_count") or 0,
            ),
            hashtags=HASHTAG_PATTERN.findall(desc),
            audio_id=audio_id,
            audio_title=audio_title,
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
            thumbnail_url=raw.get("thumbnail"),
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
