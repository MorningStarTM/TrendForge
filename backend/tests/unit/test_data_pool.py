from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.services.ingestion.data_pool import DataPool
from app.services.ingestion.normalizer.post_schema import RawPost

NOW = datetime.now(UTC)


def make_post(
    platform: str = "instagram",
    platform_post_id: str = "1",
    hashtags: list[str] | None = None,
    posted_at: datetime = NOW,
    text: str = "post text",
    media_url: str | None = None,
) -> RawPost:
    return RawPost.model_validate(
        {
            "platform": platform,
            "platform_post_id": platform_post_id,
            "hashtags": hashtags or [],
            "posted_at": posted_at,
            "text": text,
            "media_url": media_url,
        }
    )


@pytest.mark.asyncio
async def test_add_returns_true_for_new_post() -> None:
    pool = DataPool()

    added = await pool.add(make_post())

    assert added is True
    assert pool.size == 1


@pytest.mark.asyncio
async def test_add_rejects_duplicate_platform_post_id() -> None:
    pool = DataPool()
    await pool.add(make_post(platform="tiktok", platform_post_id="123", text="a"))

    duplicate = make_post(platform="tiktok", platform_post_id="123", text="different text")
    added_again = await pool.add(duplicate)

    assert added_again is False
    assert pool.size == 1


@pytest.mark.asyncio
async def test_add_rejects_duplicate_content_hash_across_platforms() -> None:
    pool = DataPool()
    await pool.add(make_post(platform="instagram", platform_post_id="1", text="same meme"))

    duplicate = make_post(platform="tiktok", platform_post_id="2", text="same meme")
    added_again = await pool.add(duplicate)

    assert added_again is False
    assert pool.size == 1


@pytest.mark.asyncio
async def test_add_many_returns_count_of_non_duplicates() -> None:
    pool = DataPool()
    posts = [
        make_post(platform_post_id="1", text="a"),
        make_post(platform_post_id="2", text="b"),
        make_post(platform_post_id="1", text="a"),  # duplicate
    ]

    added_count = await pool.add_many(posts)

    assert added_count == 2
    assert pool.size == 2


def test_get_since_filters_out_older_posts() -> None:
    pool = DataPool()
    pool._posts = [
        make_post(platform_post_id="old", posted_at=NOW - timedelta(hours=10)),
        make_post(platform_post_id="new", posted_at=NOW - timedelta(hours=1)),
    ]

    recent = pool.get_since(timedelta(hours=6))

    assert len(recent) == 1
    assert recent[0].platform_post_id == "new"


def test_get_since_can_filter_by_platform() -> None:
    pool = DataPool()
    pool._posts = [
        make_post(platform="instagram", platform_post_id="1", posted_at=NOW),
        make_post(platform="tiktok", platform_post_id="2", posted_at=NOW),
    ]

    result = pool.get_since(timedelta(hours=1), platform="tiktok")

    assert len(result) == 1
    assert result[0].platform == "tiktok"


def test_get_by_hashtag_is_case_and_hash_symbol_insensitive() -> None:
    pool = DataPool()
    pool._posts = [make_post(hashtags=["#Pizza"])]

    assert len(pool.get_by_hashtag("pizza")) == 1
    assert len(pool.get_by_hashtag("#PIZZA")) == 1
    assert len(pool.get_by_hashtag("burger")) == 0


def test_velocity_ratio_compares_recent_to_prior_window() -> None:
    pool = DataPool()
    window = timedelta(hours=6)
    # 1 post in the prior window, 3 in the most recent window -> ratio 3.0
    tags = ["pizza"]
    pool._posts = [
        make_post(platform_post_id="prior-1", hashtags=tags, posted_at=NOW - timedelta(hours=8)),
        make_post(platform_post_id="recent-1", hashtags=tags, posted_at=NOW - timedelta(hours=1)),
        make_post(platform_post_id="recent-2", hashtags=tags, posted_at=NOW - timedelta(hours=2)),
        make_post(platform_post_id="recent-3", hashtags=tags, posted_at=NOW - timedelta(hours=3)),
    ]

    assert pool.velocity_ratio("pizza", window) == pytest.approx(3.0)


def test_velocity_ratio_returns_recent_count_when_no_prior_posts() -> None:
    pool = DataPool()
    window = timedelta(hours=6)
    pool._posts = [make_post(hashtags=["pizza"], posted_at=NOW - timedelta(hours=1))]

    assert pool.velocity_ratio("pizza", window) == 1.0


def test_cross_platform_count_counts_distinct_platforms_sharing_content() -> None:
    pool = DataPool()
    pool._posts = [
        make_post(platform="instagram", platform_post_id="1", text="viral meme"),
        make_post(platform="tiktok", platform_post_id="2", text="viral meme"),
        make_post(platform="tiktok", platform_post_id="3", text="viral meme"),
    ]
    content_hash = pool._posts[0].content_hash

    assert pool.cross_platform_count(content_hash) == 2


@pytest.mark.asyncio
async def test_clear_empties_the_pool_and_returns_previous_count() -> None:
    pool = DataPool()
    await pool.add(make_post(platform_post_id="1"))
    await pool.add(make_post(platform_post_id="2", text="other"))

    cleared_count = await pool.clear()

    assert cleared_count == 2
    assert pool.size == 0

    # dedup state must also reset, or a re-scraped post would be wrongly dropped
    added_after_clear = await pool.add(make_post(platform_post_id="1"))
    assert added_after_clear is True
