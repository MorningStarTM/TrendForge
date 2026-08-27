"""Content generation for a detected trend, via AWS Bedrock.

Chains the real models: Haiku classifies the trend (Module 9), then Sonnet
writes caption variants (Module 13) and one image prompt per caption
(Module 14), fed by the trend's extracted `generation_inputs` (hashtags,
captions, audio). Everything runs on Bedrock using the models configured in
settings.

Single-process, in-memory cache of the last generation per trend.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.services import trend_detection
from app.services.generation.caption.generator import generate_captions
from app.services.generation.caption.models import CaptionRequest
from app.services.generation.caption.sonnet_client import SonnetClient
from app.services.generation.image_prompt.generator import generate_image_prompts
from app.services.generation.image_prompt.models import ImagePromptRequest
from app.services.trend_engine.detection.classifier import classify_candidate
from app.services.trend_engine.detection.haiku_client import HaikuClient

logger = logging.getLogger(__name__)

# Last generation per trend id (single process).
_generated: dict[str, dict[str, Any]] = {}


def _haiku_client() -> HaikuClient:
    s = get_settings()
    # aws_* may be None -> AnthropicBedrock falls back to the standard AWS
    # credential chain (~/.aws, env, IAM role).
    return HaikuClient(
        aws_access_key=s.aws_access_key_id,
        aws_secret_key=s.aws_secret_access_key,
        aws_region=s.bedrock_region,
        model_id=s.haiku_model_id,
    )


def _sonnet_client() -> SonnetClient:
    s = get_settings()
    return SonnetClient(
        aws_access_key=s.aws_access_key_id,
        aws_secret_key=s.aws_secret_access_key,
        aws_region=s.bedrock_region,
        model_id=s.sonnet_model_id,
    )


def generate_for_trend(trend_id: str) -> dict[str, Any]:
    """Classify (Haiku) → captions (Sonnet) → image prompts (Sonnet) for a trend."""
    scored = trend_detection.get_scored(trend_id)
    trend = trend_detection.get_trend(trend_id)
    if scored is None or trend is None:
        raise KeyError(trend_id)
    inputs = trend.get("generation_inputs", {})

    # 1. Classify the trend with Haiku (trend_summary, brand_angle, category, scores).
    detection = classify_candidate(scored, _haiku_client())

    # 2. Caption variants with Sonnet.
    sonnet = _sonnet_client()
    audio = inputs.get("trending_audio") or []
    caption_req = CaptionRequest(
        trend_summary=detection.trend_summary,
        brand_angle=detection.brand_angle,
        category=detection.category,
        source_post_texts=inputs.get("captions", []),
        trending_hashtags=inputs.get("trending_hashtags", []),
        trending_audio=audio[0] if audio else None,
        market="BOTH",
        num_variants=3,
    )
    caption_result = generate_captions(caption_req, sonnet)

    # 3. One image prompt per caption with Sonnet.
    variants = [sv.variant for sv in caption_result.variants]
    image_prompts = []
    if variants:
        image_result = generate_image_prompts(
            ImagePromptRequest(
                captions=[v.caption for v in variants],
                platforms=inputs.get("platforms", []),
            ),
            sonnet,
        )
        image_prompts = [sp.prompt for sp in image_result.prompts]

    # Pair caption + image prompt by order.
    paired: list[dict[str, Any]] = []
    for i, sv in enumerate(caption_result.variants):
        prompt = image_prompts[i] if i < len(image_prompts) else None
        paired.append(
            {
                "caption": sv.variant.caption,
                "hashtags": sv.variant.hashtags,
                "cta": sv.variant.cta,
                "language": sv.variant.language,
                "market": sv.variant.market,
                "tone": sv.variant.tone,
                "valid": sv.validation.is_valid,
                "issues": sv.validation.issues,
                "image_prompt": None
                if prompt is None
                else {
                    "positive_prompt": prompt.positive_prompt,
                    "negative_prompt": prompt.negative_prompt,
                    "aspect_ratio": prompt.aspect_ratio,
                    "style_reference": prompt.style_reference,
                    "text_overlay": prompt.text_overlay,
                },
            }
        )

    result = {
        "trend_id": trend_id,
        "classification": {
            "relevance_score": detection.relevance_score,
            "brand_fit_score": detection.brand_fit_score,
            "category": detection.category,
            "trend_summary": detection.trend_summary,
            "brand_angle": detection.brand_angle,
            "urgency": detection.urgency,
            "estimated_lifespan": detection.estimated_lifespan,
            "risk_flags": detection.risk_flags,
        },
        "variants": paired,
    }
    _generated[trend_id] = result
    logger.info("Generated %s caption variants for trend %s", len(paired), trend_id)
    return result


def get_generated(trend_id: str) -> dict[str, Any] | None:
    return _generated.get(trend_id)


def generate_image_for_variant(trend_id: str, index: int) -> tuple[str, bytes]:
    """Render an image (Gemini) for one caption variant's image prompt.

    Returns (mime_type, raw_bytes). The trend must have been generated first
    (so the variant + its image prompt exist in the cache).
    """
    from app.services.generation.image_gen.gemini_client import generate_image

    generated = _generated.get(trend_id)
    if generated is None:
        raise KeyError(trend_id)
    variants = generated.get("variants", [])
    if index < 0 or index >= len(variants):
        raise KeyError(f"{trend_id}#{index}")

    image_prompt = variants[index].get("image_prompt")
    if not image_prompt or not image_prompt.get("positive_prompt"):
        raise ValueError("This variant has no image prompt to render.")

    # Build the text prompt: positive, plus aspect-ratio and negative hints
    # (nano banana takes a single text prompt, not separate fields).
    prompt = image_prompt["positive_prompt"]
    if image_prompt.get("aspect_ratio"):
        prompt += f"\n\nAspect ratio: {image_prompt['aspect_ratio']}."
    if image_prompt.get("text_overlay"):
        prompt += f"\nInclude text overlay: {image_prompt['text_overlay']}."
    if image_prompt.get("negative_prompt"):
        prompt += f"\nAvoid: {image_prompt['negative_prompt']}."

    s = get_settings()
    if not s.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")
    mime, data = generate_image(
        prompt, api_key=s.gemini_api_key, model=s.gemini_image_model
    )
    logger.info("Rendered image for trend %s variant %s (%s)", trend_id, index, mime)
    return mime, data
