from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from app.services.embeddings import Embedder, cosine_similarity, embed_text
from app.services.generation.brand_kb.chunking import BrandChunk

DEFAULT_TOP_K = 5


@dataclass
class _EmbeddedChunk:
    chunk: BrandChunk
    embedding: list[float]


@dataclass
class RetrievedChunk:
    chunk: BrandChunk
    score: float


class BrandKB:
    """In-memory brand knowledge base with semantic retrieval (architecture doc 4.1, 12.3-12.4).

    The doc stores chunk embeddings in pgvector and retrieves by cosine
    similarity; at ~200 chunks pgvector is doing a linear scan anyway, so an
    in-memory list with brute-force cosine is functionally identical without a
    database. Reuses the shared embedding model (all-MiniLM-L6-v2) — the same
    one used for Trend Dedup.
    """

    def __init__(self, embedder: Embedder = embed_text) -> None:
        self._chunks: list[_EmbeddedChunk] = []
        self._embedder = embedder

    def add_chunks(self, chunks: list[BrandChunk]) -> int:
        """Embed and store chunks. Returns the number added."""
        for chunk in chunks:
            embedding = self._embedder(chunk.content_text)
            self._chunks.append(_EmbeddedChunk(chunk=chunk, embedding=embedding))
        return len(chunks)

    def retrieve(self, query_text: str, k: int = DEFAULT_TOP_K) -> list[RetrievedChunk]:
        """Top-k most relevant brand chunks by cosine similarity (doc 12.4).

        Query is typically the trend_summary (+ category) from the TCO.
        """
        query_embedding = self._embedder(query_text)
        scored = [
            RetrievedChunk(
                chunk=item.chunk,
                score=cosine_similarity(query_embedding, item.embedding),
            )
            for item in self._chunks
        ]
        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:k]

    def clear(self) -> int:
        count = len(self._chunks)
        self._chunks.clear()
        return count

    @property
    def size(self) -> int:
        return len(self._chunks)


@lru_cache
def get_brand_kb() -> BrandKB:
    """The single shared BrandKB instance for this process."""
    return BrandKB()


def retrieve_brand_context(query_text: str, k: int = DEFAULT_TOP_K) -> list[RetrievedChunk]:
    """Convenience wrapper over the shared BrandKB (architecture doc 12.4)."""
    return get_brand_kb().retrieve(query_text, k=k)
