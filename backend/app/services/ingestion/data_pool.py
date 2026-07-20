from __future__ import annotations

import asyncio
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from app.services.ingestion.normalizer.post_schema import RawPost


class DataPool:
    """In-memory, single-process store for raw scraped posts.

    Deliberately not persisted to a database: TrendForge runs as one process
    (no separate Celery workers), so there is no cross-process state to
    share, and this data is temporary by design — it exists only to score
    trend candidates. Once a trend is selected (or a scrape cycle's
    candidates are all rejected), call `clear()` rather than waiting on a
    retention policy.
    """

    def __init__(self) -> None:
        self._posts: list[RawPost] = []
        self._seen_content_hashes: set[str] = set()
        self._seen_platform_ids: set[tuple[str, str]] = set()
        self._lock = asyncio.Lock()

    async def add(self, post: RawPost) -> bool:
        """Add a post unless it's a duplicate. Returns False if it was dropped."""
        platform_key = (post.platform, post.platform_post_id)
        async with self._lock:
            is_duplicate = (
                post.content_hash in self._seen_content_hashes
                or platform_key in self._seen_platform_ids
            )
            if is_duplicate:
                return False
            self._posts.append(post)
            self._seen_content_hashes.add(post.content_hash)
            self._seen_platform_ids.add(platform_key)
            return True

    async def add_many(self, posts: Iterable[RawPost]) -> int:
        """Add several posts, skipping duplicates. Returns the number actually added."""
        added = 0
        for post in posts:
            if await self.add(post):
                added += 1
        return added

    def _snapshot(self) -> list[RawPost]:
        """A shallow copy, so readers never iterate a list being mutated concurrently."""
        return list(self._posts)

    def all_posts(self) -> list[RawPost]:
        """Every post currently in the pool (a snapshot copy). Mainly for inspection/logging."""
        return self._snapshot()

    def get_since(self, window: timedelta, platform: str | None = None) -> list[RawPost]:
        cutoff = datetime.now(UTC) - window
        return [
            post
            for post in self._snapshot()
            if post.posted_at >= cutoff and (platform is None or post.platform == platform)
        ]

    def get_by_hashtag(self, hashtag: str, window: timedelta | None = None) -> list[RawPost]:
        target = hashtag.lower().lstrip("#")
        posts = self.get_since(window) if window is not None else self._snapshot()
        return [post for post in posts if target in (h.lower().lstrip("#") for h in post.hashtags)]

    def count_in_window(self, hashtag: str, window: timedelta) -> int:
        return len(self.get_by_hashtag(hashtag, window))

    def velocity_ratio(self, hashtag: str, window: timedelta) -> float:
        """(posts in the most recent `window`) / (posts in the window before it).

        Mirrors the architecture doc's 6-hour spike signal (ratio > 3.0x flags a
        spike). If there were zero posts in the prior window, there's no ratio to
        compute — the raw recent count is returned instead as a proxy signal.
        """
        now = datetime.now(UTC)
        recent_count = self.count_in_window(hashtag, window)
        prior_count = len(
            [
                post
                for post in self.get_by_hashtag(hashtag)
                if now - (2 * window) <= post.posted_at < now - window
            ]
        )
        if prior_count == 0:
            return float(recent_count)
        return recent_count / prior_count

    def cross_platform_count(self, content_hash: str) -> int:
        """Number of distinct platforms a piece of content has appeared on."""
        matches = self._snapshot()
        return len({post.platform for post in matches if post.content_hash == content_hash})

    async def clear(self) -> int:
        """Empty the pool. Returns the number of posts cleared."""
        async with self._lock:
            count = len(self._posts)
            self._posts.clear()
            self._seen_content_hashes.clear()
            self._seen_platform_ids.clear()
            return count

    @property
    def size(self) -> int:
        return len(self._posts)


@lru_cache
def get_data_pool() -> DataPool:
    """The single shared DataPool instance for this process."""
    return DataPool()
