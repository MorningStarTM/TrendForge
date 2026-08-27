from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

# architecture doc 3.1: "24-hour volume" thresholds differ per platform.
DEFAULT_VOLUME_THRESHOLDS: dict[str, int] = {
    "tiktok": 500,
    "instagram": 200,
    "x": 100,
}


@dataclass
class ScoringConfig:
    """Tunable thresholds for the Rule-Based Engine's velocity signals (architecture doc 3.1).

    A single mutable instance, shared process-wide via `get_scoring_config()`.
    Edit its fields directly to retune scoring without a restart — same
    "hot-reloadable, in-memory" pattern already used for the Data Pool and
    Dead Letter Queue. There's no persisted `scoring_config` table (doc 8.3)
    yet since nothing in this project is persisted to a database so far.
    """

    spike_ratio_threshold: float = 3.0
    volume_thresholds: dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_VOLUME_THRESHOLDS)
    )
    default_volume_threshold: int = 100
    engagement_acceleration_threshold: float = 2.0
    creator_tier_follower_count: int = 100_000
    creator_tier_minimum_accounts: int = 3
    minimum_signals_to_pass: int = 2
    """Kept for anyone using `VelocityScore.passes()` directly — the default
    Rule Engine (`engine.run_rule_engine`) ranks candidates instead of
    gating on this, since absolute thresholds calibrated for firehose-scale
    ingestion (doc 3.1) rarely clear at the volume a single-user tool
    actually scrapes."""

    top_n: int = 5
    """How many ranked candidates `run_rule_engine` returns by default."""


@lru_cache
def get_scoring_config() -> ScoringConfig:
    """The single shared ScoringConfig instance for this process."""
    return ScoringConfig()
