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


def test_engagement_rate_defaults_to_zero_until_normalizer_sets_it() -> None:
    post = make_post(engagement=EngagementStats(likes=100, views=1000))

    assert post.engagement_rate == 0.0


def test_engagement_rate_can_be_set_explicitly() -> None:
    post = make_post(engagement_rate=0.13)

    assert post.engagement_rate == 0.13
