"""Backwards-compatible re-export.

Embedding infrastructure now lives in `app.services.embeddings` (shared
between Trend Dedup and the Brand KB RAG layer). Kept here so existing
imports of this path keep working.
"""

from __future__ import annotations

from app.services.embeddings import MODEL_NAME, embed_text

__all__ = ["MODEL_NAME", "embed_text"]
