from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

from app.services.trend_engine.rule_engine.clustering import TrendCandidate

# PLACEHOLDER SEED VALUES ONLY.
#
# Competitor names and culturally/politically/religiously sensitive keywords
# for the KSA/UAE markets (architecture doc 3.1) are business decisions, not
# engineering ones. These are just illustrative examples so the filter has
# something to check against — replace with the real, business-approved
# list before this is used against real content.
DEFAULT_COMPETITOR_BRANDS: list[str] = ["domino's", "dominos", "pizza hut", "little caesars"]
DEFAULT_SENSITIVE_KEYWORDS: list[str] = ["election", "protest"]


@dataclass
class BlacklistFilter:
    """Configurable content blacklist (architecture doc 3.1).

    Checks a candidate's combined post text + hashtag against competitor
    brand mentions and sensitive keywords, and its posts' content hashes
    against previously-rejected content. Edit the lists directly (or call
    `reject()`) to update — same in-memory, hot-editable pattern as
    `ScoringConfig`.
    """

    competitor_brands: list[str] = field(default_factory=lambda: list(DEFAULT_COMPETITOR_BRANDS))
    sensitive_keywords: list[str] = field(default_factory=lambda: list(DEFAULT_SENSITIVE_KEYWORDS))
    rejected_content_hashes: set[str] = field(default_factory=set)

    def is_blocked(self, candidate: TrendCandidate) -> tuple[bool, str | None]:
        """Returns (blocked, reason). `reason` is None when not blocked."""
        hashtags = candidate.hashtags or {candidate.hashtag}
        combined_text = " ".join(post.text.lower() for post in candidate.posts)
        combined_text += " " + " ".join(h.lower() for h in hashtags)

        for brand in self.competitor_brands:
            if brand.lower() in combined_text:
                return True, f"competitor_brand:{brand}"

        for keyword in self.sensitive_keywords:
            if keyword.lower() in combined_text:
                return True, f"sensitive_keyword:{keyword}"

        for post in candidate.posts:
            if post.content_hash in self.rejected_content_hashes:
                return True, "previously_rejected_content"

        return False, None

    def reject(self, content_hash: str) -> None:
        """Record a content_hash as rejected, so future recurrences are blocked."""
        self.rejected_content_hashes.add(content_hash)


@lru_cache
def get_blacklist_filter() -> BlacklistFilter:
    """The single shared BlacklistFilter instance for this process."""
    return BlacklistFilter()
