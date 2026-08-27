from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.services.ingestion.data_pool import DataPool
from app.services.ingestion.normalizer.post_schema import RawPost


@dataclass
class TrendCandidate:
    """A cluster of posts belonging to the same trend — the unit the Rule Engine scores.

    Clustering is hashtag-keyed, then merged by post overlap: posts are
    first grouped one-candidate-per-hashtag, and any candidates that share
    at least one post (i.e. some post carries both hashtags) are merged
    into a single candidate. This approximates the architecture doc's
    "hashtag co-occurrence" clustering (doc 3.1) without a stricter
    2+-shared-hashtags rule — simple, but note it can transitively chain
    unrelated candidates together through a common generic hashtag (e.g.
    "fyp") if one ever shows up in the shared hashtag set.

    `hashtag` is the single most representative label (most posts, ties
    broken alphabetically) — kept as a plain string so existing callers
    that key off one hashtag (`score_candidate`, `is_blocked`) keep working
    unchanged. `hashtags` is the full merged set, matching the architecture
    doc's `hashtag_set` field (doc 8.4).
    """

    candidate_id: UUID = field(default_factory=uuid4)
    hashtag: str = ""
    hashtags: set[str] = field(default_factory=set)
    posts: list[RawPost] = field(default_factory=list)
    detected_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def platforms(self) -> set[str]:
        return {post.platform for post in self.posts}

    @property
    def post_ids(self) -> list[str]:
        return [str(post.post_id) for post in self.posts]

    @property
    def platform_breakdown(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for post in self.posts:
            counts[post.platform] = counts.get(post.platform, 0) + 1
        return counts

    @property
    def average_engagement_rate(self) -> float:
        """Used as a ranking tiebreaker by the Rule Engine — see `engine.py`."""
        if not self.posts:
            return 0.0
        return sum(post.engagement_rate for post in self.posts) / len(self.posts)


# Generic, high-frequency hashtags that appear on almost everything and carry
# no trend signal. If they're used as a clustering axis they chain-merge
# unrelated posts into one giant blob, so they're excluded by default. The
# search query itself should also be added (it's on every pulled post).
GENERIC_HASHTAGS: frozenset[str] = frozenset(
    {
        "fyp",
        "foryou",
        "foryoupage",
        "viral",
        "trending",
        "trend",
        "shorts",
        "short",
        "reels",
        "reel",
        "explore",
        "explorepage",
        "instagram",
        "insta",
        "tiktok",
        "youtube",
        "video",
        "viralvideo",
        "love",
        "follow",
        "like",
        "share",
        "comment",
    }
)


def build_candidates(
    pool: DataPool,
    window: timedelta = timedelta(hours=24),
    ignore_hashtags: frozenset[str] = GENERIC_HASHTAGS,
) -> list[TrendCandidate]:
    """Group the Data Pool's recent posts into trend candidates.

    Posts are first bucketed one-per-hashtag (skipping `ignore_hashtags`), then
    hashtag buckets that share any post are merged into a single candidate
    (see `TrendCandidate`). Excluding generic/query hashtags keeps unrelated
    posts from chain-merging through a hashtag everyone uses.
    """
    posts = pool.get_since(window)
    by_hashtag: dict[str, list[RawPost]] = {}
    for post in posts:
        for hashtag in post.hashtags:
            key = hashtag.lower().lstrip("#")
            if key in ignore_hashtags:
                continue
            by_hashtag.setdefault(key, []).append(post)

    return _merge_overlapping_hashtags(by_hashtag)


def _merge_overlapping_hashtags(by_hashtag: dict[str, list[RawPost]]) -> list[TrendCandidate]:
    parent: dict[str, str] = {hashtag: hashtag for hashtag in by_hashtag}

    def find(hashtag: str) -> str:
        while parent[hashtag] != hashtag:
            parent[hashtag] = parent[parent[hashtag]]
            hashtag = parent[hashtag]
        return hashtag

    def union(a: str, b: str) -> None:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a

    # Two hashtags belong to the same trend if some post carries both.
    posts_by_id: dict[UUID, RawPost] = {}
    for posts in by_hashtag.values():
        for post in posts:
            posts_by_id[post.post_id] = post

    for post in posts_by_id.values():
        tags_in_scope = [
            tag.lower().lstrip("#") for tag in post.hashtags if tag.lower().lstrip("#") in parent
        ]
        for a, b in zip(tags_in_scope, tags_in_scope[1:], strict=False):
            union(a, b)

    groups: dict[str, set[str]] = {}
    for hashtag in by_hashtag:
        groups.setdefault(find(hashtag), set()).add(hashtag)

    candidates: list[TrendCandidate] = []
    for hashtag_set in groups.values():
        merged_posts: dict[UUID, RawPost] = {}
        for hashtag in hashtag_set:
            for post in by_hashtag[hashtag]:
                merged_posts[post.post_id] = post

        primary = max(hashtag_set, key=lambda h: (len(by_hashtag[h]), h))
        candidates.append(
            TrendCandidate(hashtag=primary, hashtags=hashtag_set, posts=list(merged_posts.values()))
        )

    return candidates
