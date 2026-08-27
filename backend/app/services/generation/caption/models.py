from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Market = Literal["KSA", "UAE", "BOTH"]
Language = Literal["ar", "en", "bilingual"]
Tone = Literal["playful", "witty", "bold", "informative"]


class CaptionRequest(BaseModel):
    """Input to caption generation, assembled from TCO fields (architecture doc 4.2).

    The full TCO Builder (Module 10) isn't built yet, so this is the focused
    slice of the TCO that caption generation actually needs. A future TCO
    Builder / generation orchestrator populates it from the DetectionResult
    (trend_summary, brand_angle, category), the trend candidate (source posts,
    trending hashtags), the Brand KB retrieval (brand_context), regional
    config, and any reviewer refinement notes.
    """

    trend_summary: str
    brand_angle: str
    category: str
    source_post_texts: list[str] = Field(default_factory=list)
    trending_hashtags: list[str] = Field(default_factory=list)
    trending_audio: str | None = None
    market: Market = "BOTH"
    regional_notes: str | None = None
    brand_context: list[str] = Field(default_factory=list)
    refinement_notes: list[str] = Field(default_factory=list)
    num_variants: int = 3


class CaptionVariant(BaseModel):
    """One generated caption variant (architecture doc 4.2 output format)."""

    caption: str
    hashtags: list[str] = Field(default_factory=list)
    cta: str
    language: Language
    market: Market
    tone: Tone


class CaptionValidationResult(BaseModel):
    """Outcome of validating a variant (architecture doc / plan task 13.3).

    Non-fatal: issues are collected rather than raised so the generator can
    keep valid variants and log/flag the rest instead of failing the batch.
    """

    is_valid: bool
    issues: list[str] = Field(default_factory=list)
