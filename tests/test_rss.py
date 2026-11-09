from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from unittest.mock import MagicMock

from src.models import RSSSourceConfig
from src.scrapers.rss import RSSScraper

_FEED = """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0"><channel><title>Test</title>
  <item>
    <guid>entry-1</guid>
    <title>Item 1</title>
    <link>https://example.com/item-1</link>
    <pubDate>Fri, 24 Apr 2026 12:00:00 GMT</pubDate>
    <description>Short summary from feed.</description>
  </item>
</channel></rss>
"""
_SINCE = datetime(2026, 4, 24, 0, 0, tzinfo=timezone.utc)


def _make_feed_client(feed_text: str) -> AsyncMock:
    response = MagicMock()
    response.text = feed_text
    response.raise_for_status.return_value = None
    client = AsyncMock()
    client.get.return_value = response
    return client


def test_rss_ids_are_deterministic() -> None:
    client = _make_feed_client(_FEED)
    source = RSSSourceConfig(name="Test", url="https://example.com/feed.xml")
    scraper = RSSScraper([source], client)

    first = asyncio.run(scraper.fetch(_SINCE))[0].id
    second = asyncio.run(scraper.fetch(_SINCE))[0].id

    assert first == second
    assert first == "rss:example.com_feed.xml:5e2d5d1e58e94d76"


def test_failed_feed_is_diagnosed_not_silently_empty():
    import httpx
    client = AsyncMock()
    client.get.side_effect = httpx.ConnectError("unavailable")
    source = RSSSourceConfig(name="Test", url="https://example.com/feed.xml")
    scraper = RSSScraper([source], client)
    assert asyncio.run(scraper.fetch(_SINCE)) == []
    assert scraper.feed_results == [{"name": "Test", "items": 0, "status": "failure", "error": "ConnectError"}]


def test_rss_requests_use_browser_compatible_user_agent() -> None:
    client = _make_feed_client(_FEED)
    source = RSSSourceConfig(name="Test", url="https://example.com/feed.xml")

    asyncio.run(RSSScraper([source], client).fetch(_SINCE))

    headers = client.get.await_args.kwargs["headers"]
    assert headers["User-Agent"].startswith("Mozilla/5.0")


def _make_registry(name: str, extractor):
    registry = MagicMock()
    registry.get.side_effect = lambda n: extractor if n == name else None
    return registry


def test_content_extractor_replaces_feed_content() -> None:
    client = _make_feed_client(_FEED)
    extractor = AsyncMock()
    extractor.extract.return_value = "Full article text from extractor."

    source = RSSSourceConfig(
        name="Test", url="https://example.com/feed.xml", content_extractor="my-ext"
    )
    scraper = RSSScraper([source], client, extractors=_make_registry("my-ext", extractor))
    items = asyncio.run(scraper.fetch(_SINCE))

    assert len(items) == 1
    assert items[0].content == "Full article text from extractor."
    extractor.extract.assert_awaited_once_with("https://example.com/item-1", client)


def test_content_extractor_falls_back_on_none() -> None:
    client = _make_feed_client(_FEED)
    extractor = AsyncMock()
    extractor.extract.return_value = None  # extraction failed

    source = RSSSourceConfig(
        name="Test", url="https://example.com/feed.xml", content_extractor="my-ext"
    )
    scraper = RSSScraper([source], client, extractors=_make_registry("my-ext", extractor))
    items = asyncio.run(scraper.fetch(_SINCE))

    assert len(items) == 1
    assert items[0].content == "Short summary from feed."


def test_unknown_extractor_name_ignored() -> None:
    client = _make_feed_client(_FEED)
    source = RSSSourceConfig(
        name="Test", url="https://example.com/feed.xml", content_extractor="nonexistent"
    )
    scraper = RSSScraper([source], client, extractors=_make_registry("other", AsyncMock()))
    items = asyncio.run(scraper.fetch(_SINCE))

    assert len(items) == 1
    assert items[0].content == "Short summary from feed."


def test_same_publisher_fallback_preserves_failure_and_headline_quality():
    import httpx
    from unittest.mock import patch
    source = RSSSourceConfig(name="Test", url="https://example.com/feed.xml", fallback_google_news=True)
    primary = httpx.Response(403, request=httpx.Request("GET", str(source.url)))
    fallback_item = asyncio.run(RSSScraper([RSSSourceConfig(name="Test", url=source.url)], _make_feed_client(_FEED)).fetch(_SINCE))[0]
    fallback_item.content = "Indexed headline, not full source evidence. " * 20
    client = AsyncMock()
    client.get.return_value = primary
    with patch("src.scrapers.rss.GoogleNewsScraper") as fallback:
        fallback.return_value.fetch = AsyncMock(return_value=[fallback_item])
        scraper = RSSScraper([source], client)
        items = asyncio.run(scraper.fetch(_SINCE))
        config = fallback.call_args.args[0]
        assert config.allowed_domains == ["example.com"]
        assert config.query == "site:example.com"
    assert items[0].metadata["collection_method"] == "google_news_fallback"
    assert items[0].metadata["collection_method"] != "rss"
    assert scraper.feed_results[0]["status"] == "degraded"
    assert scraper.feed_results[0]["error"] == "HTTP 403"
    assert scraper.feed_results[0]["fallback_items"] == 1


def test_successful_original_feed_never_requests_fallback():
    from unittest.mock import patch
    source = RSSSourceConfig(name="Test", url="https://example.com/feed.xml", fallback_google_news=True)
    with patch("src.scrapers.rss.GoogleNewsScraper") as fallback:
        items = asyncio.run(RSSScraper([source], _make_feed_client(_FEED)).fetch(_SINCE))
        assert len(items) == 1
        fallback.assert_not_called()


def test_empty_fallback_does_not_claim_primary_recovered():
    import httpx
    from unittest.mock import patch
    source = RSSSourceConfig(name="Test", url="https://example.com/feed.xml", fallback_google_news=True)
    client = AsyncMock()
    client.get.return_value = httpx.Response(403, request=httpx.Request("GET", str(source.url)))
    with patch("src.scrapers.rss.GoogleNewsScraper") as fallback:
        fallback.return_value.fetch = AsyncMock(return_value=[])
        scraper = RSSScraper([source], client)
        assert asyncio.run(scraper.fetch(_SINCE)) == []
        assert scraper.feed_results[0]["status"] == "failure"


def test_html_response_is_not_a_successful_empty_feed():
    scraper = RSSScraper([RSSSourceConfig(name="Test", url="https://example.com/feed.xml")], _make_feed_client("<html>blocked</html>"))
    assert asyncio.run(scraper.fetch(_SINCE)) == []
    assert scraper.feed_results[0]["status"] == "failure"
