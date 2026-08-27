from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.generation.image_prompt.models import ImagePrompt
from app.services.generation.quality_gate.brand_compliance import check_brand_compliance
from app.services.generation.quality_gate.clip_alignment import check_image_caption_alignment
from app.services.generation.quality_gate.duplicate_check import (
    PublishedCaptionStore,
    check_duplicate_caption,
)
from app.services.generation.quality_gate.gate import run_quality_gate
from app.services.generation.quality_gate.models import GateAction, aggregate_action
from app.services.generation.quality_gate.safety_check import check_text_safety

NOW = datetime(2026, 7, 31, 12, 0, tzinfo=UTC)


class _FakeSafetyClient:
    def __init__(self, response: dict[str, object]) -> None:
        self._response = response
        self.calls = 0

    def complete_json(self, system_prompt: str, user_message: str) -> dict[str, object]:
        self.calls += 1
        return self._response


def make_image_prompt(**overrides: object) -> ImagePrompt:
    base: dict[str, object] = {
        "positive_prompt": "A hot cheese pizza close-up, warm tones, steam rising",
        "negative_prompt": "blurry, text errors",
        "aspect_ratio": "1:1",
    }
    base.update(overrides)
    return ImagePrompt.model_validate(base)


# ---- 16.1 text safety ----


def test_safe_caption_passes() -> None:
    client = _FakeSafetyClient({"safe": True, "flags": [], "reason": ""})

    result = check_text_safety("Order a hot pizza tonight!", client)  # type: ignore[arg-type]

    assert result.passed is True
    assert result.fail_action is GateAction.REJECT


def test_unsafe_caption_fails_with_reason() -> None:
    client = _FakeSafetyClient(
        {"safe": False, "flags": ["competitor"], "reason": "mentions a competitor"}
    )

    result = check_text_safety("Better than Domino's", client)  # type: ignore[arg-type]

    assert result.passed is False
    assert result.reason == "mentions a competitor"


# ---- 16.2 image-caption alignment (fake CLIP scorer) ----


def test_alignment_passes_above_threshold() -> None:
    result = check_image_caption_alignment(b"img", "a pizza", scorer=lambda img, cap: 0.31)

    assert result.passed is True
    assert result.score == 0.31


def test_alignment_fails_below_threshold_and_asks_for_regen() -> None:
    result = check_image_caption_alignment(b"img", "a pizza", scorer=lambda img, cap: 0.10)

    assert result.passed is False
    assert result.fail_action is GateAction.REGENERATE_IMAGE


# ---- 16.3 brand compliance ----


def test_halal_violation_in_image_prompt_is_reject() -> None:
    checks = check_brand_compliance(
        caption="tasty",
        image_positive_prompt="pizza topped with crispy bacon and ham",
        aspect_ratio="1:1",
    )
    halal = next(c for c in checks if c.name == "halal_compliance")

    assert halal.passed is False
    assert halal.fail_action is GateAction.REJECT


def test_clean_food_prompt_passes_halal() -> None:
    checks = check_brand_compliance(
        caption="tasty", image_positive_prompt="margherita pizza with basil", aspect_ratio="1:1"
    )
    halal = next(c for c in checks if c.name == "halal_compliance")

    assert halal.passed is True


def test_invalid_aspect_ratio_is_flagged() -> None:
    checks = check_brand_compliance(caption="tasty", aspect_ratio="3:7")
    aspect = next(c for c in checks if c.name == "aspect_ratio")

    assert aspect.passed is False
    assert aspect.fail_action is GateAction.FLAG


def test_overlong_caption_is_flagged() -> None:
    checks = check_brand_compliance(caption="x" * 5000)
    length = next(c for c in checks if c.name == "caption_length")

    assert length.passed is False


# ---- 16.4 duplicate check ----


