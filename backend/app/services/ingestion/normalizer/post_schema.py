from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator

Platform = Literal["instagram", "facebook", "tiktok", "youtube", "snapchat", "x"]
MediaType = Literal["image", "video", "carousel", "text_only", "story"]
Geo = Literal["KSA", "UAE", "BOTH"]


class EngagementStats(BaseModel):
    likes: int = 0
    views: int = 0
    shares: int = 0
    comments: int = 0
    saves: int = 0


class RawPost(BaseModel):
    """Canonical post shape every scraped platform response is normalized into.

    This is the Data Pool's unit of storage — see
    `app.services.ingestion.data_pool.DataPool`. It intentionally has no
    database-specific fields (no FKs, no table concerns): the pool is an
    in-memory, single-process store, not a persisted table.
    """

    post_id: UUID = Field(default_factory=uuid4)
    platform: Platform
    platform_post_id: str
    content_hash: str = ""
    text: str = ""
    language: str | None = None
    media_url: str | None = None
    media_type: MediaType | None = None
    engagement: EngagementStats = Field(default_factory=EngagementStats)
    hashtags: list[str] = Field(default_factory=list)
    audio_id: str | None = None
    geo: Geo | None = None
    author_follower_count: int | None = None
    engagement_rate: float = 0.0
    posted_at: datetime
    scraped_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source_query: str | None = None

    @model_validator(mode="after")
    def _fill_content_hash(self) -> RawPost:
        """Cross-platform dedup key: SHA-256 of text + media_url (architecture doc 2.3)."""
        if not self.content_hash:
            digest_input = f"{self.text}|{self.media_url or ''}".encode()
            self.content_hash = hashlib.sha256(digest_input).hexdigest()
        return self
