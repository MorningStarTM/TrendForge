from __future__ import annotations

from app.services.generation.quality_gate.models import CheckResult, GateAction

# Plan task 16.3 / architecture doc 4.5: rule-based checks — halal compliance
# (non-halal ingredients in the image prompt), correct aspect ratio, caption
# length within platform limits, no forbidden colors.

# Clearly non-halal ingredients for KSA/UAE. Deliberately does NOT include
# pepperoni/sausage — Papa John's sells halal (beef/chicken) versions in these
# markets, so flagging them would be a false positive. Tune as needed.
DEFAULT_NON_HALAL_TERMS = [
    "pork",
    "bacon",
    "ham",
    "prosciutto",
    "lard",
    "alcohol",
    "wine",
    "beer",
    "champagne",
    "vodka",
    "rum",
]
VALID_ASPECT_RATIOS = {"1:1", "9:16", "16:9", "4:5"}
DEFAULT_MAX_CAPTION_CHARS = 2200


def check_brand_compliance(
    caption: str,
    image_positive_prompt: str | None = None,
    aspect_ratio: str | None = None,
    non_halal_terms: list[str] | None = None,
    forbidden_colors: list[str] | None = None,
    max_caption_chars: int = DEFAULT_MAX_CAPTION_CHARS,
) -> list[CheckResult]:
    """Rule-based brand compliance checks (plan task 16.3).

    Returns one CheckResult per rule so they can carry different failure
    actions — a halal violation is an auto-REJECT, the rest are FLAGs.
    """
    checks: list[CheckResult] = []
    non_halal_terms = non_halal_terms if non_halal_terms is not None else DEFAULT_NON_HALAL_TERMS

    # Halal compliance — scan the image prompt for non-halal ingredients.
    if image_positive_prompt is not None:
        prompt_lower = image_positive_prompt.lower()
        found = [term for term in non_halal_terms if term.lower() in prompt_lower]
        checks.append(
            CheckResult(
                name="halal_compliance",
                passed=not found,
                reason=None if not found else f"non-halal ingredient(s) in image prompt: {found}",
                fail_action=GateAction.REJECT,
            )
        )

    # Aspect ratio must be one of the supported values.
    if aspect_ratio is not None:
        valid = aspect_ratio in VALID_ASPECT_RATIOS
        checks.append(
            CheckResult(
                name="aspect_ratio",
                passed=valid,
                reason=None if valid else f"unsupported aspect ratio: {aspect_ratio}",
                fail_action=GateAction.FLAG,
            )
        )

    # Caption length within platform limits.
    within_limit = len(caption) <= max_caption_chars
    checks.append(
        CheckResult(
            name="caption_length",
            passed=within_limit,
            reason=None if within_limit else f"caption exceeds {max_caption_chars} chars",
            fail_action=GateAction.FLAG,
        )
    )

    # Forbidden brand colors (business content — skipped unless supplied).
    if forbidden_colors and image_positive_prompt is not None:
        prompt_lower = image_positive_prompt.lower()
        found_colors = [c for c in forbidden_colors if c.lower() in prompt_lower]
        checks.append(
            CheckResult(
                name="forbidden_colors",
                passed=not found_colors,
                reason=None if not found_colors else f"forbidden color(s): {found_colors}",
                fail_action=GateAction.FLAG,
            )
        )

    return checks
