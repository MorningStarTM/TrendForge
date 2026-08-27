from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.services.ingestion.data_pool import DataPool
from app.services.trend_engine.rule_engine.clustering import TrendCandidate
from app.services.trend_engine.rule_engine.scoring_config import ScoringConfig, get_scoring_config


@dataclass
class VelocityScore:
    """The 5 velocity signals from architecture doc 3.1, each a pass/fail."""

    spike_6hr: bool
    volume_24hr: bool
    engagement_acceleration: bool
    cross_platform: bool
    creator_tier: bool

    @property
    def signals_passed(self) -> int:
        return sum(
            [
                self.spike_6hr,
                self.volume_24hr,
                self.engagement_acceleration,
                self.cross_platform,
                self.creator_tier,
            ]
        )

    def passes(self, config: ScoringConfig) -> bool:
        """Candidates passing at least `minimum_signals_to_pass` signals move forward."""
        return self.signals_passed >= config.minimum_signals_to_pass


def _spike_signal(hashtag: str, pool: DataPool, config: ScoringConfig) -> bool:
    """6-hour spike: recent-6hr count / prior-6hr count > threshold."""
    ratio = pool.velocity_ratio(hashtag, timedelta(hours=6))
    return ratio > config.spike_ratio_threshold


def _volume_signal(hashtag: str, pool: DataPool, config: ScoringConfig) -> bool:
    """24-hour volume: any platform's post count over its own threshold."""
    posts = pool.get_by_hashtag(hashtag, timedelta(hours=24))
    counts_by_platform: dict[str, int] = {}
    for post in posts:
        counts_by_platform[post.platform] = counts_by_platform.get(post.platform, 0) + 1

    return any(
        count > config.volume_thresholds.get(platform, config.default_volume_threshold)
        for platform, count in counts_by_platform.items()
    )


def _engagement_acceleration_signal(hashtag: str, pool: DataPool, config: ScoringConfig) -> bool:
    """AVG(engagement_rate) in the last 6hrs vs the 24hrs before that window."""
    now = datetime.now(UTC)
    recent_posts = pool.get_by_hashtag(hashtag, timedelta(hours=6))
    prior_posts = [
        post
        for post in pool.get_by_hashtag(hashtag)
        if now - timedelta(hours=30) <= post.posted_at < now - timedelta(hours=6)
    ]

    recent_avg = (
        sum(p.engagement_rate for p in recent_posts) / len(recent_posts) if recent_posts else 0.0
    )
    prior_avg = (
        sum(p.engagement_rate for p in prior_posts) / len(prior_posts) if prior_posts else 0.0
    )

    if recent_avg == 0.0:
        return False
    if prior_avg == 0.0:
        return True
    return (recent_avg / prior_avg) > config.engagement_acceleration_threshold


def _cross_platform_signal(hashtag: str, pool: DataPool, config: ScoringConfig) -> bool:
    """Same content_hash appearing on 2+ platforms within the last 12hrs."""
    posts = pool.get_by_hashtag(hashtag, timedelta(hours=12))
    platforms_by_content_hash: dict[str, set[str]] = {}
    for post in posts:
        platforms_by_content_hash.setdefault(post.content_hash, set()).add(post.platform)

    return any(len(platforms) >= 2 for platforms in platforms_by_content_hash.values())


def _creator_tier_signal(hashtag: str, pool: DataPool, config: ScoringConfig) -> bool:
    """More than N posts from accounts with > threshold followers."""
    posts = pool.get_by_hashtag(hashtag)
    follower_threshold = config.creator_tier_follower_count
    large_account_posts = [
        post for post in posts if (post.author_follower_count or 0) > follower_threshold
    ]
    return len(large_account_posts) > config.creator_tier_minimum_accounts


def score_candidate(
    candidate: TrendCandidate, pool: DataPool, config: ScoringConfig | None = None
) -> VelocityScore:
    """Score a candidate against all 5 velocity signals.

    Signals are recomputed against the Data Pool (not just `candidate.posts`)
    so each uses its own correct lookback window, independent of whatever
    window the candidate was clustered with.

    A merged candidate can be known by several hashtags (`candidate.hashtags`)
    — a signal counts for the whole candidate if it fires under *any* of its
    aliases, since they all represent the same underlying trend.
    """
    config = config or get_scoring_config()
    hashtags = candidate.hashtags or {candidate.hashtag}

    return VelocityScore(
        spike_6hr=any(_spike_signal(h, pool, config) for h in hashtags),
        volume_24hr=any(_volume_signal(h, pool, config) for h in hashtags),
        engagement_acceleration=any(
            _engagement_acceleration_signal(h, pool, config) for h in hashtags
        ),
        cross_platform=any(_cross_platform_signal(h, pool, config) for h in hashtags),
        creator_tier=any(_creator_tier_signal(h, pool, config) for h in hashtags),
    )
