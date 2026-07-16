from __future__ import annotations

import httpx
from app.services.ingestion.scrapers.base import ScrapeCreatorsClient
from app.services.ingestion.scrapers.instagram import InstagramScraper
from app.services.ingestion.scrapers.tiktok import TikTokScraper
from app.services.ingestion.scrapers.youtube import YouTubeScraper


def make_client(handler: httpx.MockTransport) -> ScrapeCreatorsClient:
    client = ScrapeCreatorsClient(api_key="test-key")
    client._client = httpx.Client(
        base_url="https://api.scrapecreators.com",
        headers={"x-api-key": "test-key"},
        transport=handler,
    )
    return client


def test_instagram_search_hashtag_parses_real_response_shape() -> None:
    fixture = {
        "success": True,
        "credits_remaining": 4998,
        "hashtag": "pizza",
        "media_type": "all",
        "posts": [{"id": "1", "shortcode": "abc", "caption": "best pizza", "like_count": 100}],
        "cursor": "1",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["hashtag"] == "pizza"
        assert request.url.params["media_type"] == "all"
        return httpx.Response(200, json=fixture)

    scraper = InstagramScraper(make_client(httpx.MockTransport(handler)))
    result = scraper.search_hashtag("pizza")

    assert result.hashtag == "pizza"
    assert result.cursor == "1"
    assert result.posts[0]["caption"] == "best pizza"


def test_instagram_get_user_reels_requires_handle_or_user_id() -> None:
    transport = httpx.MockTransport(lambda r: httpx.Response(200, json={}))
    scraper = InstagramScraper(make_client(transport))

    try:
        scraper.get_user_reels()
    except ValueError as exc:
        assert "handle or user_id" in str(exc)
    else:
        raise AssertionError("expected ValueError when neither handle nor user_id is given")


def test_tiktok_search_hashtag_parses_real_response_shape() -> None:
    fixture = {
        "aweme_list": [
            {
                "aweme_id": "7277923990184742177",
                "desc": "best boys #friends #joeytribbiani",
                "statistics": {"digg_count": 2840077, "play_count": 12711728},
                "author": {"unique_id": "someuser"},
            }
        ],
        "cursor": 10,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["hashtag"] == "friends"
        return httpx.Response(200, json=fixture)

    scraper = TikTokScraper(make_client(httpx.MockTransport(handler)))
    result = scraper.search_hashtag("friends")

    assert result.cursor == 10
    assert result.aweme_list[0]["aweme_id"] == "7277923990184742177"
    assert result.aweme_list[0]["statistics"]["digg_count"] == 2840077


def test_tiktok_search_keyword_parses_search_item_list() -> None:
    fixture = {
        "search_item_list": [
            {
                "aweme_id": "7268287584244124971",
                "desc": "keyword match",
                "statistics": {"play_count": 1282645},
            }
        ],
        "cursor": 1,
    }

    transport = httpx.MockTransport(lambda r: httpx.Response(200, json=fixture))
    scraper = TikTokScraper(make_client(transport))
    result = scraper.search_keyword("musclesandnursing")

    assert result.search_item_list[0]["desc"] == "keyword match"


def test_youtube_search_parses_videos_and_shorts() -> None:
    fixture = {
        "videos": [{"id": "abc123", "title": "Pizza trend", "viewCountInt": 5000}],
        "channels": [],
        "playlists": [],
        "shorts": [{"id": "xyz789", "title": "Pizza short", "viewCountInt": 20000}],
        "shelves": [],
        "lives": [],
        "continuationToken": "next-page-token",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["query"] == "pizza trend"
        return httpx.Response(200, json=fixture)

    scraper = YouTubeScraper(make_client(httpx.MockTransport(handler)))
    result = scraper.search("pizza trend")

    assert result.videos[0]["title"] == "Pizza trend"
    assert result.shorts[0]["viewCountInt"] == 20000
    assert result.continuationToken == "next-page-token"


def test_youtube_trending_shorts_parses_response() -> None:
    fixture = {
        "success": True,
        "shorts": [{"id": "s1", "title": "Trending short", "viewCountInt": 999}],
    }

    transport = httpx.MockTransport(lambda r: httpx.Response(200, json=fixture))
    scraper = YouTubeScraper(make_client(transport))
    result = scraper.get_trending_shorts()

    assert result.success is True
    assert result.shorts[0]["id"] == "s1"
