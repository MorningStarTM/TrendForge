from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.ingestion.data_pool import DataPool
from app.services.ingestion.normalizer.post_schema import RawPost
from app.services.trend_engine.rule_engine.clustering import TrendCandidate
from app.services.trend_engine.rule_engine.scoring_config import ScoringConfig
from app.services.trend_engine.rule_engine.velocity_scorer import (
    VelocityScore,
    _cross_platform_signal,
    _engagement_acceleration_signal,
    _spike_signal,
    _volume_signal,
    score_candidate,
)

NOW = datetime.now(UTC)


def make_post(
    platform: str = "instagram",
    platform_post_id: str = "1",
    hashtags: list[str] | None = None,
    posted_at: datetime = NOW,
    text: str = "post text",
    engagement_rate: float = 0.0,
    author_follower_count: int | None = None,
) -> RawPost:
    return RawPost.model_validate(
        {
            "platform": platform,
            "platform_post_id": platform_post_id,
            "hashtags": hashtags or ["pizza"],
            "posted_at": posted_at,
            "text": text,
            "engagement_rate": engagement_rate,
            "author_follower_count": author_follower_count,
        }
    )


def test_spike_signal_fires_above_threshold() -> None:
    pool = DataPool()
    config = ScoringConfig()
    pool._posts = [
        make_post(platform_post_id="prior", posted_at=NOW - timedelta(hours=8)),
        make_post(platform_post_id="r1", posted_at=NOW - timedelta(hours=1)),
        make_post(platform_post_id="r2", posted_at=NOW - timedelta(hours=2)),
        make_post(platform_post_id="r3", posted_at=NOW - timedelta(hours=3)),
        make_post(platform_post_id="r4", posted_at=NOW - timedelta(hours=4)),
    ]

    assert _spike_signal("pizza", pool, config) is True


def test_spike_signal_does_not_fire_below_threshold() -> None:
    pool = DataPool()
    config = ScoringConfig()
    pool._posts = [
        make_post(platform_post_id="prior", posted_at=NOW - timedelta(hours=8)),
        make_post(platform_post_id="recent", posted_at=NOW - timedelta(hours=1)),
    ]

    assert _spike_signal("pizza", pool, config) is False


def test_volume_signal_fires_when_any_platform_exceeds_its_threshold() -> None:
    pool = DataPool()
    config = ScoringConfig()
    # "x" platform threshold is 100 -> 101 posts trips it.
    pool._posts = [
        make_post(platform="x", platform_post_id=str(i), posted_at=NOW - timedelta(hours=1))
        for i in range(101)
    ]

    assert _volume_signal("pizza", pool, config) is True


def test_volume_signal_does_not_fire_below_platform_threshold() -> None:
    pool = DataPool()
    config = ScoringConfig()
    pool._posts = [
        make_post(platform="x", platform_post_id=str(i), posted_at=NOW - timedelta(hours=1))
        for i in range(5)
    ]

    assert _volume_signal("pizza", pool, config) is False


def test_engagement_acceleration_fires_when_recent_average_is_much_higher() -> None:
    pool = DataPool()
    config = ScoringConfig()
    pool._posts = [
        make_post(
            platform_post_id="prior", posted_at=NOW - timedelta(hours=10), engagement_rate=0.01
        ),
        make_post(
            platform_post_id="recent", posted_at=NOW - timedelta(hours=1), engagement_rate=0.10
        ),
    ]

    assert _engagement_acceleration_signal("pizza", pool, config) is True


def test_engagement_acceleration_does_not_fire_when_flat() -> None:
    pool = DataPool()
    config = ScoringConfig()
    pool._posts = [
        make_post(
            platform_post_id="prior", posted_at=NOW - timedelta(hours=10), engagement_rate=0.05
        ),
        make_post(
            platform_post_id="recent", posted_at=NOW - timedelta(hours=1), engagement_rate=0.05
        ),
    ]

    assert _engagement_acceleration_signal("pizza", pool, config) is False


def test_cross_platform_signal_fires_for_shared_content_across_platforms() -> None:
    pool = DataPool()
    config = ScoringConfig()
    pool._posts = [
        make_post(platform="instagram", platform_post_id="1", text="same meme"),
        make_post(platform="tiktok", platform_post_id="2", text="same meme"),
    ]

    assert _cross_platform_signal("pizza", pool, config) is True


def test_cross_platform_signal_does_not_fire_for_single_platform() -> None:
    pool = DataPool()
    config = ScoringConfig()
    pool._posts = [
        make_post(platform="instagram", platform_post_id="1", text="same meme"),
        make_post(platform="instagram", platform_post_id="2", text="different meme"),
    ]

    assert _cross_platform_signal("pizza", pool, config) is False


def test_velocity_score_passes_with_minimum_signals() -> None:
    config = ScoringConfig(minimum_signals_to_pass=2)
    score = VelocityScore(
        spike_6hr=True,
        volume_24hr=True,
        engagement_acceleration=False,
        cross_platform=False,
        creator_tier=False,
    )

    assert score.signals_passed == 2
    assert score.passes(config) is True


def test_velocity_score_fails_below_minimum_signals() -> None:
    config = ScoringConfig(minimum_signals_to_pass=2)
    score = VelocityScore(
        spike_6hr=True,
        volume_24hr=False,
        engagement_acceleration=False,
        cross_platform=False,
        creator_tier=False,
    )

    assert score.signals_passed == 1
    assert score.passes(config) is False


def test_score_candidate_combines_all_five_signals() -> None:
    pool = DataPool()
    config = ScoringConfig()
    # Cross-platform signal only: same content on 2 platforms, nothing else trips.
    pool._posts = [
        make_post(platform="instagram", platform_post_id="1", text="same meme"),
        make_post(platform="tiktok", platform_post_id="2", text="same meme"),
    ]
    candidate = TrendCandidate(hashtag="pizza", posts=pool._posts)

    score = score_candidate(candidate, pool, config)

    assert score.cross_platform is True
    assert score.spike_6hr is False
    assert score.creator_tier is False
    assert score.signals_passed == 1
