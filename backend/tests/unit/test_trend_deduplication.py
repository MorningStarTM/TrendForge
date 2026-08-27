from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from app.services.trend_engine.deduplication.similarity import (
    TrendDeduplicationStore,
    cosine_similarity,
    get_dedup_store,
)
from app.services.trend_engine.rule_engine.clustering import TrendCandidate

NOW = datetime(2026, 7, 29, 12, 0, tzinfo=UTC)


def make_candidate(
    hashtag: str, platform: str = "instagram", post_id: str = "p1"
) -> TrendCandidate:
    # TrendCandidate.platforms/post_ids derive from posts; build a minimal post.
    from app.services.ingestion.normalizer.post_schema import RawPost

    post = RawPost.model_validate(
        {
            "platform": platform,
            "platform_post_id": post_id,
            "text": f"post {post_id}",
            "posted_at": NOW,
        }
    )
    return TrendCandidate(hashtag=hashtag, hashtags={hashtag}, posts=[post])


# Deterministic fake embedder keyed by summary text, so tests don't load a model.
EMBEDDINGS = {
    "pineapple pizza debate": [1.0, 0.0, 0.0],
    "argument about pineapple on pizza": [0.99, 0.14, 0.0],  # ~0.99 cosine with the above
    "skateboarding tricks": [0.0, 1.0, 0.0],  # orthogonal -> 0.0 cosine
}


def fake_embedder(text: str) -> list[float]:
    return EMBEDDINGS[text]


def make_store(**kwargs: object) -> TrendDeduplicationStore:
    kwargs.setdefault("embedder", fake_embedder)
    return TrendDeduplicationStore(**kwargs)  # type: ignore[arg-type]


def test_cosine_similarity_basic_cases() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == pytest.approx(1.0)
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == pytest.approx(0.0)
    assert cosine_similarity([0.0, 0.0], [1.0, 1.0]) == 0.0  # zero vector guard


def test_first_trend_is_registered_as_new() -> None:
    store = make_store()

    result = store.check_and_register(make_candidate("pizza"), "pineapple pizza debate", now=NOW)

    assert result.is_duplicate is False
    assert result.matched_trend_id is None
    assert store.size == 1


def test_semantically_similar_trend_is_flagged_duplicate_and_merged() -> None:
    store = make_store()
    first = make_candidate("pizza", platform="instagram", post_id="ig1")
    store.check_and_register(first, "pineapple pizza debate", now=NOW)

    second = make_candidate("pineapple", platform="tiktok", post_id="tt1")
    result = store.check_and_register(second, "argument about pineapple on pizza", now=NOW)

    assert result.is_duplicate is True
    assert result.matched_trend_id == first.candidate_id
    assert result.trend_id == first.candidate_id  # canonical id is the original's
    assert result.similarity > 0.85
    # no new trend registered — merged into the original
    assert store.size == 1

    original = store.all_trends()[0]
    assert original.platforms == {"instagram", "tiktok"}  # both platforms credited
    # post_ids are the internal UUIDs from both candidates, unioned on merge
    assert original.post_ids == set(first.post_ids) | set(second.post_ids)
    assert len(original.post_ids) == 2
    assert original.merged_count == 1


def test_dissimilar_trend_is_registered_separately() -> None:
    store = make_store()
    store.check_and_register(make_candidate("pizza"), "pineapple pizza debate", now=NOW)

    result = store.check_and_register(make_candidate("skate"), "skateboarding tricks", now=NOW)

    assert result.is_duplicate is False
    assert store.size == 2


def test_trends_outside_the_lookback_window_are_ignored() -> None:
    store = make_store(lookback=timedelta(days=30))
    old = make_candidate("pizza", post_id="old")
    store.check_and_register(old, "pineapple pizza debate", now=NOW - timedelta(days=31))

    # 31 days later, a near-identical trend should NOT match the expired one.
    result = store.check_and_register(
        make_candidate("pineapple", post_id="new"),
        "argument about pineapple on pizza",
        now=NOW,
    )

    assert result.is_duplicate is False
    assert store.size == 2


def test_threshold_is_configurable() -> None:
    # With a threshold above the pair's ~0.99 similarity, it won't dedup.
    store = make_store(threshold=0.999)
    store.check_and_register(make_candidate("pizza"), "pineapple pizza debate", now=NOW)

    result = store.check_and_register(
        make_candidate("pineapple"), "argument about pineapple on pizza", now=NOW
    )

    assert result.is_duplicate is False
    assert store.size == 2


def test_clear_empties_the_store() -> None:
    store = make_store()
    store.check_and_register(make_candidate("pizza"), "pineapple pizza debate", now=NOW)

    cleared = store.clear()

    assert cleared == 1
    assert store.size == 0


def test_get_dedup_store_returns_singleton() -> None:
    assert get_dedup_store() is get_dedup_store()
