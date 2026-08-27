from __future__ import annotations

from app.services.generation.caption.models import CaptionValidationResult, CaptionVariant

# Architecture doc / plan task 13.3: validate caption length within platform
# limits, hashtag count within best practices (5-15), CTA present, language
# matches market config.

# Instagram/TikTok captions run long; the tightest common limit is X's 280.
# Kept generous by default (a variant carries a market, not one platform) and
# configurable.
DEFAULT_MAX_CAPTION_CHARS = 2200
MIN_HASHTAGS = 5
MAX_HASHTAGS = 15


def validate_variant(
    variant: CaptionVariant,
    max_caption_chars: int = DEFAULT_MAX_CAPTION_CHARS,
) -> CaptionValidationResult:
    """Validate one caption variant, collecting all issues (non-fatal)."""
    issues: list[str] = []

    if not variant.caption.strip():
        issues.append("caption is empty")
    elif len(variant.caption) > max_caption_chars:
        issues.append(f"caption exceeds {max_caption_chars} chars ({len(variant.caption)})")

    hashtag_count = len(variant.hashtags)
    if hashtag_count < MIN_HASHTAGS:
        issues.append(f"too few hashtags ({hashtag_count} < {MIN_HASHTAGS})")
    elif hashtag_count > MAX_HASHTAGS:
        issues.append(f"too many hashtags ({hashtag_count} > {MAX_HASHTAGS})")

    if not variant.cta.strip():
        issues.append("CTA is missing")

    # Language should match the market: KSA is Arabic-dominant, so an
    # English-only caption for KSA is flagged (bilingual/ar are fine).
    if variant.market == "KSA" and variant.language == "en":
        issues.append("KSA market caption should be Arabic or bilingual, not English-only")

    return CaptionValidationResult(is_valid=not issues, issues=issues)
