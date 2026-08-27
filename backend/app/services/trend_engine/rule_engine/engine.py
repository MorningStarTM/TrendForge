from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from app.services.ingestion.data_pool import DataPool
from app.services.trend_engine.rule_engine.blacklist_filter import (
    BlacklistFilter,
    get_blacklist_filter,
)
from app.services.trend_engine.rule_engine.clustering import (
    GENERIC_HASHTAGS,
    TrendCandidate,
    build_candidates,
)
from app.services.trend_engine.rule_engine.scoring_config import ScoringConfig, get_scoring_config
from app.services.trend_engine.rule_engine.velocity_scorer import VelocityScore, score_candidate


@dataclass
class ScoredTrendCandidate:
    """A candidate that passed velocity scoring and the blacklist.

    Ready for the Detection Model.
    """

    candidate: TrendCandidate
    velocity: VelocityScore


@dataclass
class RuleEngineResult:
    candidates_built: int
    passed: list[ScoredTrendCandidate] = field(default_factory=list)
    not_selected: int = 0
    rejected_low_velocity: int = 0
    """Unused by the current ranking-based `run_rule_engine` (always 0) — kept
    for anyone using the older threshold-gate behavior via
    `VelocityScore.passes()` directly instead of this function."""
    rejected_blacklisted: int = 0


def run_rule_engine(
    pool: DataPool,
    window: timedelta = timedelta(hours=24),
    config: ScoringConfig | None = None,
    blacklist: BlacklistFilter | None = None,
    top_n: int | None = None,
    ignore_hashtags: frozenset[str] = GENERIC_HASHTAGS,
) -> RuleEngineResult:
    """The Rule-Based Engine pre-filter (architecture doc 3.1): cluster -> score -> rank.

    Cheap, structured-data-only filtering meant to run before any LLM calls.
    Candidates are ranked, not gated on an absolute pass/fail bar: the doc's
    thresholds (500+ TikTok posts/24hr, 3+ accounts over 100K followers,
    etc.) were calibrated for firehose-scale ingestion and rarely clear at
    the volume a single-user tool actually scrapes, so gating on them would
    return empty almost every run. Instead, every non-blacklisted candidate
    is scored and sorted by (signals_passed desc, average_engagement_rate
    desc), and the top `top_n` are returned — these are what would be
    forwarded to the Detection Model (Haiku) next, which is the real
    judgment call on whether something is actually worth generating content
    for. The blacklist is still a hard filter, applied before ranking.

    `top_n` falls back to `config.top_n` when not given. The older
    threshold-gate behavior (`VelocityScore.passes()`,
    `config.minimum_signals_to_pass`) still exists and works — it's just not
    what this function uses anymore.
    """
    config = config or get_scoring_config()
    blacklist = blacklist or get_blacklist_filter()
    limit = top_n if top_n is not None else config.top_n

    candidates = build_candidates(pool, window=window, ignore_hashtags=ignore_hashtags)
    result = RuleEngineResult(candidates_built=len(candidates))

    scored: list[ScoredTrendCandidate] = []
    for candidate in candidates:
        blocked, _reason = blacklist.is_blocked(candidate)
        if blocked:
            result.rejected_blacklisted += 1
            continue

        velocity = score_candidate(candidate, pool, config)
        scored.append(ScoredTrendCandidate(candidate=candidate, velocity=velocity))

    scored.sort(
        key=lambda sc: (sc.velocity.signals_passed, sc.candidate.average_engagement_rate),
        reverse=True,
    )

    result.passed = scored[:limit]
    result.not_selected = len(scored) - len(result.passed)
    return result
