from __future__ import annotations

from app.services.ingestion.normalizer.post_schema import EngagementStats


def compute_engagement_rate(engagement: EngagementStats, follower_count: int | None) -> float:
    """(likes + comments + shares) / max(views, follower_count).

    Makes a 10K-view TikTok from a 50K-follower account comparable to a
    500K-view post from a 5M-follower account (architecture doc 2.4).
    """
    denominator = max(engagement.views, follower_count or 0)
    if denominator == 0:
        return 0.0
    numerator = engagement.likes + engagement.comments + engagement.shares
    return numerator / denominator
