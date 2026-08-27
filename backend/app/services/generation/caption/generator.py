from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.services.bedrock import BedrockLLMClient, BedrockResponseParseError
from app.services.generation.caption.models import (
    CaptionRequest,
    CaptionValidationResult,
    CaptionVariant,
)
from app.services.generation.caption.prompt_builder import build_system_prompt, build_user_message
from app.services.generation.caption.validator import validate_variant

logger = logging.getLogger(__name__)


@dataclass
class ScoredCaptionVariant:
    variant: CaptionVariant
    validation: CaptionValidationResult


@dataclass
class CaptionGenerationResult:
    """Result of caption generation for one trend (architecture doc 4.2).

    `variants` are appended to the TCO as generated_captions[] downstream.
    Invalid variants (task 13.3) are kept but flagged rather than dropped, so
    a reviewer can still see them.
    """

    variants: list[ScoredCaptionVariant] = field(default_factory=list)

    @property
    def valid_variants(self) -> list[CaptionVariant]:
        return [sv.variant for sv in self.variants if sv.validation.is_valid]


def generate_captions(
    request: CaptionRequest,
    client: BedrockLLMClient,
    max_caption_chars: int | None = None,
) -> CaptionGenerationResult:
    """Generate 2-3 caption variants for a trend via Sonnet (Module 13).

    Assembles the prompt from the request (TCO slice + Brand KB context),
    calls Sonnet for a JSON object of variants, parses/validates each, and
    returns them. Refinement mode is automatic: if `request.refinement_notes`
    is set, the prompt incorporates the reviewer feedback (task 13.4).
    """
    system_prompt = build_system_prompt(request)
    user_message = build_user_message(request)
    raw = client.complete_json(system_prompt, user_message)

    raw_variants = raw.get("variants")
    if not isinstance(raw_variants, list):
        raise BedrockResponseParseError(
            "Caption response missing a 'variants' array", json.dumps(raw)
        )

    result = CaptionGenerationResult()
    for raw_variant in raw_variants:
        try:
            variant = CaptionVariant.model_validate(raw_variant)
        except ValidationError as exc:
            logger.warning("Skipping malformed caption variant: %s", exc)
            continue
        validation = validate_variant(
            variant,
            **({"max_caption_chars": max_caption_chars} if max_caption_chars is not None else {}),
        )
        result.variants.append(ScoredCaptionVariant(variant=variant, validation=validation))

    return result
