from __future__ import annotations

from app.services.trend_engine.detection.classifier import DetectionResult
from app.services.trend_engine.detection.routing import route_detection_result

BASE_RESULT_KWARGS = {
    "category": "food_challenge",
    "trend_summary": "summary",
    "brand_angle": "angle",
    "estimated_lifespan": "short",
    "urgency": "same_day",
}


def make_result(brand_fit_score: int) -> DetectionResult:
    return DetectionResult.model_validate(
        {"relevance_score": 80, "brand_fit_score": brand_fit_score, **BASE_RESULT_KWARGS}
    )


def test_high_score_routes_to_auto_queue() -> None:
    result = route_detection_result(make_result(80))

    assert result.decision == "auto_queue"


def test_score_exactly_at_auto_queue_threshold_does_not_auto_queue() -> None:
    # doc: "> 75" is auto-queue, so exactly 75 falls into the review band.
    result = route_detection_result(make_result(75))

    assert result.decision == "slack_review"


def test_borderline_score_routes_to_slack_review() -> None:
    result = route_detection_result(make_result(60))

    assert result.decision == "slack_review"


def test_score_exactly_at_slack_review_threshold_routes_to_slack_review() -> None:
    result = route_detection_result(make_result(50))

    assert result.decision == "slack_review"


def test_low_score_routes_to_auto_reject() -> None:
    result = route_detection_result(make_result(30))

    assert result.decision == "auto_reject"


def test_thresholds_are_configurable() -> None:
    result = route_detection_result(make_result(90), auto_queue_threshold=95.0)

    assert result.decision == "slack_review"
