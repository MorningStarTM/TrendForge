from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.services.ingestion.data_pool import DataPool
from app.services.ingestion.normalizer.post_schema import RawPost
from app.services.trend_engine.rule_engine.clustering import TrendCandidate, build_candidates

NOW = datetime.now(UTC)


def make_post(
    platform: str = "instagram",
    platform_post_id: str = "1",
    hashtags: list[str] | None = None,
    posted_at: datetime = NOW,
    text: str = "post text",
    engagement_rate: float = 0.0,
) -> RawPost:
    return RawPost.model_validate(
        {
            "platform": platform,
            "platform_post_id": platform_post_id,
            "hashtags": hashtags or [],
            "posted_at": posted_at,
            "text": text,
            "engagement_rate": engagement_rate,
        }
    )


def test_ignored_hashtags_do_not_chain_merge_candidates() -> None:
    # A generic tag ("fyp") shared by two otherwise-unrelated posts would
    # chain-merge them into one blob; ignoring it keeps them separate.
    pool = DataPool()
    pool._posts = [
        make_post(platform_post_id="1", hashtags=["eggplantparm", "fyp"]),
        make_post(platform_post_id="2", hashtags=["detroitstyle", "fyp"]),
    ]

    merged = build_candidates(pool, ignore_hashtags=frozenset())
    separate = build_candidates(pool, ignore_hashtags=frozenset({"fyp"}))

    # Without ignoring "fyp": all chain-merged into one candidate.
    assert len(merged) == 1
    # Ignoring "fyp": two distinct candidates, and "fyp" isn't a candidate.
    assert {c.hashtag for c in separate} == {"eggplantparm", "detroitstyle"}


def test_generic_hashtags_are_ignored_by_default() -> None:
    pool = DataPool()
    pool._posts = [make_post(platform_post_id="1", hashtags=["realtrend", "fyp", "viral"])]

    candidates = build_candidates(pool)

    # "fyp"/"viral" are in the default GENERIC_HASHTAGS stoplist.
    assert {c.hashtag for c in candidates} == {"realtrend"}


def test_posts_are_grouped_by_hashtag() -> None:
    pool = DataPool()
    pool._posts = [
        make_post(platform_post_id="1", hashtags=["pizza"]),
        # post 2 carries both "pizza" and "food" -> those two candidates merge.
        make_post(platform_post_id="2", hashtags=["pizza", "food"]),
        make_post(platform_post_id="3", hashtags=["burger"]),
    ]

    candidates = build_candidates(pool)
    by_hashtag = {c.hashtag: c for c in candidates}

    # "pizza" has more posts (2) than "food" (1), so it's the primary label.
    assert set(by_hashtag) == {"pizza", "burger"}
    assert by_hashtag["pizza"].hashtags == {"pizza", "food"}
    assert len(by_hashtag["pizza"].posts) == 2
    assert len(by_hashtag["burger"].posts) == 1
    assert by_hashtag["burger"].hashtags == {"burger"}


def test_one_post_with_multiple_hashtags_does_not_fragment_into_separate_candidates() -> None:
    # Mirrors a real observation: a single TikTok video tagged with 4
    # hashtags previously produced 4 separate single-post candidates.
    pool = DataPool()
    pool._posts = [
        make_post(
            platform="tiktok",
            platform_post_id="1",
            hashtags=["mauritius", "tafart", "tafstyle", "creatorsearchinsights"],
        )
    ]

    candidates = build_candidates(pool)

    assert len(candidates) == 1
    assert candidates[0].hashtags == {"mauritius", "tafart", "tafstyle", "creatorsearchinsights"}
    assert len(candidates[0].posts) == 1


def test_unrelated_hashtags_on_different_posts_stay_separate() -> None:
    pool = DataPool()
    pool._posts = [
        make_post(platform_post_id="1", hashtags=["pizza"]),
        make_post(platform_post_id="2", hashtags=["burger"]),
    ]

    candidates = build_candidates(pool)

    assert len(candidates) == 2
    assert {c.hashtag for c in candidates} == {"pizza", "burger"}


def test_hashtag_key_is_case_and_hash_symbol_normalized() -> None:
    pool = DataPool()
    pool._posts = [
        make_post(platform_post_id="1", hashtags=["#Pizza"]),
        make_post(platform_post_id="2", hashtags=["PIZZA"]),
    ]

    candidates = build_candidates(pool)

    assert len(candidates) == 1
    assert candidates[0].hashtag == "pizza"
    assert len(candidates[0].posts) == 2


def test_posts_outside_window_are_excluded() -> None:
    pool = DataPool()
    pool._posts = [
        make_post(platform_post_id="old", hashtags=["pizza"], posted_at=NOW - timedelta(hours=48)),
        make_post(platform_post_id="new", hashtags=["pizza"], posted_at=NOW - timedelta(hours=1)),
    ]

    candidates = build_candidates(pool, window=timedelta(hours=24))

    assert len(candidates) == 1
    assert len(candidates[0].posts) == 1
    assert candidates[0].posts[0].platform_post_id == "new"


def test_platform_breakdown_and_post_ids() -> None:
    pool = DataPool()
    pool._posts = [
        make_post(platform="instagram", platform_post_id="1", hashtags=["pizza"]),
        make_post(platform="tiktok", platform_post_id="2", hashtags=["pizza"]),
        make_post(platform="tiktok", platform_post_id="3", hashtags=["pizza"]),
    ]

    candidates = build_candidates(pool)
    candidate = candidates[0]

    assert candidate.platform_breakdown == {"instagram": 1, "tiktok": 2}
    assert candidate.platforms == {"instagram", "tiktok"}
    assert len(candidate.post_ids) == 3


def test_average_engagement_rate() -> None:
    pool = DataPool()
    pool._posts = [
        make_post(platform_post_id="1", hashtags=["pizza"], engagement_rate=0.10),
        make_post(platform_post_id="2", hashtags=["pizza"], engagement_rate=0.20),
    ]

    candidates = build_candidates(pool)

    assert candidates[0].average_engagement_rate == pytest.approx(0.15)


def test_average_engagement_rate_is_zero_for_empty_candidate() -> None:
    assert TrendCandidate(hashtag="empty").average_engagement_rate == 0.0
