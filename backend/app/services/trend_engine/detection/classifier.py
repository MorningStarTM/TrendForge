from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel, ValidationError

from app.services.trend_engine.detection.haiku_client import HaikuClient, HaikuResponseParseError
from app.services.trend_engine.rule_engine.clustering import TrendCandidate
from app.services.trend_engine.rule_engine.engine import ScoredTrendCandidate
from app.services.trend_engine.rule_engine.velocity_scorer import VelocityScore

Category = Literal[
    "food_challenge",
    "meme_format",
    "cultural_moment",
    "audio_trend",
    "visual_trend",
    "news_reaction",
]
EstimatedLifespan = Literal["flash", "short", "medium", "long"]
Urgency = Literal["immediate", "same_day", "next_day", "low"]

# PLACEHOLDER SYSTEM PROMPT.
#
# Brand identity, category definitions with examples, and few-shot scored
# trend examples (architecture doc 3.2, task 9.2) are business/creative
# decisions for Papa John's KSA/UAE, not engineering ones — same category
# as the blacklist's seed content. Replace this before relying on real
# classifications. See also prompts/detection/system_prompt.md and
# few_shot_examples.md, which are the intended long-term home for this
# (likely versioned via the not-yet-built Prompt Version Manager, Module 24)
# — this inline default exists so the classifier works out of the box.
DEFAULT_SYSTEM_PROMPT = """\
You are a trend classification assistant for Papa John's social media in the \
KSA and UAE markets. Given a trend candidate (source posts, hashtags, and \
velocity signals), classify it for relevance and brand fit.

Categories: food_challenge, meme_format, cultural_moment, audio_trend, \
visual_trend, news_reaction.

Respond with ONLY a JSON object matching this exact schema, no other text:
{
  "relevance_score": <0-100 integer, how relevant to QSR/food/culture/lifestyle>,
  "brand_fit_score": <0-100 integer, how well Papa John's can authentically participate>,
  "category": <one of the categories above>,
  "trend_summary": <2-3 sentence description of the trend>,
  "brand_angle": <suggested creative direction for Papa John's>,
  "risk_flags": <array from: cultural_sensitivity, competitor_adjacent, controversial, short_lived>,
  "estimated_lifespan": <one of: flash, short, medium, long>,
  "urgency": <one of: immediate, same_day, next_day, low>
}
"""


class DetectionResult(BaseModel):
    """Haiku's structured classification of a trend candidate (architecture doc 3.2)."""

    relevance_score: int
    brand_fit_score: int
    category: Category
    trend_summary: str
    brand_angle: str
    risk_flags: list[str] = []
    estimated_lifespan: EstimatedLifespan
    urgency: Urgency


def _format_top_posts(candidate: TrendCandidate, limit: int = 5) -> str:
    top_posts = sorted(candidate.posts, key=lambda post: post.engagement_rate, reverse=True)[:limit]
    lines = [
        f"- [{post.platform}] {post.text[:200]!r} "
        f"(likes={post.engagement.likes}, views={post.engagement.views})"
        for post in top_posts
    ]
    return "\n".join(lines) if lines else "(no posts)"


def build_user_message(candidate: TrendCandidate, velocity: VelocityScore) -> str:
    """Assemble the trend candidate + velocity stats into Haiku's input (doc 3.2)."""
    hashtags = sorted(candidate.hashtags or {candidate.hashtag})
    return (
        f"Hashtags: {', '.join(hashtags)}\n"
        f"Platforms: {candidate.platform_breakdown}\n"
        f"Velocity signals passed: {velocity.signals_passed}/5 "
        f"(spike={velocity.spike_6hr}, volume={velocity.volume_24hr}, "
        f"engagement_acceleration={velocity.engagement_acceleration}, "
        f"cross_platform={velocity.cross_platform}, creator_tier={velocity.creator_tier})\n\n"
        f"Top posts by engagement:\n{_format_top_posts(candidate)}"
    )


def classify_candidate(
    scored: ScoredTrendCandidate,
    client: HaikuClient,
    system_prompt: str = DEFAULT_SYSTEM_PROMPT,
) -> DetectionResult:
    """Classify a Rule Engine candidate for relevance and brand fit (doc 3.2, task 9.2)."""
    user_message = build_user_message(scored.candidate, scored.velocity)
    raw = client.complete_json(system_prompt, user_message)

    try:
        return DetectionResult.model_validate(raw)
    except ValidationError as exc:
        raise HaikuResponseParseError(
            f"Haiku's JSON didn't match the DetectionResult schema: {exc}", json.dumps(raw)
        ) from exc
