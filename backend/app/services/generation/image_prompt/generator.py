from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from pydantic import ValidationError

from app.services.bedrock import BedrockLLMClient, BedrockResponseParseError
from app.services.generation.image_prompt.models import (
    ImagePrompt,
    ImagePromptRequest,
    ImagePromptValidationResult,
)
from app.services.generation.image_prompt.prompt_builder import (
    build_system_prompt,
    build_user_message,
)
from app.services.generation.image_prompt.validator import validate_image_prompt

logger = logging.getLogger(__name__)


@dataclass
class ScoredImagePrompt:
    caption: str
    prompt: ImagePrompt
    validation: ImagePromptValidationResult


@dataclass
class ImagePromptGenerationResult:
    """Result of image-prompt generation (architecture doc 4.3).

    One prompt per caption variant, appended to the TCO as image_prompts[]
    downstream. Invalid prompts (tasks 14.2-14.3) are kept but flagged rather
    than dropped.
    """

    prompts: list[ScoredImagePrompt] = field(default_factory=list)

    @property
    def valid_prompts(self) -> list[ImagePrompt]:
        return [sp.prompt for sp in self.prompts if sp.validation.is_valid]


def generate_image_prompts(
    request: ImagePromptRequest,
    client: BedrockLLMClient,
    brand_color_hexes: list[str] | None = None,
    forbidden_terms: list[str] | None = None,
) -> ImagePromptGenerationResult:
    """Generate one optimized image prompt per caption via Sonnet (Module 14).

    Assembles the prompt from the request (caption + visual patterns + brand
    visual rules + platform specs + dos-and-donts), calls Sonnet for a JSON
    object of image prompts, then parses/validates each and aligns it to its
    caption by order.
    """
    if not request.captions:
        return ImagePromptGenerationResult()

    system_prompt = build_system_prompt(request)
    user_message = build_user_message(request)
    raw = client.complete_json(system_prompt, user_message)

    raw_prompts = raw.get("image_prompts")
    if not isinstance(raw_prompts, list):
        raise BedrockResponseParseError(
            "Image-prompt response missing an 'image_prompts' array", json.dumps(raw)
        )

    if len(raw_prompts) != len(request.captions):
        logger.warning(
            "Model returned %s image prompts for %s captions; pairing by order",
            len(raw_prompts),
            len(request.captions),
        )

    result = ImagePromptGenerationResult()
    for caption, raw_prompt in zip(request.captions, raw_prompts, strict=False):
        try:
            prompt = ImagePrompt.model_validate(raw_prompt)
        except ValidationError as exc:
            logger.warning("Skipping malformed image prompt: %s", exc)
            continue
        validation = validate_image_prompt(
            prompt, brand_color_hexes=brand_color_hexes, forbidden_terms=forbidden_terms
        )
        result.prompts.append(
            ScoredImagePrompt(caption=caption, prompt=prompt, validation=validation)
        )

    return result
