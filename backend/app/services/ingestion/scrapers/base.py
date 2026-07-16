from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.scrapecreators.com"
DEFAULT_TIMEOUT = 30.0


class ScrapeCreatorsError(Exception):
    """Base exception for all ScrapeCreators API errors."""

    def __init__(
        self, message: str, status_code: int | None = None, response_body: Any = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AuthenticationError(ScrapeCreatorsError):
    """401 — missing or invalid `x-api-key`."""


class InsufficientCreditsError(ScrapeCreatorsError):
    """402 — account has run out of credits."""


class ForbiddenError(ScrapeCreatorsError):
    """403 — the source platform blocked this resource."""


class NotFoundError(ScrapeCreatorsError):
    """404 — the requested resource does not exist."""


class ScrapeCreatorsServerError(ScrapeCreatorsError):
    """5xx — the ScrapeCreators API failed internally. Safe to retry."""


_STATUS_EXCEPTIONS: dict[int, type[ScrapeCreatorsError]] = {
    401: AuthenticationError,
    402: InsufficientCreditsError,
    403: ForbiddenError,
    404: NotFoundError,
}


class ScrapeCreatorsClient:
    """Synchronous HTTP client for the ScrapeCreators API (https://docs.scrapecreators.com).

    One instance is shared across all platform-specific scrapers (Instagram, TikTok,
    YouTube, ...) so authentication, retries, and error handling live in one place.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._client = httpx.Client(
            base_url=base_url,
            headers={"x-api-key": api_key},
            timeout=timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> ScrapeCreatorsClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    @retry(
        retry=retry_if_exception_type(ScrapeCreatorsServerError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Issue a GET request and return the parsed JSON body.

        `None`-valued params are dropped so callers can pass every optional
        query parameter unconditionally without hand-pruning the dict.
        """
        clean_params = {k: v for k, v in (params or {}).items() if v is not None}
        response = self._client.get(path, params=clean_params)
        return self._handle_response(response)

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        if response.status_code == 200:
            return response.json()

        try:
            body: Any = response.json()
        except ValueError:
            body = response.text

        message = (
            f"ScrapeCreators API request failed: {response.status_code} {response.request.url}"
        )
        logger.warning(message)

        exception_cls = _STATUS_EXCEPTIONS.get(response.status_code)
        if exception_cls is None:
            exception_cls = (
                ScrapeCreatorsServerError if response.status_code >= 500 else ScrapeCreatorsError
            )
        raise exception_cls(message, status_code=response.status_code, response_body=body)
