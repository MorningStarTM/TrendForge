from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AspectRatio = Literal["1:1", "9:16", "16:9", "4:5"]


class ImagePromptRequest(BaseModel):
    """Input to image-prompt generation, assembled from TCO fields (architecture doc 4.3).

    Like `CaptionRequest`, this is the focused TCO slice this step needs rather
    than the (not-yet-built) full TCO object. It carries the visual_patterns
    fields as plain values — instead of importing the trend-engine
    `VisualPatterns` type — so generation stays decoupled from trend_engine;
    the future TCO Builder / orchestrator maps VisualPatterns onto these.
    """

    # One image prompt is produced per caption (doc 4.3: "for each caption
    # variant, Sonnet outputs an image prompt object").
    captions: list[str] = Field(default_factory=list)

    # From TCO visual_patterns (Haiku visual analysis of top posts).
    dominant_format: str | None = None
    color_palette: list[str] = Field(default_factory=list)
    composition_style: str | None = None
    text_on_image_patterns: str | None = None

    # From the Brand KB RAG layer.
    brand_visual_context: list[str] = Field(default_factory=list)  # visual identity guide
    dos_and_donts: list[str] = Field(default_factory=list)  # source for the negative prompt

    # Target platforms drive aspect ratio (doc 4.3 platform specs).
    platforms: list[str] = Field(default_factory=list)


class ImagePrompt(BaseModel):
    """One generated image prompt (architecture doc 4.3 output format)."""

    positive_prompt: str
    negative_prompt: str
    aspect_ratio: AspectRatio
    style_reference: str | None = None
    text_overlay: str | None = None


class ImagePromptValidationResult(BaseModel):
    """Outcome of validating one image prompt (plan tasks 14.2-14.3).

    Non-fatal: issues are collected rather than raised so the generator keeps
    valid prompts and flags the rest.
    """

    is_valid: bool
    issues: list[str] = Field(default_factory=list)
