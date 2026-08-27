from __future__ import annotations

from datetime import UTC, datetime

import pytest
from app.services.ingestion.normalizer.post_schema import RawPost
from app.services.trend_engine.detection.classifier import (
    DetectionResult,
    build_user_message,
    classify_candidate,
)
from app.services.trend_engine.detection.haiku_client import HaikuResponseParseError
from app.services.trend_engine.rule_engine.clustering import TrendCandidate
from app.services.trend_engine.rule_engine.engine import ScoredTrendCandidate
from app.services.trend_engine.rule_engine.velocity_scorer import VelocityScore

NOW = datetime.now(UTC)

VALID_DETECTION_JSON = {
    "relevance_score": 85,
    "brand_fit_score": 78,
    "category": "food_challenge",
    "trend_summary": "A viral pizza-eating challenge is trending across platforms.",
    "brand_angle": "Papa John's could sponsor a branded version of the challenge.",
    "risk_flags": [],
    "estimated_lifespan": "short",
    "urgency": "same_day",
}


def make_post(text: str = "pizza post", engagement_rate: float = 0.05) -> RawPost:
    return RawPost.model_validate(
        {
            "platform": "instagram",
            "platform_post_id": "1",
            "text": text,
            "posted_at": NOW,
            "engagement_rate": engagement_rate,
        }
    )


def make_scored_candidate() -> ScoredTrendCandidate:
    candidate = TrendCandidate(hashtag="pizza", hashtags={"pizza"}, posts=[make_post()])
    velocity = VelocityScore(
        spike_6hr=True,
        volume_24hr=False,
        engagement_acceleration=False,
        cross_platform=True,
        creator_tier=False,
    )
    return ScoredTrendCandidate(candidate=candidate, velocity=velocity)


class _FakeHaikuClient:
    def __init__(self, response: dict[str, object]) -> None:
        self._response = response
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system_prompt: str, user_message: str) -> dict[str, object]:
        self.calls.append((system_prompt, user_message))
        return self._response


def test_build_user_message_includes_hashtags_platforms_and_signals() -> None:
    scored = make_scored_candidate()

    message = build_user_message(scored.candidate, scored.velocity)

    assert "pizza" in message
    assert "signals passed: 2/5" in message.lower() or "2/5" in message
    assert "spike=True" in message
    assert "pizza post" in message


def test_classify_candidate_parses_valid_response_into_detection_result() -> None:
    scored = make_scored_candidate()
    client = _FakeHaikuClient(VALID_DETECTION_JSON)

    result = classify_candidate(scored, client)  # type: ignore[arg-type]

    assert isinstance(result, DetectionResult)
    assert result.relevance_score == 85
    assert result.brand_fit_score == 78
    assert result.category == "food_challenge"
    assert result.estimated_lifespan == "short"
    assert result.urgency == "same_day"
    assert client.calls[0][1] == build_user_message(scored.candidate, scored.velocity)


def test_classify_candidate_raises_on_schema_mismatch() -> None:
    scored = make_scored_candidate()
    client = _FakeHaikuClient({"relevance_score": "not a number"})

    with pytest.raises(HaikuResponseParseError):
        classify_candidate(scored, client)  # type: ignore[arg-type]


def test_detection_result_defaults_risk_flags_to_empty_list() -> None:
    payload = dict(VALID_DETECTION_JSON)
    del payload["risk_flags"]

    result = DetectionResult.model_validate(payload)

    assert result.risk_flags == []
