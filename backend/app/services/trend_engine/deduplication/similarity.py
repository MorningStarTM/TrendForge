from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from uuid import UUID

# cosine_similarity is re-exported here so existing imports of it from this
# module keep working; it now lives in the shared embeddings module.
from app.services.embeddings import Embedder, cosine_similarity, embed_text
from app.services.trend_engine.rule_engine.clustering import TrendCandidate

__all__ = [
    "DEFAULT_SIMILARITY_THRESHOLD",
    "DEFAULT_LOOKBACK",
    "cosine_similarity",
    "RegisteredTrend",
    "DedupResult",
    "TrendDeduplicationStore",
    "get_dedup_store",
]

# architecture doc 11.2 / section 8: cosine > 0.85 = duplicate, compared
# against trends from the last 30 days.
DEFAULT_SIMILARITY_THRESHOLD = 0.85
DEFAULT_LOOKBACK = timedelta(days=30)


@dataclass
class RegisteredTrend:
    """A trend the dedup store already knows about (architecture doc 11.1-11.3).

    `platforms` and `post_ids` accumulate as duplicates are merged in, which is
    how a trend "credits both platforms" (doc section 8). Velocity is not
    stored here — it's always recomputed from the Data Pool — so there's
    nothing velocity-related to merge.
    """

    trend_id: UUID
    trend_summary: str
    embedding: list[float]
    platforms: set[str]
    post_ids: set[str]
    registered_at: datetime
    merged_count: int = 0


@dataclass
class DedupResult:
    is_duplicate: bool
    trend_id: UUID  # canonical id: the original's id on a duplicate, else the new one
    similarity: float
    matched_trend_id: UUID | None = None


class TrendDeduplicationStore:
    """In-memory semantic dedup for trends (architecture doc, Module 11).

    The doc specifies pgvector; we have no database, so this keeps embeddings
    in a list and does brute-force cosine similarity. At single-user volume
    (a handful of trends per run, dozens over a 30-day window) that's
    trivially fast. Being in-memory, it only remembers trends for the life of
    the process — a restart loses dedup history, an accepted limitation of
    the no-DB design.

    This complements, not duplicates, the Data Pool's content-hash dedup:
    that catches byte-identical cross-platform reposts; this catches
    *different* posts that are semantically about the *same* trend, by
    comparing their (Haiku-produced) trend summaries.
    """

    def __init__(
        self,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        lookback: timedelta = DEFAULT_LOOKBACK,
        embedder: Embedder = embed_text,
    ) -> None:
        self._trends: list[RegisteredTrend] = []
        self._threshold = threshold
        self._lookback = lookback
        self._embedder = embedder

    def _recent(self, now: datetime) -> list[RegisteredTrend]:
        cutoff = now - self._lookback
        return [trend for trend in self._trends if trend.registered_at >= cutoff]

    def _most_similar(
        self, embedding: list[float], now: datetime
    ) -> tuple[RegisteredTrend | None, float]:
        best: RegisteredTrend | None = None
        best_score = 0.0
        for trend in self._recent(now):
            score = cosine_similarity(embedding, trend.embedding)
            if score > best_score:
                best, best_score = trend, score
        return best, best_score

    def check_and_register(
        self,
        candidate: TrendCandidate,
        trend_summary: str,
        now: datetime | None = None,
    ) -> DedupResult:
        """Dedup a trend before it's queued for generation (architecture doc 11.2-11.3).

        If `trend_summary` is > threshold cosine-similar to a trend from the
        last 30 days, the candidate's platforms/posts are merged into that
        original and no new trend is registered (so no duplicate generation
        task). Otherwise the trend is registered as new.
        """
        now = now or datetime.now(UTC)
        embedding = self._embedder(trend_summary)
        match, score = self._most_similar(embedding, now)

        if match is not None and score > self._threshold:
            match.platforms |= set(candidate.platforms)
            match.post_ids |= set(candidate.post_ids)
            match.merged_count += 1
            return DedupResult(
                is_duplicate=True,
                trend_id=match.trend_id,
                similarity=score,
                matched_trend_id=match.trend_id,
            )

        self._trends.append(
            RegisteredTrend(
                trend_id=candidate.candidate_id,
                trend_summary=trend_summary,
                embedding=embedding,
                platforms=set(candidate.platforms),
                post_ids=set(candidate.post_ids),
                registered_at=now,
            )
        )
        return DedupResult(is_duplicate=False, trend_id=candidate.candidate_id, similarity=score)

    def all_trends(self) -> list[RegisteredTrend]:
        """Snapshot of registered trends — data for the dedup dashboard view (doc 11.4)."""
        return list(self._trends)

    def clear(self) -> int:
        count = len(self._trends)
        self._trends.clear()
        return count

    @property
    def size(self) -> int:
        return len(self._trends)


@lru_cache
def get_dedup_store() -> TrendDeduplicationStore:
    """The single shared TrendDeduplicationStore instance for this process."""
    return TrendDeduplicationStore()
