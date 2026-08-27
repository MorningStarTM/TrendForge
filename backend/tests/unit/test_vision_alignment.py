from __future__ import annotations

import pytest
from app.services.bedrock import BedrockResponseParseError
from app.services.generation.quality_gate.clip_alignment import check_image_caption_alignment
from app.services.generation.quality_gate.gate import run_quality_gate
from app.services.generation.quality_gate.models import GateAction
from app.services.generation.quality_gate.vision_alignment import (
    VISION_ALIGNMENT_THRESHOLD,
    make_claude_vision_scorer,
)


class _FakeVisionClient:
    def __init__(self, response: dict[str, object]) -> None:
        self._response = response
        self.image_calls: list[list[tuple[str, bytes]]] = []

    def complete_json_with_images(
        self, system_prompt: str, user_message: str, images: list[tuple[str, bytes]]
    ) -> dict[str, object]:
        self.image_calls.append(images)
        return self._response


def test_vision_scorer_returns_alignment_score() -> None:
    client = _FakeVisionClient({"alignment_score": 0.82, "reason": "image shows the pizza"})
    scorer = make_claude_vision_scorer(client)  # type: ignore[arg-type]

    score = scorer(b"\x89PNG-bytes", "a hot pizza")

    assert score == pytest.approx(0.82)
    # the image was actually sent to the vision client
    assert client.image_calls[0][0][1] == b"\x89PNG-bytes"


def test_vision_scorer_clamps_out_of_range_scores() -> None:
    client = _FakeVisionClient({"alignment_score": 1.5, "reason": "over"})
    scorer = make_claude_vision_scorer(client)  # type: ignore[arg-type]

    assert scorer(b"img", "cap") == 1.0


def test_vision_scorer_raises_on_bad_schema() -> None:
    client = _FakeVisionClient({"not_a_score": True})
    scorer = make_claude_vision_scorer(client)  # type: ignore[arg-type]

    with pytest.raises(BedrockResponseParseError):
        scorer(b"img", "cap")


def test_vision_scorer_swaps_into_the_alignment_check() -> None:
    client = _FakeVisionClient({"alignment_score": 0.9, "reason": "great match"})
    scorer = make_claude_vision_scorer(client)  # type: ignore[arg-type]

    result = check_image_caption_alignment(
        b"img", "a pizza", threshold=VISION_ALIGNMENT_THRESHOLD, scorer=scorer
    )

    assert result.passed is True
    assert result.score == pytest.approx(0.9)


def test_vision_scorer_swaps_into_the_full_gate() -> None:
    safety = _FakeSafetyClient({"safe": True, "flags": [], "reason": ""})
    vision = _FakeVisionClient({"alignment_score": 0.2, "reason": "wrong subject"})
    scorer = make_claude_vision_scorer(vision)  # type: ignore[arg-type]

    result = run_quality_gate(
        caption="a pizza",
        image_bytes=b"img",
        safety_client=safety,  # type: ignore[arg-type]
        alignment_scorer=scorer,
        alignment_threshold=VISION_ALIGNMENT_THRESHOLD,
    )

    # 0.2 < 0.6 vision threshold -> misaligned -> regenerate image
    assert result.action is GateAction.REGENERATE_IMAGE


class _FakeSafetyClient:
    def __init__(self, response: dict[str, object]) -> None:
        self._response = response

    def complete_json(self, system_prompt: str, user_message: str) -> dict[str, object]:
        return self._response
