from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from app.services.ingestion.normalizer.post_schema import RawPost
from app.services.trend_engine.detection.haiku_client import HaikuResponseParseError
from app.services.trend_engine.rule_engine.clustering import TrendCandidate
from app.services.trend_engine.tco_builder.visual_patterns import (
    VisualPatterns,
    analyze_from_metadata,
    analyze_from_vision,
    analyze_visual_patterns,
)

NOW = datetime.now(UTC)

VALID_LLM_JSON = {
    "dominant_format": "close-up food shot",
    "color_palette": ["red", "gold", "brown"],
    "composition_style": "centered subject, shallow depth of field",
    "text_on_image_patterns": "bold caption overlay top-center",
}


def make_post(
    platform_post_id: str = "1",
    text: str = "delicious #pizza",
    thumbnail_url: str | None = None,
    engagement_rate: float = 0.05,
    media_type: str = "image",
) -> RawPost:
    return RawPost.model_validate(
        {
            "platform": "instagram",
            "platform_post_id": platform_post_id,
            "text": text,
            "thumbnail_url": thumbnail_url,
            "media_type": media_type,
            "engagement_rate": engagement_rate,
            "posted_at": NOW,
        }
    )


def make_candidate(posts: list[RawPost] | None = None) -> TrendCandidate:
    return TrendCandidate(
        hashtag="pizza",
        hashtags={"pizza"},
        posts=posts or [make_post()],
    )


class _FakeHaikuClient:
    def __init__(self, response: dict[str, object]) -> None:
        self._response = response
        self.text_calls: list[tuple[str, str]] = []
        self.vision_calls: list[tuple[str, str, list[tuple[str, bytes]]]] = []

    def complete_json(self, system_prompt: str, user_message: str) -> dict[str, object]:
        self.text_calls.append((system_prompt, user_message))
        return self._response

    def complete_json_with_images(
        self, system_prompt: str, user_message: str, images: list[tuple[str, bytes]]
    ) -> dict[str, object]:
        self.vision_calls.append((system_prompt, user_message, images))
        return self._response


def test_metadata_analysis_returns_visual_patterns_tagged_metadata() -> None:
    client = _FakeHaikuClient(VALID_LLM_JSON)

    result = analyze_from_metadata(make_candidate(), client)  # type: ignore[arg-type]

    assert isinstance(result, VisualPatterns)
    assert result.analysis_method == "metadata"
    assert result.dominant_format == "close-up food shot"
    assert result.color_palette == ["red", "gold", "brown"]
    assert len(client.text_calls) == 1
    assert len(client.vision_calls) == 0


def test_vision_analysis_downloads_thumbnails_and_tags_vision() -> None:
    posts = [make_post(platform_post_id="1", thumbnail_url="https://cdn.example.com/a.jpg")]
    client = _FakeHaikuClient(VALID_LLM_JSON)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, content=b"\xff\xd8fakejpeg", headers={"content-type": "image/jpeg"}
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))

    result = analyze_from_vision(make_candidate(posts), client, http_client=http_client)  # type: ignore[arg-type]

    assert result.analysis_method == "vision"
    assert len(client.vision_calls) == 1
    _, _, images = client.vision_calls[0]
    assert images == [("image/jpeg", b"\xff\xd8fakejpeg")]


def test_vision_analysis_falls_back_to_metadata_when_no_thumbnails() -> None:
    posts = [make_post(platform_post_id="1", thumbnail_url=None)]
    client = _FakeHaikuClient(VALID_LLM_JSON)

    result = analyze_from_vision(make_candidate(posts), client)  # type: ignore[arg-type]

    assert result.analysis_method == "metadata"
    assert len(client.text_calls) == 1
    assert len(client.vision_calls) == 0


def test_vision_analysis_skips_failed_downloads_and_falls_back_if_all_fail() -> None:
    posts = [make_post(platform_post_id="1", thumbnail_url="https://cdn.example.com/dead.jpg")]
    client = _FakeHaikuClient(VALID_LLM_JSON)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    http_client = httpx.Client(transport=httpx.MockTransport(handler))

    result = analyze_from_vision(make_candidate(posts), client, http_client=http_client)  # type: ignore[arg-type]

    # all downloads failed -> no images -> metadata fallback
    assert result.analysis_method == "metadata"
    assert len(client.vision_calls) == 0


def test_analysis_raises_on_schema_mismatch() -> None:
    client = _FakeHaikuClient({"dominant_format": "only one field"})

    with pytest.raises(HaikuResponseParseError):
        analyze_from_metadata(make_candidate(), client)  # type: ignore[arg-type]


def test_dispatcher_routes_to_metadata() -> None:
    client = _FakeHaikuClient(VALID_LLM_JSON)

    result = analyze_visual_patterns(make_candidate(), client, method="metadata")  # type: ignore[arg-type]

    assert result.analysis_method == "metadata"


def test_top_posts_are_selected_by_engagement_for_thumbnails() -> None:
    posts = [
        make_post(
            platform_post_id="low",
            thumbnail_url="https://cdn.example.com/low.jpg",
            engagement_rate=0.01,
        ),
        make_post(
            platform_post_id="high",
            thumbnail_url="https://cdn.example.com/high.jpg",
            engagement_rate=0.9,
        ),
    ]
    client = _FakeHaikuClient(VALID_LLM_JSON)
    requested_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested_urls.append(str(request.url))
        return httpx.Response(200, content=b"img", headers={"content-type": "image/jpeg"})

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    analyze_from_vision(make_candidate(posts), client, http_client=http_client)  # type: ignore[arg-type]

    # highest-engagement post's thumbnail is fetched first
    assert requested_urls[0] == "https://cdn.example.com/high.jpg"
