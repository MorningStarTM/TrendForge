from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.services.ingestion.scrapers.base import ScrapeCreatorsClient


class YouTubeSearchResult(BaseModel):
    videos: list[dict[str, Any]] = []
    channels: list[dict[str, Any]] = []
    playlists: list[dict[str, Any]] = []
    shorts: list[dict[str, Any]] = []
    shelves: list[dict[str, Any]] = []
    lives: list[dict[str, Any]] = []
    continuationToken: str | None = None


class YouTubeTrendingShortsResult(BaseModel):
    success: bool
    shorts: list[dict[str, Any]]


class YouTubeVideoDetails(BaseModel):
    success: bool
    credits_remaining: int
    id: str
    title: str
    url: str
    channel: dict[str, Any]
    viewCountInt: int | None = None
    likeCountInt: int | None = None
    commentCountInt: int | None = None
    publishDate: str | None = None
    durationMs: int | None = None
    keywords: list[str] = []


class YouTubeScraper:
    """YouTube endpoints used for trend ingestion, backed by the ScrapeCreators API."""

    def __init__(self, client: ScrapeCreatorsClient) -> None:
        self._client = client

    def search(
        self,
        query: str,
        upload_date: str | None = None,
        sort_by: str | None = None,
        content_type: str | None = None,
        duration: str | None = None,
        region: str | None = None,
        continuation_token: str | None = None,
        include_extras: bool | None = None,
    ) -> YouTubeSearchResult:
        """Search YouTube by keyword; returns videos/shorts/channels/playlists/lives."""
        data = self._client.get(
            "/v1/youtube/search",
            params={
                "query": query,
                "uploadDate": upload_date,
                "sortBy": sort_by,
                "type": content_type,
                "duration": duration,
                "region": region,
                "continuationToken": continuation_token,
                "includeExtras": include_extras,
            },
        )
        return YouTubeSearchResult.model_validate(data)

    def get_trending_shorts(self) -> YouTubeTrendingShortsResult:
        """Get a fresh batch (~48) of currently trending YouTube Shorts."""
        data = self._client.get("/v1/youtube/shorts/trending")
        return YouTubeTrendingShortsResult.model_validate(data)

    def get_video(self, url: str, language: str | None = None) -> YouTubeVideoDetails:
        """Get full details (engagement, description, keywords, captions) for one video/short."""
        data = self._client.get(
            "/v1/youtube/video",
            params={"url": url, "language": language},
        )
        return YouTubeVideoDetails.model_validate(data)
