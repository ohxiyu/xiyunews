import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
from bs4 import BeautifulSoup

from src.models import TelegramChannelConfig, TelegramConfig
from src.scrapers.telegram import TelegramScraper


def _scraper() -> TelegramScraper:
    return TelegramScraper(TelegramConfig(), AsyncMock())


def test_parse_message_ignores_reply_preview_text() -> None:
    html = """
    <div class="tgme_widget_message" data-post="zaihuapd/42385">
      <div class="tgme_widget_message_bubble">
        <a class="tgme_widget_message_reply" href="https://t.me/zaihuapd/41026">
          <div class="tgme_widget_message_text js-message_reply_text" dir="auto">
            腾讯混元 Hy3 preview 模型发布并开源
          </div>
        </a>
        <div class="tgme_widget_message_text js-message_text" dir="auto">
          <b>腾讯混元 Hy3 正式发布：幻觉率减半，任务解决率升至 90%</b><br/>
          <br/>
          腾讯混元今日正式发布 Hy3 模型。<br/>
          <br/>
          <a href="https://huggingface.co/tencent/Hunyuan-Hy3">Huggingface</a>
        </div>
        <a class="tgme_widget_message_date" href="https://t.me/zaihuapd/42385">
          <time datetime="2026-07-06T10:09:00+00:00">10:09</time>
        </a>
      </div>
    </div>
    """
    msg = BeautifulSoup(html, "html.parser").select_one("div.tgme_widget_message")

    item = _scraper()._parse_message(
        msg,
        TelegramChannelConfig(channel="zaihuapd"),
        datetime(2026, 7, 6, 0, 0, tzinfo=timezone.utc),
    )

    assert item is not None
    assert item.title == "腾讯混元 Hy3 正式发布：幻觉率减半，任务解决率升至 90%"
    assert item.content is not None
    assert "preview 模型发布" not in item.content
    assert "正式发布 Hy3 模型" in item.content
    assert str(item.url) == "https://huggingface.co/tencent/Hunyuan-Hy3"


def test_parse_channel_html_keeps_supported_messages() -> None:
    html = """
    <div class="tgme_widget_message" data-post="channel/1">
      <div class="tgme_widget_message_text js-message_text">Hello<br/>world</div>
      <time datetime="2026-07-06T10:00:00+00:00">10:00</time>
    </div>
    """
    cfg = TelegramChannelConfig(channel="channel", fetch_limit=10)

    items = _scraper()._parse_channel_html(
        html,
        cfg,
        datetime(2026, 7, 6, 0, 0, tzinfo=timezone.utc),
    )

    assert len(items) == 1
    assert items[0].title == "Hello world"


def test_fetch_channel_uses_alternate_domain_after_dns_failure() -> None:
    requested_hosts = []
    html = """
    <div class="tgme_widget_message" data-post="channel/1">
      <div class="tgme_widget_message_text js-message_text">Hello</div>
      <time datetime="2026-07-06T10:00:00+00:00">10:00</time>
    </div>
    """

    async def handler(request: httpx.Request) -> httpx.Response:
        requested_hosts.append(request.url.host)
        if request.url.host == "telegram.me":
            raise httpx.ConnectError("Name or service not known", request=request)
        return httpx.Response(200, text=html, request=request)

    async def fetch_items():  # type: ignore[no-untyped-def]
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            scraper = TelegramScraper(
                TelegramConfig(channels=[TelegramChannelConfig(channel="channel")]),
                client,
            )
            return await scraper.fetch(datetime(2026, 7, 6, 0, 0, tzinfo=timezone.utc))

    items = asyncio.run(fetch_items())

    assert requested_hosts == ["telegram.me", "telegram.dog"]
    assert len(items) == 1


def test_fetch_raises_when_all_telegram_endpoints_fail() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Name or service not known", request=request)

    async def fetch_items():  # type: ignore[no-untyped-def]
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            scraper = TelegramScraper(
                TelegramConfig(channels=[TelegramChannelConfig(channel="channel")]),
                client,
            )
            return await scraper.fetch(datetime(2026, 7, 6, 0, 0, tzinfo=timezone.utc))

    try:
        asyncio.run(fetch_items())
    except RuntimeError as exc:
        assert "All Telegram channels failed" in str(exc)
    else:
        raise AssertionError("Expected all Telegram endpoint failures to propagate")


