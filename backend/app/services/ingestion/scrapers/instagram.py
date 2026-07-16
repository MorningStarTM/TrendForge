from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel

from app.services.ingestion.scrapers.base import ScrapeCreatorsClient


class InstagramHashtagSearchResult(BaseModel):
    success: bool
    credits_remaining: int
    hashtag: str
    media_type: str
    posts: list[dict[str, Any]]
    cursor: str | None = None


class InstagramUserPostsResult(BaseModel):
    items: list[dict[str, Any]]
    next_max_id: str | None = None
    num_results: int
    more_available: bool
    user: dict[str, Any]


class InstagramUserReelsResult(BaseModel):
    items: list[dict[str, Any]]
    max_id: str | None = None


class InstagramScraper:
    """Instagram endpoints used for trend ingestion, backed by the ScrapeCreators API."""

    def __init__(self, client: ScrapeCreatorsClient) -> None:
        self._client = client

    def search_hashtag(
        self,
        hashtag: str,
        media_type: Literal["all", "reels"] = "all",
        date_posted: str | None = None,
        cursor: str | None = None,
    ) -> InstagramHashtagSearchResult:
        """Search public posts/reels tagged with `hashtag` (Google-indexed, best-effort)."""
        data = self._client.get(
            "/v1/instagram/search/hashtag",
            params={
                "hashtag": hashtag,
                "media_type": media_type,
                "date_posted": date_posted,
                "cursor": cursor,
            },
        )
        return InstagramHashtagSearchResult.model_validate(data)

    def get_user_posts(
        self,
        handle: str,
        next_max_id: str | None = None,
        trim: bool | None = None,
    ) -> InstagramUserPostsResult:
        """Get a public profile's recent posts (photos, videos, carousels, reels)."""
        data = self._client.get(
            "/v2/instagram/user/posts",
            params={"handle": handle, "next_max_id": next_max_id, "trim": trim},
        )
        return InstagramUserPostsResult.model_validate(data)

    def get_user_reels(
        self,
        handle: str | None = None,
        user_id: str | None = None,
        max_id: str | None = None,
        trim: bool | None = None,
    ) -> InstagramUserReelsResult:
        """Get a public profile's reels. Prefer `user_id` over `handle` for speed."""
        if not handle and not user_id:
            raise ValueError("Either handle or user_id is required")
        data = self._client.get(
            "/v1/instagram/user/reels",
            params={"handle": handle, "user_id": user_id, "max_id": max_id, "trim": trim},
        )
        return InstagramUserReelsResult.model_validate(data)
