from __future__ import annotations

from app.services.bedrock import BedrockLLMClient
from app.services.generation.caption.models import Market
from app.services.generation.image_prompt.models import ImagePrompt
from app.services.generation.quality_gate.brand_compliance import check_brand_compliance
from app.services.generation.quality_gate.clip_alignment import (
    CLIP_THRESHOLD,
    AlignmentScorer,
    check_image_caption_alignment,
    default_clip_scorer,
)
from app.services.generation.quality_gate.duplicate_check import (
    PublishedCaptionStore,
    check_duplicate_caption,
)
from app.services.generation.quality_gate.models import (
    QualityGateResult,
    aggregate_action,
)
from app.services.generation.quality_gate.safety_check import check_text_safety


def run_quality_gate(
    caption: str,
    market: Market = "BOTH",
    image_prompt: ImagePrompt | None = None,
    image_bytes: bytes | None = None,
    safety_client: BedrockLLMClient | None = None,
    duplicate_store: PublishedCaptionStore | None = None,
    alignment_scorer: AlignmentScorer = default_clip_scorer,
    alignment_threshold: float = CLIP_THRESHOLD,
    non_halal_terms: list[str] | None = None,
    forbidden_colors: list[str] | None = None,
) -> QualityGateResult:
    """Run the quality gate on one content variant (plan Module 16 / doc 4.5).

    Runs whichever checks their inputs allow and aggregates them into a single
    action (the most severe failure): text safety (needs a Haiku client),
    rule-based brand compliance (always), duplicate check (needs a published-
    caption store), and image-caption alignment (needs generated image bytes,
    which don't exist until Module 15). A check whose input isn't provided is
    skipped, not failed — in production all inputs should be supplied.

    `alignment_scorer` defaults to CLIP; pass a Claude-vision scorer (see
    `vision_alignment.make_claude_vision_scorer`) with its own
    `alignment_threshold` to swap in the LLM-judge approach.
    """
    checks = []

    if safety_client is not None:
        checks.append(check_text_safety(caption, safety_client))

    checks.extend(
        check_brand_compliance(
            caption=caption,
            image_positive_prompt=image_prompt.positive_prompt if image_prompt else None,
            aspect_ratio=image_prompt.aspect_ratio if image_prompt else None,
            non_halal_terms=non_halal_terms,
            forbidden_colors=forbidden_colors,
        )
    )

    if duplicate_store is not None:
        checks.append(check_duplicate_caption(caption, duplicate_store))

    if image_bytes is not None:
        checks.append(
            check_image_caption_alignment(
                image_bytes, caption, threshold=alignment_threshold, scorer=alignment_scorer
            )
        )

    return QualityGateResult(action=aggregate_action(checks), checks=checks)
