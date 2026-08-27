from __future__ import annotations

from app.services.generation.caption.models import CaptionRequest

# Architecture doc 4.2: the caption prompt is assembled from TCO fields in a
# specific order. The system prompt grounds the model in Papa John's brand
# voice (retrieved from the Brand KB); the user message carries the trend
# briefing, reference posts, trending signals, regional rules, and — on a
# re-generation — reviewer refinement notes.
#
# The base brand identity here is a PLACEHOLDER (business/creative content,
# like the detection system prompt and blacklist). The real brand voice is
# injected at runtime from `request.brand_context` (Brand KB retrieval).

_BASE_SYSTEM_PROMPT = """\
You are a social media copywriter for Papa John's in the KSA and UAE markets.
Write captions that are on-trend but unmistakably in Papa John's brand voice.
Ground every caption in the brand voice guidelines below."""

# Sonnet returns an object wrapping the variant array, so the response stays a
# JSON object (what the Bedrock client's complete_json expects).
_OUTPUT_SCHEMA_INSTRUCTION = """\
Respond with ONLY a JSON object, no other text:
{
  "variants": [
    {
      "caption": <post text, in the trend's language/vibe but Papa John's voice>,
      "hashtags": <array mixing trending hashtags + branded tags like #PapaJohnsUAE>,
      "cta": <call-to-action, e.g. "Order now" / "Tag a friend who'd try this">,
      "language": <"ar" | "en" | "bilingual">,
      "market": <"KSA" | "UAE" | "BOTH">,
      "tone": <"playful" | "witty" | "bold" | "informative">
    }
  ]
}"""


def build_system_prompt(request: CaptionRequest) -> str:
    """System prompt = base role + brand voice from the Brand KB + output schema."""
    parts = [_BASE_SYSTEM_PROMPT]
    if request.brand_context:
        joined = "\n\n".join(f"- {chunk}" for chunk in request.brand_context)
        parts.append(f"Brand voice guidelines:\n{joined}")
    parts.append(_OUTPUT_SCHEMA_INSTRUCTION)
    return "\n\n".join(parts)


def build_user_message(request: CaptionRequest) -> str:
    """User message = trend briefing + reference posts + signals + regional rules.

    On a re-generation (refinement_notes present, task 13.4), reviewer feedback
    is appended so the model produces an improved version.
    """
    sections: list[str] = [
        "Trend briefing:",
        f"- Summary: {request.trend_summary}",
        f"- Suggested brand angle: {request.brand_angle}",
        f"- Category: {request.category}",
        f"- Target market: {request.market}",
        f"\nGenerate {request.num_variants} distinct caption variants.",
    ]

    if request.source_post_texts:
        refs = "\n".join(f"- {text[:200]!r}" for text in request.source_post_texts[:3])
        sections.append(f"\nHow people are talking about this trend (reference posts):\n{refs}")

    if request.trending_hashtags:
        sections.append(f"\nTrending hashtags to consider: {', '.join(request.trending_hashtags)}")
    if request.trending_audio:
        sections.append(f"Trending audio: {request.trending_audio}")

    if request.regional_notes:
        sections.append(f"\nRegional rules ({request.market}): {request.regional_notes}")

    if request.refinement_notes:
        notes = "; ".join(request.refinement_notes)
        sections.append(
            "\nThe previous version was rejected. Reviewer feedback: "
            f"{notes}. Generate an improved version addressing this feedback."
        )

    return "\n".join(sections)
