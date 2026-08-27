from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.services.ingestion.data_pool import DataPool
from app.services.ingestion.normalizer.post_schema import RawPost
from app.services.trend_engine.rule_engine.blacklist_filter import BlacklistFilter
from app.services.trend_engine.rule_engine.engine import run_rule_engine
from app.services.trend_engine.rule_engine.scoring_config import ScoringConfig

NOW = datetime.now(UTC)


def make_post(
    platform: str = "instagram",
    platform_post_id: str = "1",
    hashtags: list[str] | None = None,
    posted_at: datetime = NOW,
    text: str = "post text",
) -> RawPost:
    return RawPost.model_validate(
        {
            "platform": platform,
            "platform_post_id": platform_post_id,
            "hashtags": hashtags or [],
            "posted_at": posted_at,
            "text": text,
        }
    )


def test_candidate_with_enough_signals_and_no_blacklist_hit_passes() -> None:
    pool = DataPool()
    config = ScoringConfig(minimum_signals_to_pass=1)
    blacklist = BlacklistFilter()
    # Cross-platform signal: same content on 2 platforms is enough to pass with minimum=1.
    pool._posts = [
        make_post(platform="instagram", platform_post_id="1", hashtags=["pizza"], text="same meme"),
        make_post(platform="tiktok", platform_post_id="2", hashtags=["pizza"], text="same meme"),
    ]

    result = run_rule_engine(pool, config=config, blacklist=blacklist)

    assert result.candidates_built == 1
    assert len(result.passed) == 1
    assert result.passed[0].candidate.hashtag == "pizza"
    assert result.passed[0].velocity.cross_platform is True
    assert result.rejected_low_velocity == 0
    assert result.rejected_blacklisted == 0


def test_candidate_with_zero_signals_is_still_returned_when_ranking() -> None:
    # Ranking has no absolute pass/fail bar: even a candidate with zero
    # velocity signals firing is returned if nothing better is competing for
    # a top_n slot. This is the whole point of ranking over gating at low
    # scrape volume.
    pool = DataPool()
    pool._posts = [make_post(hashtags=["pizza"])]  # 1 post -> no signal can fire

    result = run_rule_engine(pool)

    assert result.candidates_built == 1
    assert len(result.passed) == 1
    assert result.passed[0].velocity.signals_passed == 0
    assert result.rejected_low_velocity == 0
    assert result.rejected_blacklisted == 0


def test_ranking_truncates_to_top_n_by_signals_then_engagement() -> None:
    pool = DataPool()
    # "strong": 2 platforms sharing content -> cross_platform signal fires.
    # "weak": single post, single platform -> no signal fires.
    pool._posts = [
        make_post(platform="instagram", platform_post_id="1", hashtags=["strong"], text="viral"),
        make_post(platform="tiktok", platform_post_id="2", hashtags=["strong"], text="viral"),
        make_post(platform="instagram", platform_post_id="3", hashtags=["weak"], text="meh"),
    ]

    result = run_rule_engine(pool, top_n=1)

    assert result.candidates_built == 2
    assert len(result.passed) == 1
    assert result.passed[0].candidate.hashtag == "strong"
    assert result.not_selected == 1


def test_top_n_can_be_overridden_beyond_config_default() -> None:
    pool = DataPool()
    pool._posts = [
        make_post(platform_post_id="1", hashtags=["a"]),
        make_post(platform_post_id="2", hashtags=["b"]),
    ]
    config = ScoringConfig(top_n=1)

    result = run_rule_engine(pool, config=config, top_n=2)

    assert len(result.passed) == 2


def test_candidate_passing_velocity_but_blacklisted_is_rejected() -> None:
    pool = DataPool()
    config = ScoringConfig(minimum_signals_to_pass=1)
    blacklist = BlacklistFilter()
    pool._posts = [
        make_post(
            platform="instagram",
            platform_post_id="1",
            hashtags=["pizza"],
            text="pizza hut is trending",
        ),
        make_post(
            platform="tiktok",
            platform_post_id="2",
            hashtags=["pizza"],
            text="pizza hut is trending",
        ),
    ]

    result = run_rule_engine(pool, config=config, blacklist=blacklist)

    assert len(result.passed) == 0
    assert result.rejected_blacklisted == 1
    assert result.rejected_low_velocity == 0


def test_no_candidates_when_pool_is_empty() -> None:
    pool = DataPool()

    result = run_rule_engine(pool)

    assert result.candidates_built == 0
    assert result.passed == []


def test_posts_outside_window_do_not_form_candidates() -> None:
    pool = DataPool()
    pool._posts = [make_post(hashtags=["pizza"], posted_at=NOW - timedelta(days=3))]

    result = run_rule_engine(pool, window=timedelta(hours=24))

    assert result.candidates_built == 0
