from __future__ import annotations

import pytest
from app.services.bedrock import BedrockResponseParseError
from app.services.generation.image_prompt.generator import generate_image_prompts
from app.services.generation.image_prompt.models import ImagePrompt, ImagePromptRequest
from app.services.generation.image_prompt.prompt_builder import (
    build_system_prompt,
    build_user_message,
)
from app.services.generation.image_prompt.validator import validate_image_prompt


def make_request(**overrides: object) -> ImagePromptRequest:
    defaults: dict[str, object] = {
        "captions": ["Pineapple on pizza? We said what we said. 🍍🍕"],
        "dominant_format": "close-up food shot",
        "color_palette": ["red", "gold"],
        "composition_style": "centered, shallow depth of field",
        "brand_visual_context": ["Always show the pizza hot with visible steam"],
        "dos_and_donts": ["Never show competitor logos", "No alcohol in frame"],
        "platforms": ["instagram", "tiktok"],
    }
    defaults.update(overrides)
    return ImagePromptRequest.model_validate(defaults)


def valid_prompt_json(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "positive_prompt": "A hot pineapple pizza close-up, warm red and gold tones, steam rising",
        "negative_prompt": "competitor logos, alcohol, text errors, blurry",
        "aspect_ratio": "1:1",
        "style_reference": "close-up food shot",
        "text_overlay": "We said what we said",
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


def test_system_prompt_injects_brand_visual_context_and_schema() -> None:
    prompt = build_system_prompt(make_request())

    assert "Papa John's" in prompt
    assert "visible steam" in prompt  # brand visual guide from RAG
    assert '"image_prompts"' in prompt  # output schema


def test_user_message_includes_captions_visuals_and_platform_aspect_ratios() -> None:
    message = build_user_message(make_request())

    assert "We said what we said" in message
    assert "close-up food shot" in message  # dominant_format
    assert "red, gold" in message  # color palette
    assert "9:16" in message  # tiktok aspect ratio guidance
    assert "Never show competitor logos" in message  # dos-and-donts


def test_user_message_numbers_multiple_captions() -> None:
    message = build_user_message(make_request(captions=["first caption", "second caption"]))

    assert "1. first caption" in message
    assert "2. second caption" in message


# ---- validator ----


def test_valid_image_prompt_passes() -> None:
    result = validate_image_prompt(ImagePrompt.model_validate(valid_prompt_json()))

    assert result.is_valid is True
    assert result.issues == []


def test_overlong_positive_prompt_is_flagged() -> None:
    prompt = ImagePrompt.model_validate(valid_prompt_json(positive_prompt="x" * 100))

    result = validate_image_prompt(prompt, max_prompt_chars=50)

    assert any("exceeds" in issue for issue in result.issues)


def test_empty_negative_prompt_is_flagged() -> None:
    prompt = ImagePrompt.model_validate(valid_prompt_json(negative_prompt="   "))

    result = validate_image_prompt(prompt)

    assert any("negative_prompt is empty" in issue for issue in result.issues)


def test_missing_brand_color_is_flagged_when_hexes_supplied() -> None:
    prompt = ImagePrompt.model_validate(valid_prompt_json())

    result = validate_image_prompt(prompt, brand_color_hexes=["#C8102E"])

    assert any("brand color" in issue for issue in result.issues)


def test_brand_color_present_passes() -> None:
    prompt = ImagePrompt.model_validate(
        valid_prompt_json(positive_prompt="Pizza in brand red #C8102E, gold accents")
    )

    result = validate_image_prompt(prompt, brand_color_hexes=["#C8102E"])

    assert result.is_valid is True


def test_forbidden_competitor_term_is_flagged() -> None:
    prompt = ImagePrompt.model_validate(
        valid_prompt_json(positive_prompt="A pizza styled like Domino's signature box")
    )

    result = validate_image_prompt(prompt, forbidden_terms=["Domino's"])

    assert any("forbidden/competitor" in issue for issue in result.issues)


# ---- generator ----


def test_generate_image_prompts_pairs_prompts_to_captions() -> None:
    request = make_request(captions=["caption one", "caption two"])
    response = {
        "image_prompts": [
            valid_prompt_json(positive_prompt="prompt for one"),
            valid_prompt_json(positive_prompt="prompt for two"),
        ]
    }
    client = _FakeClient(response)

    result = generate_image_prompts(request, client)  # type: ignore[arg-type]

    assert len(result.prompts) == 2
    assert result.prompts[0].caption == "caption one"
    assert result.prompts[1].caption == "caption two"
    assert len(result.valid_prompts) == 2


def test_generate_image_prompts_keeps_but_flags_invalid() -> None:
    response = {"image_prompts": [valid_prompt_json(negative_prompt="")]}
    client = _FakeClient(response)

    result = generate_image_prompts(make_request(), client)  # type: ignore[arg-type]

    assert len(result.prompts) == 1
    assert len(result.valid_prompts) == 0


def test_generate_image_prompts_skips_malformed_prompt_objects() -> None:
    response = {"image_prompts": [{"positive_prompt": "missing aspect_ratio and negative"}]}
    client = _FakeClient(response)

    result = generate_image_prompts(make_request(), client)  # type: ignore[arg-type]

    assert len(result.prompts) == 0


def test_generate_image_prompts_raises_without_array() -> None:
    client = _FakeClient({"wrong_key": []})

    with pytest.raises(BedrockResponseParseError):
        generate_image_prompts(make_request(), client)  # type: ignore[arg-type]


def test_generate_image_prompts_short_circuits_on_no_captions() -> None:
    client = _FakeClient({"image_prompts": []})

    result = generate_image_prompts(make_request(captions=[]), client)  # type: ignore[arg-type]

    assert result.prompts == []
    assert client.calls == []  # no LLM call when there's nothing to illustrate
