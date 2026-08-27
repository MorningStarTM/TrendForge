from __future__ import annotations

import pytest
from app.services.bedrock import BedrockResponseParseError
from app.services.generation.caption.generator import generate_captions
from app.services.generation.caption.models import CaptionRequest, CaptionVariant
from app.services.generation.caption.prompt_builder import build_system_prompt, build_user_message
from app.services.generation.caption.validator import validate_variant


def make_request(**overrides: object) -> CaptionRequest:
    defaults: dict[str, object] = {
        "trend_summary": "Pineapple pizza debate goes viral",
        "brand_angle": "Papa John's owns the debate with confidence",
        "category": "meme_format",
        "source_post_texts": ["team pineapple forever", "pineapple ruins pizza"],
        "trending_hashtags": ["pineapplepizza", "fyp"],
        "market": "UAE",
        "brand_context": ["Voice: bold and playful, never mean-spirited"],
        "num_variants": 3,
    }
    defaults.update(overrides)
    return CaptionRequest.model_validate(defaults)


def valid_variant_json(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "caption": "Pineapple on pizza? We said what we said. 🍍🍕",
        "hashtags": ["pineapplepizza", "fyp", "papajohns", "pizzalovers", "uae", "foodie"],
        "cta": "Order now",
        "language": "en",
        "market": "UAE",
        "tone": "playful",
    }
    base.update(overrides)
    return base


class _FakeClient:
    def __init__(self, response: dict[str, object]) -> None:
        self._response = response
        self.calls: list[tuple[str, str]] = []

    def complete_json(self, system_prompt: str, user_message: str) -> dict[str, object]:
        self.calls.append((system_prompt, user_message))
        return self._response


# ---- prompt builder ----


def test_system_prompt_injects_brand_context_and_schema() -> None:
    prompt = build_system_prompt(make_request())

    assert "Papa John's" in prompt
    assert "bold and playful" in prompt  # brand voice from RAG
    assert '"variants"' in prompt  # output schema


def test_user_message_includes_briefing_signals_and_reference_posts() -> None:
    message = build_user_message(make_request())

    assert "Pineapple pizza debate goes viral" in message
    assert "pineapplepizza" in message
    assert "team pineapple forever" in message
    assert "3 distinct caption variants" in message


def test_user_message_adds_refinement_feedback_when_present() -> None:
    request = make_request(refinement_notes=["too generic", "wrong tone"])

    message = build_user_message(request)

    assert "previous version was rejected" in message.lower()
    assert "too generic" in message
    assert "wrong tone" in message


def test_user_message_has_no_refinement_section_without_notes() -> None:
    assert "rejected" not in build_user_message(make_request()).lower()


# ---- validator ----


def test_valid_variant_passes() -> None:
    result = validate_variant(CaptionVariant.model_validate(valid_variant_json()))

    assert result.is_valid is True
    assert result.issues == []


def test_too_few_hashtags_is_flagged() -> None:
    variant = CaptionVariant.model_validate(valid_variant_json(hashtags=["one", "two"]))

    result = validate_variant(variant)

    assert result.is_valid is False
    assert any("too few hashtags" in issue for issue in result.issues)


def test_missing_cta_is_flagged() -> None:
    variant = CaptionVariant.model_validate(valid_variant_json(cta="  "))

    result = validate_variant(variant)

    assert any("CTA" in issue for issue in result.issues)


def test_ksa_english_only_caption_is_flagged() -> None:
    variant = CaptionVariant.model_validate(valid_variant_json(market="KSA", language="en"))

    result = validate_variant(variant)

    assert any("KSA" in issue for issue in result.issues)


def test_overlong_caption_is_flagged() -> None:
    variant = CaptionVariant.model_validate(valid_variant_json(caption="x" * 50))

    result = validate_variant(variant, max_caption_chars=10)

    assert any("exceeds" in issue for issue in result.issues)


# ---- generator ----


def test_generate_captions_parses_and_validates_variants() -> None:
    response = {"variants": [valid_variant_json(), valid_variant_json(caption="Second take 🍕")]}
    client = _FakeClient(response)

    result = generate_captions(make_request(), client)  # type: ignore[arg-type]

    assert len(result.variants) == 2
    assert len(result.valid_variants) == 2
    assert client.calls  # the client was actually called


def test_generate_captions_keeps_but_flags_invalid_variants() -> None:
    response = {
        "variants": [
            valid_variant_json(),
            valid_variant_json(hashtags=["only", "two"]),  # too few -> invalid
        ]
    }
    client = _FakeClient(response)

    result = generate_captions(make_request(), client)  # type: ignore[arg-type]

    assert len(result.variants) == 2  # kept
    assert len(result.valid_variants) == 1  # only one valid


def test_generate_captions_skips_malformed_variant_objects() -> None:
    response = {"variants": [valid_variant_json(), {"caption": "missing required fields"}]}
    client = _FakeClient(response)

    result = generate_captions(make_request(), client)  # type: ignore[arg-type]

    assert len(result.variants) == 1


def test_generate_captions_raises_without_variants_array() -> None:
    client = _FakeClient({"not_variants": []})

    with pytest.raises(BedrockResponseParseError):
        generate_captions(make_request(), client)  # type: ignore[arg-type]