def test_duplicate_caption_is_flagged() -> None:
    # Fake embedder: near-identical vectors -> high cosine.
    table = {
        "fresh pizza daily": [1.0, 0.0, 0.0],
        "fresh pizza every day": [0.999, 0.045, 0.0],  # ~0.999 cosine
    }
    store = PublishedCaptionStore(embedder=lambda t: table[t])
    store.add_published("fresh pizza daily", published_at=NOW)

    result = check_duplicate_caption("fresh pizza every day", store, now=NOW)

    assert result.passed is False
    assert result.fail_action is GateAction.FLAG


def test_distinct_caption_passes_duplicate_check() -> None:
    table = {
        "fresh pizza daily": [1.0, 0.0, 0.0],
        "skateboard tricks": [0.0, 1.0, 0.0],
    }
    store = PublishedCaptionStore(embedder=lambda t: table[t])
    store.add_published("fresh pizza daily", published_at=NOW)

    result = check_duplicate_caption("skateboard tricks", store, now=NOW)

    assert result.passed is True


def test_published_caption_outside_window_is_ignored() -> None:
    table = {
        "fresh pizza daily": [1.0, 0.0, 0.0],
        "fresh pizza every day": [0.999, 0.045, 0.0],
    }
    store = PublishedCaptionStore(embedder=lambda t: table[t], lookback=timedelta(days=30))
    store.add_published("fresh pizza daily", published_at=NOW - timedelta(days=31))

    result = check_duplicate_caption("fresh pizza every day", store, now=NOW)

    assert result.passed is True  # the similar one is too old to count


# ---- aggregation + orchestrator ----


def test_aggregate_action_picks_most_severe_failure() -> None:
    from app.services.generation.quality_gate.models import CheckResult

    checks = [
        CheckResult(name="a", passed=True, fail_action=GateAction.REJECT),
        CheckResult(name="b", passed=False, fail_action=GateAction.FLAG),
        CheckResult(name="c", passed=False, fail_action=GateAction.REGENERATE_IMAGE),
    ]

    assert aggregate_action(checks) == GateAction.REGENERATE_IMAGE


def test_run_quality_gate_rejects_on_safety_failure() -> None:
    client = _FakeSafetyClient({"safe": False, "flags": ["profanity"], "reason": "profanity"})

    result = run_quality_gate(
        caption="a bad caption",
        image_prompt=make_image_prompt(),
        safety_client=client,  # type: ignore[arg-type]
    )

    assert result.action is GateAction.REJECT
    assert result.passed is False


def test_run_quality_gate_passes_clean_variant() -> None:
    client = _FakeSafetyClient({"safe": True, "flags": [], "reason": ""})

    result = run_quality_gate(
        caption="Order a hot margherita tonight!",
        image_prompt=make_image_prompt(),
        safety_client=client,  # type: ignore[arg-type]
    )

    assert result.action is GateAction.PASS
    assert result.passed is True


def test_run_quality_gate_runs_clip_when_image_bytes_given() -> None:
    client = _FakeSafetyClient({"safe": True, "flags": [], "reason": ""})

    result = run_quality_gate(
        caption="a pizza",
        image_prompt=make_image_prompt(),
        image_bytes=b"fake-image",
        safety_client=client,  # type: ignore[arg-type]
        alignment_scorer=lambda img, cap: 0.05,  # below threshold -> regenerate
    )

    assert result.action is GateAction.REGENERATE_IMAGE
    assert any(c.name == "image_caption_alignment" for c in result.checks)


def test_run_quality_gate_skips_checks_without_inputs() -> None:
    # No safety client, no image bytes, no duplicate store -> only rule-based
    # compliance runs, and a clean variant passes.
    result = run_quality_gate(caption="Order now!", image_prompt=make_image_prompt())

    assert result.passed is True
    check_names = {c.name for c in result.checks}
    assert "text_safety" not in check_names
    assert "image_caption_alignment" not in check_names
    assert "halal_compliance" in check_names
