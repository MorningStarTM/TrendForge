from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.services.ingestion.normalizer.post_schema import EngagementStats, RawPost
from pydantic import ValidationError


def make_post(**overrides: object) -> RawPost:
    defaults: dict[str, object] = {
        "platform": "instagram",
        "platform_post_id": "abc123",
        "text": "best pizza in town",
        "posted_at": datetime(2026, 7, 20, 12, 0, tzinfo=UTC),
    }
    defaults.update(overrides)
    return RawPost.model_validate(defaults)


def test_content_hash_is_deterministic_for_same_text_and_media() -> None:
    post_a = make_post(media_url="https://example.com/a.jpg")
    post_b = make_post(media_url="https://example.com/a.jpg")

    assert post_a.content_hash == post_b.content_hash


def test_content_hash_differs_for_different_text() -> None:
    post_a = make_post(text="best pizza in town")
    post_b = make_post(text="worst pizza in town")

    assert post_a.content_hash != post_b.content_hash


def test_content_hash_can_be_explicitly_overridden() -> None:
    post = make_post(content_hash="deadbeef")

    assert post.content_hash == "deadbeef"


def test_missing_required_fields_raise_validation_error() -> None:
    with pytest.raises(ValidationError):
        RawPost.model_validate({"platform": "tiktok"})


def test_engagement_rate_uses_views_when_larger_than_follower_count() -> None:
    post = make_post(
        engagement=EngagementStats(likes=100, comments=20, shares=10, views=1000),
        author_follower_count=50,
    )

    assert post.engagement_rate() == pytest.approx(130 / 1000)


def test_engagement_rate_falls_back_to_follower_count_when_views_are_zero() -> None:
    post = make_post(
        engagement=EngagementStats(likes=50, comments=0, shares=0, views=0),
        author_follower_count=500,
    )

    assert post.engagement_rate() == pytest.approx(50 / 500)


def test_engagement_rate_is_zero_when_no_denominator_available() -> None:
    post = make_post(engagement=EngagementStats(likes=5))

    assert post.engagement_rate() == 0.0
