from __future__ import annotations

from app.services.generation.image_prompt.models import ImagePrompt, ImagePromptValidationResult

# Plan tasks 14.2-14.3:
#   14.2 parse + validate prompt length (< 4000 chars for Ideogram)
#   14.3 quality checks: no forbidden visual elements, brand color hex present,
#        no competitor visual references.
IDEOGRAM_MAX_PROMPT_CHARS = 4000


def validate_image_prompt(
    prompt: ImagePrompt,
    brand_color_hexes: list[str] | None = None,
    forbidden_terms: list[str] | None = None,
    max_prompt_chars: int = IDEOGRAM_MAX_PROMPT_CHARS,
) -> ImagePromptValidationResult:
    """Validate one image prompt, collecting all issues (non-fatal).

    `brand_color_hexes` and `forbidden_terms` come from the Brand KB
    (dos-and-donts / visual identity) — business content we don't have yet, so
    those checks are skipped when the lists are empty (the default).
    """
    issues: list[str] = []

    if not prompt.positive_prompt.strip():
        issues.append("positive_prompt is empty")
    elif len(prompt.positive_prompt) > max_prompt_chars:
        issues.append(
            f"positive_prompt exceeds {max_prompt_chars} chars ({len(prompt.positive_prompt)})"
        )

    if not prompt.negative_prompt.strip():
        issues.append("negative_prompt is empty")

    haystack = f"{prompt.positive_prompt}\n{prompt.negative_prompt}\n{prompt.text_overlay or ''}"
    haystack_lower = haystack.lower()

    if brand_color_hexes and not any(
        hex_code.lower() in haystack_lower for hex_code in brand_color_hexes
    ):
        issues.append("no brand color hex code present in the prompt")

    for term in forbidden_terms or []:
        if term.lower() in prompt.positive_prompt.lower():
            issues.append(f"forbidden/competitor visual reference: {term}")

    return ImagePromptValidationResult(is_valid=not issues, issues=issues)
