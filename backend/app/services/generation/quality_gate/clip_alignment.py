from __future__ import annotations

import logging
from collections.abc import Callable
from functools import lru_cache
from typing import TYPE_CHECKING

from app.services.embeddings import cosine_similarity
from app.services.generation.quality_gate.models import CheckResult, GateAction

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# Plan task 16.2 / architecture doc 4.5: CLIP (ViT-B/32) score between the
# generated image and the caption. >= 0.25 passes; below → regenerate image.
CLIP_MODEL_NAME = "clip-ViT-B-32"
CLIP_THRESHOLD = 0.25

# (image_bytes, caption) -> alignment score. Injectable so the scorer can be
# swapped — CLIP (below) or a vision-LLM judge (see vision_alignment.py) — and
# so the gate is testable without a real model or images.
#
# NOTE: the pass threshold is scorer-specific. CLIP scores good matches around
# ~0.3 (hence 0.25); a vision-LLM judge scores on a 0-1 semantic scale, so pass
# its own higher threshold (VISION_ALIGNMENT_THRESHOLD).
AlignmentScorer = Callable[[bytes, str], float]


@lru_cache
def _get_clip_model() -> SentenceTransformer:
    from sentence_transformers import SentenceTransformer

    logger.info("Loading CLIP model %s", CLIP_MODEL_NAME)
    return SentenceTransformer(CLIP_MODEL_NAME)


def default_clip_scorer(image_bytes: bytes, caption: str) -> float:
    """Real CLIP score via sentence-transformers clip-ViT-B-32.

    NOTE: `sentence-transformers`/`torch` were removed from the deps (embeddings
    now run on the HF Inference API), and `pillow` was never added — so this
    local-CLIP path is not installed by default. Use the Claude-vision scorer
    (`make_claude_vision_scorer`, no local ML deps) instead, or reinstall
    `sentence-transformers` + `pillow` to use CLIP. This runs only once real
    generated images exist (Module 15).
    """
    try:
        import io

        from PIL import Image
    except ModuleNotFoundError as exc:  # pragma: no cover - depends on optional dep
        raise RuntimeError(
            "Local CLIP alignment needs `pillow` and `sentence-transformers`, which "
            "aren't installed. Use the Claude-vision scorer (make_claude_vision_scorer) "
            "instead, or add those two packages back."
        ) from exc

    model = _get_clip_model()
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image_embedding = [float(x) for x in model.encode(image)]
    text_embedding = [float(x) for x in model.encode(caption)]
    return cosine_similarity(image_embedding, text_embedding)


def check_image_caption_alignment(
    image_bytes: bytes,
    caption: str,
    threshold: float = CLIP_THRESHOLD,
    scorer: AlignmentScorer = default_clip_scorer,
) -> CheckResult:
    """Score image-caption alignment (plan task 16.2).

    `scorer` and `threshold` must match: the default CLIP scorer pairs with
    `CLIP_THRESHOLD`; a vision-LLM scorer pairs with `VISION_ALIGNMENT_THRESHOLD`.
    """
    score = scorer(image_bytes, caption)
    passed = score >= threshold
    return CheckResult(
        name="image_caption_alignment",
        passed=passed,
        score=score,
        reason=None if passed else f"alignment score {score:.3f} < {threshold}",
        fail_action=GateAction.REGENERATE_IMAGE,
    )
