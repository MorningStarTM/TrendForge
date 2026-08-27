from __future__ import annotations

import json
import logging
from typing import Literal

import httpx
from pydantic import BaseModel, ValidationError

from app.services.ingestion.normalizer.post_schema import RawPost
from app.services.trend_engine.detection.haiku_client import HaikuClient, HaikuResponseParseError
from app.services.trend_engine.rule_engine.clustering import TrendCandidate

logger = logging.getLogger(__name__)

AnalysisMethod = Literal["metadata", "vision"]

MAX_IMAGES = 5
DOWNLOAD_TIMEOUT = 15.0

# Shared instruction tail so both strategies return the exact same JSON shape,
# which is what makes their outputs directly comparable during evaluation.
_OUTPUT_SCHEMA_INSTRUCTION = """\
Respond with ONLY a JSON object, no other text:
{
  "dominant_format": <e.g. "flat lay", "reaction video", "close-up food shot">,
  "color_palette": <array of 2-5 dominant colors as plain names or hex>,
  "composition_style": <e.g. "centered subject, shallow depth of field">,
  "text_on_image_patterns": <how on-image text/captions are used, or "none">
}
"""

_METADATA_SYSTEM_PROMPT = (
    "You infer the likely visual style of a social media trend from post "
    "METADATA ONLY (you cannot see the images). Base your inference on the "
    "media types, hashtags, and captions provided.\n\n" + _OUTPUT_SCHEMA_INSTRUCTION
)

_VISION_SYSTEM_PROMPT = (
    "You analyze the visual style of a social media trend from the ATTACHED "
    "IMAGES (thumbnails of the top posts).\n\n" + _OUTPUT_SCHEMA_INSTRUCTION
)


class VisualPatterns(BaseModel):
    """The TCO `visual_patterns` section (architecture doc 3.3).

    `analysis_method` records which strategy produced this so the two
    approaches can be compared during evaluation.
    """

    dominant_format: str
    color_palette: list[str] = []
    composition_style: str
    text_on_image_patterns: str
    analysis_method: AnalysisMethod


def _top_posts(candidate: TrendCandidate, limit: int = MAX_IMAGES) -> list[RawPost]:
    return sorted(candidate.posts, key=lambda post: post.engagement_rate, reverse=True)[:limit]


def _parse_visual_patterns(raw: dict[str, object], method: AnalysisMethod) -> VisualPatterns:
    raw = {**raw, "analysis_method": method}
    try:
        return VisualPatterns.model_validate(raw)
    except ValidationError as exc:
        raise HaikuResponseParseError(
            f"Haiku's JSON didn't match the VisualPatterns schema: {exc}", json.dumps(raw)
        ) from exc


def analyze_from_metadata(candidate: TrendCandidate, client: HaikuClient) -> VisualPatterns:
    """Option B — infer visual patterns from post metadata only (no images, cheap)."""
    posts = _top_posts(candidate)
    media_types = [post.media_type for post in posts if post.media_type]
    hashtags = sorted(candidate.hashtags or {candidate.hashtag})
    captions = [post.text[:200] for post in posts if post.text]

    user_message = (
        f"Media types: {media_types}\n"
        f"Hashtags: {', '.join(hashtags)}\n"
        f"Sample captions:\n" + "\n".join(f"- {caption!r}" for caption in captions)
    )
    raw = client.complete_json(_METADATA_SYSTEM_PROMPT, user_message)
    return _parse_visual_patterns(raw, "metadata")


def _download_thumbnails(
    posts: list[RawPost], http_client: httpx.Client | None = None
) -> list[tuple[str, bytes]]:
    """Download thumbnail bytes for posts that have a thumbnail_url.

    Thumbnails are downloaded (not passed as URLs) because platform CDN URLs
    expire. Failures are skipped individually — one dead URL shouldn't sink
    the whole analysis.
    """
    urls = [post.thumbnail_url for post in posts if post.thumbnail_url]
    owns_client = http_client is None
    http_client = http_client or httpx.Client(timeout=DOWNLOAD_TIMEOUT, follow_redirects=True)
    images: list[tuple[str, bytes]] = []
    try:
        for url in urls:
            try:
                response = http_client.get(url)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("Skipping thumbnail %s: %s", url, exc)
                continue
            media_type = response.headers.get("content-type", "image/jpeg").split(";")[0].strip()
            images.append((media_type, response.content))
    finally:
        if owns_client:
            http_client.close()
    return images


def analyze_from_vision(
    candidate: TrendCandidate,
    client: HaikuClient,
    http_client: httpx.Client | None = None,
) -> VisualPatterns:
    """Option A — analyze the actual thumbnail images of the top posts via vision.

    Falls back to metadata analysis if no thumbnails could be downloaded (e.g.
    every post lacked a thumbnail_url or all downloads failed), so the TCO's
    visual_patterns section is still populated rather than left empty.
    """
    posts = _top_posts(candidate)
    images = _download_thumbnails(posts, http_client=http_client)
    if not images:
        logger.info("No thumbnails available; falling back to metadata visual analysis")
        return analyze_from_metadata(candidate, client)

    hashtags = sorted(candidate.hashtags or {candidate.hashtag})
    user_message = f"Trend hashtags: {', '.join(hashtags)}\nAnalyze the attached thumbnails."
    raw = client.complete_json_with_images(_VISION_SYSTEM_PROMPT, user_message, images)
    return _parse_visual_patterns(raw, "vision")


def analyze_visual_patterns(
    candidate: TrendCandidate,
    client: HaikuClient,
    method: AnalysisMethod = "vision",
) -> VisualPatterns:
    """Dispatch to the chosen visual-analysis strategy (both share `VisualPatterns`)."""
    if method == "vision":
        return analyze_from_vision(candidate, client)
    return analyze_from_metadata(candidate, client)
