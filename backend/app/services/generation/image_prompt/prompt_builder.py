from __future__ import annotations

from app.services.generation.image_prompt.models import ImagePromptRequest

# Architecture doc 4.3: assemble the image-prompt from the caption (what the
# image must illustrate), the trend's visual patterns, brand visual rules from
# the KB, platform aspect-ratio specs, and dos-and-donts (negative prompt).
#
# The base role/brand-visual identity here is a PLACEHOLDER (business content,
# like the caption base prompt); the real visual guide is injected at runtime
# from `request.brand_visual_context` (Brand KB retrieval).

_BASE_SYSTEM_PROMPT = """\
You are an expert image-generation prompt engineer for Papa John's social
media in the KSA and UAE markets. Turn a finished caption into an optimized
prompt for an image model (Ideogram / DALL-E), matching the trend's visual
style while staying on-brand. Follow the brand visual guidelines below."""

# Platform -> recommended aspect ratio (doc 4.3).
PLATFORM_ASPECT_RATIOS: dict[str, str] = {
    "instagram": "1:1 (feed) or 9:16 (stories/reels)",
    "tiktok": "9:16",
    "youtube": "16:9 (video) or 9:16 (shorts)",
    "facebook": "1:1 or 4:5",
    "x": "16:9",
    "snapchat": "9:16",
}

_OUTPUT_SCHEMA_INSTRUCTION = """\
Respond with ONLY a JSON object, no other text. Return one image prompt per
caption, in the same order as the captions:
{
  "image_prompts": [
    {
      "positive_prompt": <detailed prompt: style, composition, subject, mood, lighting>,
      "negative_prompt": <what to exclude: competitor colors, non-halal items, text errors>,
      "aspect_ratio": <"1:1" | "9:16" | "16:9" | "4:5">,
      "style_reference": <the trend's dominant visual format, e.g. "reaction shot", "flat lay">,
      "text_overlay": <any text to render on the image (CTA / hashtag / trend phrase), or null>
    }
  ]
}"""


def build_system_prompt(request: ImagePromptRequest) -> str:
    parts = [_BASE_SYSTEM_PROMPT]
    if request.brand_visual_context:
        joined = "\n\n".join(f"- {chunk}" for chunk in request.brand_visual_context)
        parts.append(f"Brand visual guidelines:\n{joined}")
    parts.append(_OUTPUT_SCHEMA_INSTRUCTION)
    return "\n\n".join(parts)


def _aspect_ratio_guidance(platforms: list[str]) -> str:
    if not platforms:
        return "Aspect ratio: default to 1:1."
    lines = [
        f"- {platform}: {PLATFORM_ASPECT_RATIOS.get(platform, '1:1')}" for platform in platforms
    ]
    return "Target platforms and aspect ratios:\n" + "\n".join(lines)


def build_user_message(request: ImagePromptRequest) -> str:
    sections: list[str] = ["Captions to illustrate (one image prompt each, in order):"]
    sections.extend(f"{i + 1}. {caption}" for i, caption in enumerate(request.captions))

    visual_lines: list[str] = []
    if request.dominant_format:
        visual_lines.append(f"- Dominant format: {request.dominant_format}")
    if request.color_palette:
        visual_lines.append(f"- Color palette: {', '.join(request.color_palette)}")
    if request.composition_style:
        visual_lines.append(f"- Composition style: {request.composition_style}")
    if request.text_on_image_patterns:
        visual_lines.append(f"- Text-on-image patterns: {request.text_on_image_patterns}")
    if visual_lines:
        sections.append("\nTrending visual patterns to match:\n" + "\n".join(visual_lines))

    sections.append("\n" + _aspect_ratio_guidance(request.platforms))

    if request.dos_and_donts:
        joined = "\n".join(f"- {rule}" for rule in request.dos_and_donts)
        sections.append(f"\nDos and don'ts (fold the don'ts into the negative prompt):\n{joined}")

    return "\n".join(sections)