_PROBE_PAGE = """
<div class="tgme_channel_info_header_title"><span>Whale Alert</span></div>
<div class="tgme_channel_info_counter"><span class="counter_value">120K</span>
<span class="counter_type">subscribers</span></div>
<div class="tgme_widget_message" data-post="whale_alert_io/9">
  <time datetime="2026-09-28T01:00:00+00:00"></time>
  <div class="tgme_widget_message_text js-message_text">1,000 BTC moved</div>
</div>
<div class="tgme_widget_message" data-post="whale_alert_io/8">
  <time datetime="2026-09-20T01:00:00+00:00"></time>
  <div class="tgme_widget_message_text js-message_text">old</div>
</div>
<div class="tgme_widget_message" data-post="whale_alert_io/10">
  <time datetime="2026-09-28T02:00:00+00:00"></time>
</div>
"""


def _page_client(pages: dict[str, str]):
    def handler(request):
        channel = request.url.path.rsplit("/", 1)[-1]
        if channel not in pages:
            return httpx.Response(404)
        return httpx.Response(200, text=pages[channel])

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def test_channel_report_explains_yield_and_identity() -> None:
    from datetime import datetime, timezone

    from src.models import TelegramConfig, TelegramChannelConfig
    from src.scrapers.telegram import TelegramScraper

    async def run():
        async with _page_client({"whale_alert_io": _PROBE_PAGE}) as client:
            scraper = TelegramScraper(
                TelegramConfig(channels=[TelegramChannelConfig(channel="whale_alert_io")]), client
            )
            items = await scraper.fetch(datetime(2026, 9, 27, tzinfo=timezone.utc))
            return items, scraper.channel_reports

    items, [report] = asyncio.run(run())
    assert len(items) == 1
    assert report["title"] == "Whale Alert"
    assert report["subscribers"] == "120K"
    assert (report["messages_seen"], report["in_window"], report["kept"]) == (3, 2, 1)
    assert report["newest"] == "2026-09-28T02:00:00+00:00"


def test_probe_channels_are_reported_but_never_published() -> None:
    from datetime import datetime, timezone

    from src.models import TelegramConfig, TelegramChannelConfig
    from src.scrapers.telegram import TelegramScraper

    config = TelegramConfig(channels=[
        TelegramChannelConfig(channel="whale_alert_io", probe=True),
        TelegramChannelConfig(channel="missing_probe", probe=True),
        TelegramChannelConfig(channel="live_one"),
    ])

    async def run():
        pages = {"whale_alert_io": _PROBE_PAGE, "live_one": _PROBE_PAGE.replace("whale_alert_io", "live_one")}
        async with _page_client(pages) as client:
            scraper = TelegramScraper(config, client)
            items = await scraper.fetch(datetime(2026, 9, 27, tzinfo=timezone.utc))
            return items, scraper.channel_reports

    items, reports = asyncio.run(run())
    assert {item.metadata["channel"] for item in items} == {"live_one"}
    by_channel = {row["channel"]: row for row in reports}
    assert by_channel["whale_alert_io"]["probe"] is True and by_channel["whale_alert_io"]["kept"] == 1
    assert by_channel["missing_probe"]["status"] == "failed"


def test_failed_probes_alone_do_not_fail_the_source() -> None:
    from datetime import datetime, timezone

    from src.models import TelegramConfig, TelegramChannelConfig
    from src.scrapers.telegram import TelegramScraper

    config = TelegramConfig(channels=[TelegramChannelConfig(channel="gone", probe=True)])

    async def run():
        async with _page_client({}) as client:
            return await TelegramScraper(config, client).fetch(datetime(2026, 9, 27, tzinfo=timezone.utc))

    assert asyncio.run(run()) == []
