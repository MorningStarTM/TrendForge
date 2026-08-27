from __future__ import annotations

import base64
from typing import Any

import httpx
import pytest
from anthropic import APIConnectionError
from app.services.trend_engine.detection.haiku_client import (
    HaikuClient,
    HaikuClientError,
    HaikuResponseParseError,
    estimate_cost,
)


class _FakeBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _FakeUsage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _FakeResponse:
    def __init__(self, text: str, input_tokens: int = 100, output_tokens: int = 50) -> None:
        self.content = [_FakeBlock(text)]
        self.usage = _FakeUsage(input_tokens, output_tokens)


def make_client() -> HaikuClient:
    return HaikuClient(aws_access_key="test", aws_secret_key="test", aws_region="us-east-1")


def test_complete_json_returns_parsed_dict_on_valid_json() -> None:
    client = make_client()
    client._client.messages.create = lambda **kwargs: _FakeResponse('{"score": 80}')  # type: ignore[method-assign]

    result = client.complete_json("system", "user message")

    assert result == {"score": 80}


def test_complete_json_retries_once_on_malformed_json_then_succeeds() -> None:
    client = make_client()
    responses = iter([_FakeResponse("not json"), _FakeResponse('{"score": 80}')])
    client._client.messages.create = lambda **kwargs: next(responses)  # type: ignore[method-assign]

    result = client.complete_json("system", "user message")

    assert result == {"score": 80}


def test_complete_json_raises_after_exhausting_retries_on_malformed_json() -> None:
    client = make_client()
    client._client.messages.create = lambda **kwargs: _FakeResponse("still not json")  # type: ignore[method-assign]

    with pytest.raises(HaikuResponseParseError) as exc_info:
        client.complete_json("system", "user message")

    assert exc_info.value.raw_response == "still not json"


def test_complete_json_raises_when_response_is_not_a_json_object() -> None:
    client = make_client()
    client._client.messages.create = lambda **kwargs: _FakeResponse("[1, 2, 3]")  # type: ignore[method-assign]

    with pytest.raises(HaikuResponseParseError):
        client.complete_json("system", "user message")


def test_complete_json_wraps_api_errors_into_haiku_client_error() -> None:
    client = make_client()

    def _raise(**kwargs: Any) -> None:
        request = httpx.Request("POST", "https://bedrock.example.com")
        raise APIConnectionError(request=request)

    client._client.messages.create = _raise  # type: ignore[method-assign]

    with pytest.raises(HaikuClientError):
        client.complete_json("system", "user message")


def test_estimate_cost_matches_doc_example() -> None:
    # architecture doc 3.2: ~2K tokens in, ~500 tokens out -> ~$0.001
    assert estimate_cost(2000, 500) == pytest.approx(0.001)


def test_complete_json_with_images_builds_text_plus_image_blocks() -> None:
    client = HaikuClient(
        aws_access_key="test",
        aws_secret_key="test",
        aws_region="us-east-1",
        vision_model_id="vision-model",
    )
    captured: dict[str, Any] = {}

    def _create(**kwargs: Any) -> _FakeResponse:
        captured.update(kwargs)
        return _FakeResponse('{"ok": true}')

    client._client.messages.create = _create  # type: ignore[method-assign]

    result = client.complete_json_with_images(
        "system", "look at these", images=[("image/jpeg", b"\xff\xd8bytes")]
    )

    assert result == {"ok": True}
    assert captured["model"] == "vision-model"
    content = captured["messages"][0]["content"]
    assert content[0] == {"type": "text", "text": "look at these"}
    assert content[1]["type"] == "image"
    assert content[1]["source"]["media_type"] == "image/jpeg"
    # bytes are base64-encoded, not raw
    assert content[1]["source"]["data"] == base64.standard_b64encode(b"\xff\xd8bytes").decode()


def test_vision_model_id_falls_back_to_main_model_when_unset() -> None:
    client = HaikuClient(aws_access_key="t", aws_secret_key="t", model_id="main-model")
    captured: dict[str, Any] = {}

    def _create(**kwargs: Any) -> _FakeResponse:
        captured.update(kwargs)
        return _FakeResponse("{}")

    client._client.messages.create = _create  # type: ignore[method-assign]
    client.complete_json_with_images("s", "u", images=[("image/png", b"x")])

    assert captured["model"] == "main-model"
