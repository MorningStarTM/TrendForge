from __future__ import annotations

import json
import logging

from pydantic import BaseModel, ValidationError

from app.services.bedrock import BedrockLLMClient, BedrockResponseParseError
from app.services.generation.quality_gate.clip_alignment import AlignmentScorer

logger = logging.getLogger(__name__)

# A vision-LLM judge scores alignment on a 0-1 semantic scale (1 = perfect
# match), unlike CLIP's compressed ~0.2-0.35 range — so it uses a higher pass
# threshold. Pass this alongside the vision scorer to
# check_image_caption_alignment / run_quality_gate.
VISION_ALIGNMENT_THRESHOLD = 0.6

# Generated images are typically PNG; override per your image generator.
DEFAULT_IMAGE_MEDIA_TYPE = "image/png"

_ALIGNMENT_SYSTEM_PROMPT = """\
You judge how well an image matches a social media caption. Consider whether
the image depicts what the caption describes (subject, food item, mood).

Respond with ONLY a JSON object, no other text:
{
  "alignment_score": <number from 0.0 (unrelated) to 1.0 (perfect match)>,
  "reason": <short explanation of the score>
}"""


class _AlignmentVerdict(BaseModel):
    alignment_score: float
    reason: str = ""


def make_claude_vision_scorer(
    client: BedrockLLMClient,
    media_type: str = DEFAULT_IMAGE_MEDIA_TYPE,
) -> AlignmentScorer:
    """Build an alignment scorer backed by Claude vision (via Bedrock).

    A drop-in alternative to the CLIP scorer for task 16.2: reuses the Bedrock
    vision path we already have (`complete_json_with_images`), so no new LLM
    provider is needed. The client must point at a vision-capable model
    (`vision_model_id`). Returns a 0-1 score — pair it with
    VISION_ALIGNMENT_THRESHOLD.
    """

    def scorer(image_bytes: bytes, caption: str) -> float:
        raw = client.complete_json_with_images(
            _ALIGNMENT_SYSTEM_PROMPT,
            f"Caption:\n{caption}",
            [(media_type, image_bytes)],
        )
        try:
            verdict = _AlignmentVerdict.model_validate(raw)
        except ValidationError as exc:
            raise BedrockResponseParseError(
                f"Alignment response didn't match the expected schema: {exc}", json.dumps(raw)
            ) from exc

        # The judge's reason is useful context but the scorer interface only
        # returns a number; log it so it isn't lost.
        logger.info(
            "Vision alignment: score=%.3f reason=%s", verdict.alignment_score, verdict.reason
        )
        return max(0.0, min(1.0, verdict.alignment_score))

    return scorer
