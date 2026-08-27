from __future__ import annotations

import logging
import math
from collections.abc import Callable, Sequence
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from huggingface_hub import InferenceClient

logger = logging.getLogger(__name__)

# Embeddings are computed by the Hugging Face Inference API (feature
# extraction), not a local model — so the backend/container ships no
# torch/sentence-transformers. It's the SAME model as before
# (all-MiniLM-L6-v2, 384-dim), which means the validated 0.85 trend-dedup
# threshold and the Brand KB retrieval behavior are unchanged.
#
# Used by Trend Deduplication (Module 11) and the Brand KB RAG layer (Module 12).
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

Embedder = Callable[[str], list[float]]


@lru_cache
def _get_client() -> InferenceClient:
    from huggingface_hub import InferenceClient

    from app.core.config import get_settings

    settings = get_settings()
    if not settings.hf_token:
        raise RuntimeError(
            "HF_TOKEN is not set — it's required to compute embeddings "
            "(trend deduplication and Brand KB retrieval)."
        )
    logger.info("Using Hugging Face Inference embeddings: %s", settings.embedding_model)
    return InferenceClient(provider="hf-inference", api_key=settings.hf_token)


def embed_text(text: str) -> list[float]:
    """Embed `text` via the HF Inference API. Returns a 384-dim vector.

    Runs remotely (an API call), so no local ML model is needed. Token-level
    outputs (if a model returns them) are mean-pooled to a single sentence
    vector.
    """
    import numpy as np

    from app.core.config import get_settings

    vector = _get_client().feature_extraction(text, model=get_settings().embedding_model)
    arr = np.asarray(vector, dtype=float)
    if arr.ndim > 1:
        arr = arr.mean(axis=0)
    return [float(x) for x in arr]


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)
