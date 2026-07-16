from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.services.ingestion.scrapers.base import ScrapeCreatorsClient


class TikTokHashtagSearchResult(BaseModel):
    aweme_list: list[dict[str, Any]]
    cursor: int | None = None


class TikTokKeywordSearchResult(BaseModel):
    search_item_list: list[dict[str, Any]]
    cursor: int | None = None


class TikTokProfileVideosResult(BaseModel):
    aweme_list: list[dict[str, Any]]
    max_cursor: int | None = None


class TikTokScraper:
    """TikTok endpoints used for trend ingestion, backed by the ScrapeCreators API."""

    def __init__(self, client: ScrapeCreatorsClient) -> None:
        self._client = client

    def search_hashtag(
        self,
        hashtag: str,
        region: str | None = None,
        cursor: int | None = None,
        trim: bool | None = None,
    ) -> TikTokHashtagSearchResult:
        """Search videos posted under `hashtag` (without the leading #)."""
        data = self._client.get(
            "/v1/tiktok/search/hashtag",
            params={"hashtag": hashtag, "region": region, "cursor": cursor, "trim": trim},
        )
        return TikTokHashtagSearchResult.model_validate(data)

    def search_keyword(
        self,
        query: str,
        date_posted: str | None = None,
        sort_by: str | None = None,
        region: str | None = None,
        cursor: int | None = None,
        trim: bool | None = None,
    ) -> TikTokKeywordSearchResult:
        """Search videos matching a free-text keyword or phrase."""
        data = self._client.get(
            "/v1/tiktok/search/keyword",
            params={
                "query": query,
                "date_posted": date_posted,
                "sort_by": sort_by,
                "region": region,
                "cursor": cursor,
                "trim": trim,
            },
        )
        return TikTokKeywordSearchResult.model_validate(data)

    def get_profile_videos(
        self,
        handle: str,
        user_id: str | None = None,
        sort_by: str | None = None,
        max_cursor: str | None = None,
        region: str | None = None,
        trim: bool | None = None,
    ) -> TikTokProfileVideosResult:
        """Get a creator's video feed, sortable by latest or most popular."""
        data = self._client.get(
            "/v3/tiktok/profile/videos",
            params={
                "handle": handle,
                "user_id": user_id,
                "sort_by": sort_by,
                "max_cursor": max_cursor,
                "region": region,
                "trim": trim,
            },
        )
        return TikTokProfileVideosResult.model_validate(data)
