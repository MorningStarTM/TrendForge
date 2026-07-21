from __future__ import annotations

import pytest
from app.services.ingestion.normalizer.engagement import compute_engagement_rate
from app.services.ingestion.normalizer.post_schema import EngagementStats


def test_uses_views_when_larger_than_follower_count() -> None:
    stats = EngagementStats(likes=100, comments=20, shares=10, views=1000)

    assert compute_engagement_rate(stats, follower_count=50) == pytest.approx(130 / 1000)


def test_falls_back_to_follower_count_when_views_are_zero() -> None:
    stats = EngagementStats(likes=50, comments=0, shares=0, views=0)

    assert compute_engagement_rate(stats, follower_count=500) == pytest.approx(50 / 500)


def test_is_zero_when_no_denominator_available() -> None:
    stats = EngagementStats(likes=5)

    assert compute_engagement_rate(stats, follower_count=None) == 0.0


def test_is_zero_when_follower_count_is_zero_and_no_views() -> None:
    stats = EngagementStats(likes=5)

    assert compute_engagement_rate(stats, follower_count=0) == 0.0
