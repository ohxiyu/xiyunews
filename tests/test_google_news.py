from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import httpx

from src.models import GoogleNewsConfig
from src.scrapers.google_news import GoogleNewsScraper


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _feed(items_xml: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0"><channel>
      <title>Google News</title>
      {items_xml}
    </channel></rss>
    """


def _item(
    title: str,
    link: str,
    pub: str = "Sat, 27 Jun 2026 12:00:00 GMT",
    source: str | None = "Publisher",
) -> str:
    source_tag = f"<source>{source}</source>" if source is not None else ""
    return f"""
      <item>
        <title>{title}</title>
        <link>{link}</link>
        <guid>{link}</guid>
        <pubDate>{pub}</pubDate>
        <description>Summary text</description>
        {source_tag}
      </item>
    """


def _mock_client(text: str) -> AsyncMock:
    response = MagicMock()
    response.text = text
    response.raise_for_status.return_value = None
    client = AsyncMock()
    client.get.return_value = response
    return client


def test_short_window_uses_when_operator() -> None:
    client = _mock_client(_feed(_item("Foo - Publisher", "https://example.com/a")))
    config = GoogleNewsConfig(enabled=True, query="ai")
    scraper = GoogleNewsScraper(config, client)

    since = _now() - timedelta(hours=24)
    asyncio.run(scraper.fetch(since))

    q = client.get.call_args.kwargs["params"]["q"]
    assert "when:" in q
    assert q.endswith("h")
    assert q.startswith("ai ")


def test_long_window_uses_after_operator() -> None:
    client = _mock_client(_feed(_item("Foo - Publisher", "https://example.com/a")))
    config = GoogleNewsConfig(enabled=True, query="ai")
    scraper = GoogleNewsScraper(config, client)

    since = _now() - timedelta(days=30)
    asyncio.run(scraper.fetch(since))

    q = client.get.call_args.kwargs["params"]["q"]
    assert "after:" in q
    assert "when:" not in q


def test_ceid_defaults_when_unset() -> None:
    client = _mock_client(_feed(_item("Foo - Publisher", "https://example.com/a")))
    config = GoogleNewsConfig(enabled=True, query="ai", language="en", country="US")
    scraper = GoogleNewsScraper(config, client)

    asyncio.run(scraper.fetch(_now() - timedelta(hours=6)))

    params = client.get.call_args.kwargs["params"]
    assert params["ceid"] == "US:en"
    assert params["hl"] == "en"
    assert params["gl"] == "US"


def test_parses_feed_into_content_items() -> None:
    items_xml = _item(
        "Headline One - Publisher",
        "https://example.com/a",
        pub="Sat, 27 Jun 2026 12:00:00 GMT",
    ) + _item(
        "Headline Two - Other",
        "https://example.com/b",
        pub="Sat, 27 Jun 2026 13:00:00 GMT",
        source="Other",
    )
    client = _mock_client(_feed(items_xml))
    config = GoogleNewsConfig(enabled=True, query="ai")
    scraper = GoogleNewsScraper(config, client)

    items = asyncio.run(scraper.fetch(_now() - timedelta(days=365)))

    assert len(items) == 2
    first = items[0]
    assert first.title == "Headline One"
    assert str(first.url) == "https://example.com/a"
    assert first.published_at == datetime(2026, 6, 27, 12, 0, 0, tzinfo=timezone.utc)
    assert first.id.startswith("google_news:article:")
    assert first.metadata["gn_query"] == "ai"
    assert first.metadata["source_name"] == "Publisher"


def test_disabled_config_returns_empty() -> None:
    client = _mock_client(_feed(_item("Foo", "https://example.com/a")))
    config = GoogleNewsConfig(enabled=False, query="ai")
    scraper = GoogleNewsScraper(config, client)

    assert asyncio.run(scraper.fetch(_now())) == []


def test_empty_query_returns_empty() -> None:
    client = _mock_client(_feed(_item("Foo", "https://example.com/a")))
    config = GoogleNewsConfig(enabled=True, query="   ")
    scraper = GoogleNewsScraper(config, client)

    assert asyncio.run(scraper.fetch(_now())) == []


def test_http_error_returns_empty() -> None:
    client = AsyncMock()
    client.get.side_effect = httpx.HTTPError("boom")
    config = GoogleNewsConfig(enabled=True, query="ai")
    scraper = GoogleNewsScraper(config, client)

    assert asyncio.run(scraper.fetch(_now())) == []


def test_empty_feed_returns_empty() -> None:
    client = _mock_client(_feed(""))
    config = GoogleNewsConfig(enabled=True, query="ai")
    scraper = GoogleNewsScraper(config, client)

    assert asyncio.run(scraper.fetch(_now())) == []


def test_entry_missing_link_or_title_is_skipped() -> None:
    items_xml = (
        _item("", "https://example.com/no-title")  # missing title
        + "<item><title>No link</title><pubDate>Sat, 27 Jun 2026 12:00:00 GMT</pubDate></item>"
        + _item("Good - Publisher", "https://example.com/good")
    )
    client = _mock_client(_feed(items_xml))
    config = GoogleNewsConfig(enabled=True, query="ai")
    scraper = GoogleNewsScraper(config, client)

    items = asyncio.run(scraper.fetch(_now() - timedelta(days=365)))

    assert len(items) == 1
    assert str(items[0].url) == "https://example.com/good"


def test_max_results_cap() -> None:
    items_xml = "".join(
        _item(f"Item {i} - Pub", f"https://example.com/{i}") for i in range(5)
    )
    client = _mock_client(_feed(items_xml))
    config = GoogleNewsConfig(enabled=True, query="ai", max_results=2)
    scraper = GoogleNewsScraper(config, client)

    items = asyncio.run(scraper.fetch(_now() - timedelta(days=365)))

    assert len(items) == 2


def test_publisher_suffix_is_only_stripped_when_it_names_the_source() -> None:
    strip = GoogleNewsScraper._strip_publisher_suffix
    assert strip("Polymarket sued - CryptoRank", "CryptoRank") == "Polymarket sued"
    assert strip("Rate cut - what it means", "CryptoRank") == "Rate cut - what it means"
    assert strip("CryptoRank", "CryptoRank") == "CryptoRank"
    assert strip("Headline", None) == "Headline"


def test_blocked_publisher_domains_are_dropped() -> None:
    items_xml = (
        '<item><title>Token launch - openPR.com</title><link>https://example.com/a</link>'
        '<guid>a</guid><pubDate>Sat, 27 Jun 2026 12:00:00 GMT</pubDate>'
        '<source url="https://www.openpr.com">openPR.com</source></item>'
        '<item><title>Exchange hack - CoinDesk</title><link>https://example.com/b</link>'
        '<guid>b</guid><pubDate>Sat, 27 Jun 2026 12:00:00 GMT</pubDate>'
        '<source url="https://www.coindesk.com">CoinDesk</source></item>'
    )
    client = _mock_client(_feed(items_xml))
    config = GoogleNewsConfig(enabled=True, query="ai", blocked_domains=["openpr.com"])
    items = asyncio.run(GoogleNewsScraper(config, client).fetch(_now() - timedelta(days=365)))
    assert [item.title for item in items] == ["Exchange hack"]
    assert items[0].metadata["publisher_url"] == "https://www.coindesk.com"


OPAQUE = (
    "https://news.google.com/rss/articles/"
    "CBMiigFBVV95cUxQb3ZYd3R4dlRRbXNnRW54YXlEbmRvdFlkQlFmcG03VVVsNm05TVRtOWZnMFZG?oc=5"
)


def _google_transport(article: str | None, *, page_status: int = 200):
    import json

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(f"{request.method} {request.url.path}")
        if request.method == "GET" and "/rss/search" in request.url.path:
            feed = _feed(_item("Headline - Publisher", OPAQUE))
            return httpx.Response(200, text=feed)
        if request.method == "GET":
            return httpx.Response(
                page_status,
                text='<c-wiz><div jscontroller="x" data-n-a-sg="SIG" data-n-a-ts="1790000000"></div></c-wiz>',
            )
        body = request.content.decode()
        assert "Fbv4je" in body and "SIG" in body and "1790000000" in body
        if article is None:
            return httpx.Response(200, text=")]}'\n\n[]")
        row = ["wrb.fr", "Fbv4je", json.dumps(["garturlres", article, 1]), None, None, None, "generic"]
        return httpx.Response(200, text=")]}'\n\n" + json.dumps([row, ["di", 42]]))

    return httpx.MockTransport(handler), calls


def _fetch_with(transport, **config):
    async def run():
        async with httpx.AsyncClient(transport=transport) as client:
            scraper = GoogleNewsScraper(GoogleNewsConfig(enabled=True, query="ai", **config), client)
            return await scraper.fetch(_now() - timedelta(days=365))

    return asyncio.run(run())


def test_opaque_links_are_resolved_to_the_publisher_article() -> None:
    transport, _ = _google_transport("https://cryptorank.io/news/feed/abc")
    [item] = _fetch_with(transport)
    assert str(item.url) == "https://cryptorank.io/news/feed/abc"
    assert item.metadata["google_news_link_resolved"] is True


def test_resolution_failure_keeps_the_original_link() -> None:
    for transport, _ in (_google_transport(None), _google_transport("x", page_status=429)):
        [item] = _fetch_with(transport)
        assert str(item.url) == OPAQUE
        assert "google_news_link_resolved" not in item.metadata


def test_resolution_can_be_disabled() -> None:
    transport, calls = _google_transport("https://cryptorank.io/news/feed/abc")
    [item] = _fetch_with(transport, resolve_links=0)
    assert str(item.url) == OPAQUE
    assert calls == ["GET /rss/search"]


def _sourced(guid: str, title: str, outlet: str, domain: str) -> str:
    return (
        f'<item><title>{title} - {outlet}</title><link>https://example.com/{guid}</link>'
        f'<guid>{guid}</guid><pubDate>Sat, 27 Jun 2026 12:00:00 GMT</pubDate>'
        f'<source url="https://www.{domain}">{outlet}</source></item>'
    )


def test_extra_queries_keep_their_own_category_and_filters() -> None:
    """Replaces GDELT: crypto news from major outlets as a second search."""
    from src.models import GoogleNewsQuery

    exchange_feed = _feed(
        _sourced("a", "Binance maintenance", "CoinDesk", "coindesk.com")
        + _sourced("shared", "Stablecoin bill", "Reuters", "reuters.com")
    )
    mainstream_feed = _feed(
        _sourced("shared", "Stablecoin bill", "Reuters", "reuters.com")
        + _sourced("b", "Bitcoin ETF flows", "Bloomberg", "bloomberg.com")
        + _sourced("c", "Crypto press release", "openPR.com", "openpr.com")
    )
    queries: list[str] = []

    async def get(url, params=None, **_):
        queries.append(params["q"])
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.text = mainstream_feed if "site:" in params["q"] else exchange_feed
        return response

    client = AsyncMock()
    client.get.side_effect = get
    config = GoogleNewsConfig(
        enabled=True,
        query="Binance",
        category="exchange-announcements",
        resolve_links=0,
        extra_queries=[
            GoogleNewsQuery(
                query="bitcoin (site:reuters.com OR site:bloomberg.com)",
                category="crypto-markets",
                allowed_domains=["reuters.com", "bloomberg.com"],
            )
        ],
    )
    items = asyncio.run(GoogleNewsScraper(config, client).fetch(_now() - timedelta(days=365)))

    assert len(queries) == 2 and "site:reuters.com" in queries[1]
    by_title = {item.title: item for item in items}
    assert set(by_title) == {"Binance maintenance", "Stablecoin bill", "Bitcoin ETF flows"}
    # The first search to return a story keeps it; no duplicates.
    assert by_title["Stablecoin bill"].metadata["category"] == "exchange-announcements"
    assert by_title["Bitcoin ETF flows"].metadata["category"] == "crypto-markets"
    assert by_title["Bitcoin ETF flows"].metadata["gn_query"].startswith("bitcoin (site:")


def test_a_failing_extra_query_does_not_drop_the_main_one() -> None:
    from src.models import GoogleNewsQuery

    async def get(url, params=None, **_):
        if "site:" in params["q"]:
            raise httpx.ConnectError("boom")
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.text = _feed(_sourced("a", "Binance maintenance", "CoinDesk", "coindesk.com"))
        return response

    client = AsyncMock()
    client.get.side_effect = get
    config = GoogleNewsConfig(
        enabled=True, query="Binance", resolve_links=0,
        extra_queries=[GoogleNewsQuery(query="bitcoin site:reuters.com")],
    )
    items = asyncio.run(GoogleNewsScraper(config, client).fetch(_now() - timedelta(days=365)))
    assert [item.title for item in items] == ["Binance maintenance"]
