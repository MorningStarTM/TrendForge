from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from app.services.embeddings import Embedder, cosine_similarity, embed_text
from app.services.generation.quality_gate.models import CheckResult, GateAction

# Plan task 16.4 / architecture doc 4.5: embed the generated caption and
# compare against the last 30 days of PUBLISHED captions; cosine > 0.9 means
# "too similar to a past post" and is flagged.
DEFAULT_DUPLICATE_THRESHOLD = 0.9
DEFAULT_LOOKBACK = timedelta(days=30)


@dataclass
class _PublishedCaption:
    text: str
    embedding: list[float]
    published_at: datetime


class PublishedCaptionStore:
    """In-memory store of recently published captions for the duplicate check.

    The doc uses pgvector; at this scale (a few posts a week over 30 days) an
    in-memory list with brute-force cosine is equivalent — the same adaptation
    as the Trend Dedup store, which this mirrors. Reuses the shared embedding
    model. Being in-memory, it forgets on restart; a real deployment would
    seed it from the published-posts history.
    """

    def __init__(
        self,
        threshold: float = DEFAULT_DUPLICATE_THRESHOLD,
        lookback: timedelta = DEFAULT_LOOKBACK,
        embedder: Embedder = embed_text,
    ) -> None:
        self._captions: list[_PublishedCaption] = []
        self._threshold = threshold
        self._lookback = lookback
        self._embedder = embedder

    def add_published(self, text: str, published_at: datetime | None = None) -> None:
        published_at = published_at or datetime.now(UTC)
        self._captions.append(
            _PublishedCaption(text=text, embedding=self._embedder(text), published_at=published_at)
        )

    def most_similar(self, text: str, now: datetime | None = None) -> tuple[str | None, float]:
        now = now or datetime.now(UTC)
        cutoff = now - self._lookback
        embedding = self._embedder(text)
        best_text: str | None = None
        best_score = 0.0
        for published in self._captions:
            if published.published_at < cutoff:
                continue
            score = cosine_similarity(embedding, published.embedding)
            if score > best_score:
                best_text, best_score = published.text, score
        return best_text, best_score

    @property
    def threshold(self) -> float:
        return self._threshold

    def clear(self) -> int:
        count = len(self._captions)
        self._captions.clear()
        return count

    @property
    def size(self) -> int:
        return len(self._captions)


@lru_cache
def get_published_caption_store() -> PublishedCaptionStore:
    """The single shared PublishedCaptionStore instance for this process."""
    return PublishedCaptionStore()


def check_duplicate_caption(
    caption: str,
    store: PublishedCaptionStore,
    now: datetime | None = None,
) -> CheckResult:
    """Flag a caption that's too similar to a recently published one (plan task 16.4)."""
    match_text, score = store.most_similar(caption, now=now)
    is_duplicate = match_text is not None and score > store.threshold
    return CheckResult(
        name="duplicate_content",
        passed=not is_duplicate,
        score=score,
        reason=None if not is_duplicate else f"too similar to a past post (cosine {score:.3f})",
        fail_action=GateAction.FLAG,
    )
