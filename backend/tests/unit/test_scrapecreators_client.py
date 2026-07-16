from __future__ import annotations

import httpx
import pytest
from app.services.ingestion.scrapers.base import (
    AuthenticationError,
    ForbiddenError,
    InsufficientCreditsError,
    NotFoundError,
    ScrapeCreatorsClient,
    ScrapeCreatorsServerError,
)


def make_client(handler: httpx.MockTransport) -> ScrapeCreatorsClient:
    client = ScrapeCreatorsClient(api_key="test-key")
    client._client = httpx.Client(
        base_url="https://api.scrapecreators.com",
        headers={"x-api-key": "test-key"},
        transport=handler,
    )
    return client


def test_get_returns_json_on_200() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "test-key"
        return httpx.Response(200, json={"success": True, "posts": []})

    client = make_client(httpx.MockTransport(handler))
    result = client.get("/v1/instagram/search/hashtag", params={"hashtag": "pizza"})

    assert result == {"success": True, "posts": []}


def test_none_params_are_dropped_from_request() -> None:
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(dict(request.url.params))
        return httpx.Response(200, json={})

    client = make_client(httpx.MockTransport(handler))
    params = {"hashtag": "pizza", "cursor": None, "region": None}
    client.get("/v1/tiktok/search/hashtag", params=params)

    assert captured == {"hashtag": "pizza"}


@pytest.mark.parametrize(
    ("status_code", "expected_exception"),
    [
        (401, AuthenticationError),
        (402, InsufficientCreditsError),
        (403, ForbiddenError),
        (404, NotFoundError),
    ],
)
def test_known_status_codes_raise_specific_exceptions(
    status_code: int, expected_exception: type
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"error": "failed"})

    client = make_client(httpx.MockTransport(handler))

    with pytest.raises(expected_exception) as exc_info:
        client.get("/v1/instagram/search/hashtag", params={"hashtag": "pizza"})

    assert exc_info.value.status_code == status_code
    assert exc_info.value.response_body == {"error": "failed"}


def test_server_error_is_retried_then_raised() -> None:
    call_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(500, text="internal error")

    client = make_client(httpx.MockTransport(handler))

    with pytest.raises(ScrapeCreatorsServerError):
        client.get("/v1/instagram/search/hashtag", params={"hashtag": "pizza"})

    assert call_count == 3
