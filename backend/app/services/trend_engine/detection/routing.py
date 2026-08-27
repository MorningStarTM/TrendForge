from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.services.trend_engine.detection.classifier import DetectionResult

RoutingDecision = Literal["auto_queue", "slack_review", "auto_reject"]

DEFAULT_AUTO_QUEUE_THRESHOLD = 75.0
DEFAULT_SLACK_REVIEW_THRESHOLD = 50.0


@dataclass
class RoutingResult:
    decision: RoutingDecision
    reason: str


def route_detection_result(
    result: DetectionResult,
    auto_queue_threshold: float = DEFAULT_AUTO_QUEUE_THRESHOLD,
    slack_review_threshold: float = DEFAULT_SLACK_REVIEW_THRESHOLD,
) -> RoutingResult:
    """Decision routing on brand_fit_score (architecture doc 3.2):

    > auto_queue_threshold  -> auto-queue for TCO building / generation
    slack_review_threshold..auto_queue_threshold -> Slack spot-check by HOP
    < slack_review_threshold -> auto-reject, logged for scoring calibration
    """
    score = result.brand_fit_score

    if score > auto_queue_threshold:
        return RoutingResult(
            "auto_queue", f"brand_fit_score={score} > {auto_queue_threshold}"
        )
    if score >= slack_review_threshold:
        return RoutingResult(
            "slack_review",
            f"{slack_review_threshold} <= brand_fit_score={score} <= {auto_queue_threshold}",
        )
    return RoutingResult(
        "auto_reject", f"brand_fit_score={score} < {slack_review_threshold}"
    )
