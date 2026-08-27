from __future__ import annotations

from datetime import UTC, datetime

from app.services.ingestion.normalizer.post_schema import RawPost
from app.services.trend_engine.rule_engine.blacklist_filter import BlacklistFilter
from app.services.trend_engine.rule_engine.clustering import TrendCandidate

NOW = datetime.now(UTC)


def make_post(text: str, content_hash: str = "") -> RawPost:
    return RawPost.model_validate(
        {
            "platform": "instagram",
            "platform_post_id": "1",
            "text": text,
            "posted_at": NOW,
            "content_hash": content_hash,
        }
    )


def test_candidate_mentioning_a_competitor_brand_is_blocked() -> None:
    blacklist = BlacklistFilter()
    candidate = TrendCandidate(hashtag="pizza", posts=[make_post("check out pizza hut's new deal")])

    blocked, reason = blacklist.is_blocked(candidate)

    assert blocked is True
    assert reason is not None
    assert "competitor_brand" in reason


def test_candidate_mentioning_a_sensitive_keyword_is_blocked() -> None:
    blacklist = BlacklistFilter()
    post = make_post("this pizza is tied to the election")
    candidate = TrendCandidate(hashtag="pizza", posts=[post])

    blocked, reason = blacklist.is_blocked(candidate)

    assert blocked is True
    assert reason is not None
    assert "sensitive_keyword" in reason


def test_previously_rejected_content_hash_is_blocked() -> None:
    blacklist = BlacklistFilter()
    blacklist.reject("abc123")
    candidate = TrendCandidate(
        hashtag="pizza", posts=[make_post("totally normal pizza post", content_hash="abc123")]
    )

    blocked, reason = blacklist.is_blocked(candidate)

    assert blocked is True
    assert reason == "previously_rejected_content"


def test_clean_candidate_is_not_blocked() -> None:
    blacklist = BlacklistFilter()
    post = make_post("best pizza in town, come try it")
    candidate = TrendCandidate(hashtag="pizza", posts=[post])

    blocked, reason = blacklist.is_blocked(candidate)

    assert blocked is False
    assert reason is None


def test_hashtag_itself_is_checked_against_the_blacklist() -> None:
    blacklist = BlacklistFilter(sensitive_keywords=["protest"])
    candidate = TrendCandidate(hashtag="protest", posts=[make_post("normal looking text")])

    blocked, reason = blacklist.is_blocked(candidate)

    assert blocked is True
