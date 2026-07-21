from __future__ import annotations

import pytest
from app.services.ingestion.normalizer.parsers import (
    MalformedPostError,
    parse_instagram_post,
    parse_tiktok_post,
    parse_youtube_post,
)


def test_parse_instagram_post_extracts_expected_fields() -> None:
    raw = {
        "id": "3877557798330457117",
        "shortcode": "abc123",
        "caption": "Check this out #pizza #yum",
        "display_url": "https://example.com/img.jpg",
        "is_video": False,
        "like_count": 100,
        "comment_count": 10,
        "video_view_count": 0,
        "owner": {"follower_count": 5000},
        "taken_at": "2026-07-01T12:00:00.000Z",
    }

    post = parse_instagram_post(raw, source_query="hashtag:pizza")

    assert post.platform == "instagram"
    assert post.platform_post_id == "3877557798330457117"
    assert post.media_type == "image"
    assert post.hashtags == ["pizza", "yum"]
    assert post.engagement.likes == 100
    assert post.author_follower_count == 5000
    assert post.posted_at.year == 2026
    assert post.source_query == "hashtag:pizza"


def test_parse_instagram_post_raises_on_missing_id_and_shortcode() -> None:
    with pytest.raises(MalformedPostError) as exc_info:
        parse_instagram_post({"caption": "no id here"}, source_query="hashtag:pizza")

    assert exc_info.value.platform == "instagram"


def test_parse_tiktok_post_extracts_expected_fields() -> None:
    raw = {
        "aweme_id": "123456",
        "desc": "funny video #comedy #fyp",
        "statistics": {
            "digg_count": 500,
            "play_count": 10000,
            "share_count": 20,
            "comment_count": 30,
            "collect_count": 5,
        },
        "author": {"follower_count": 20000},
        "create_time_utc": "2026-07-01T10:00:00Z",
        "url": "https://tiktok.com/video/123456",
    }

    post = parse_tiktok_post(raw, source_query="hashtag:comedy")

    assert post.platform == "tiktok"
    assert post.platform_post_id == "123456"
    assert post.hashtags == ["comedy", "fyp"]
    assert post.engagement.likes == 500
    assert post.engagement.views == 10000
    assert post.engagement.saves == 5
    assert post.author_follower_count == 20000
    assert post.posted_at.year == 2026


def test_parse_tiktok_post_raises_on_missing_aweme_id() -> None:
    with pytest.raises(MalformedPostError) as exc_info:
        parse_tiktok_post({"desc": "no id"}, source_query="hashtag:comedy")

    assert exc_info.value.platform == "tiktok"


def test_parse_youtube_post_handles_search_shape_with_published_time() -> None:
    raw = {
        "id": "abc123",
        "title": "Pizza trend video",
        "viewCountInt": 5000,
        "publishedTime": "2026-07-01T08:00:00.000Z",
        "url": "https://youtube.com/watch?v=abc123",
    }

    post = parse_youtube_post(raw, source_query="keyword:pizza")

    assert post.platform_post_id == "abc123"
    assert post.engagement.views == 5000
    assert post.posted_at.year == 2026


def test_parse_youtube_post_handles_trending_shape_with_publish_date() -> None:
    raw = {
        "id": "xyz789",
        "title": "Trending short #pizza",
        "viewCountInt": 20000,
        "likeCountInt": 300,
        "commentCountInt": 15,
        "publishDate": "2026-07-05T09:00:00-07:00",
        "url": "https://youtube.com/shorts/xyz789",
    }

    post = parse_youtube_post(raw, source_query="trending")

    assert post.platform_post_id == "xyz789"
    assert post.hashtags == ["pizza"]
    assert post.engagement.likes == 300
    assert post.engagement.comments == 15
    assert post.posted_at.year == 2026


def test_parse_youtube_post_falls_back_to_keywords_when_no_hashtags_in_text() -> None:
    raw = {
        "id": "abc123",
        "title": "A video with no hashtags",
        "keywords": ["food", "pizza"],
    }

    post = parse_youtube_post(raw, source_query="trending")

    assert post.hashtags == ["food", "pizza"]


def test_parse_youtube_post_raises_on_missing_id() -> None:
    with pytest.raises(MalformedPostError) as exc_info:
        parse_youtube_post({"title": "no id"}, source_query="trending")

    assert exc_info.value.platform == "youtube"
