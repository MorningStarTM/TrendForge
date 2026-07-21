from __future__ import annotations

import pytest
from app.services.ingestion.data_pool import DataPool
from app.services.ingestion.normalizer.dead_letter import DeadLetterQueue
from app.services.ingestion.normalizer.pipeline import normalize_and_ingest


def make_instagram_raw(post_id: str, caption: str = "post #pizza") -> dict[str, object]:
    return {
        "id": post_id,
        "caption": caption,
        "display_url": "https://example.com/img.jpg",
        "is_video": False,
        "like_count": 10,
        "comment_count": 2,
        "video_view_count": 100,
        "owner": {"follower_count": 1000},
        "taken_at": "2026-07-01T12:00:00.000Z",
    }


@pytest.mark.asyncio
async def test_valid_records_are_normalized_and_added_to_the_pool() -> None:
    pool = DataPool()
    dead_letters = DeadLetterQueue()
    raw_records = [
        make_instagram_raw("1"),
        make_instagram_raw("2", caption="different text #pizza"),
    ]

    summary = await normalize_and_ingest(
        "instagram", raw_records, source_query="hashtag:pizza", pool=pool, dead_letters=dead_letters
    )

    assert summary.received == 2
    assert summary.malformed == 0
    assert summary.added_to_pool == 2
    assert pool.size == 2
    assert dead_letters.size == 0

    post = pool.all_posts()[0]
    assert post.language == "en"
    # denominator is max(views=100, follower_count=1000) == 1000
    assert post.engagement_rate == pytest.approx((10 + 2) / 1000)


@pytest.mark.asyncio
async def test_malformed_records_go_to_the_dead_letter_queue_not_the_pool() -> None:
    pool = DataPool()
    dead_letters = DeadLetterQueue()
    raw_records = [make_instagram_raw("1"), {"caption": "missing id"}]

    summary = await normalize_and_ingest(
        "instagram", raw_records, source_query="hashtag:pizza", pool=pool, dead_letters=dead_letters
    )

    assert summary.received == 2
    assert summary.malformed == 1
    assert summary.added_to_pool == 1
    assert pool.size == 1
    assert dead_letters.size == 1
    assert dead_letters.all()[0].platform == "instagram"


@pytest.mark.asyncio
async def test_duplicate_records_are_deduped_by_the_pool() -> None:
    pool = DataPool()
    dead_letters = DeadLetterQueue()
    raw_records = [
        make_instagram_raw("1", caption="same text"),
        make_instagram_raw("2", caption="same text"),
    ]

    summary = await normalize_and_ingest(
        "instagram", raw_records, source_query="hashtag:pizza", pool=pool, dead_letters=dead_letters
    )

    assert summary.received == 2
    assert summary.malformed == 0
    assert summary.added_to_pool == 1
    assert summary.duplicates == 1
    assert pool.size == 1
