"""Contract, crash recovery, timing, and isolation tests for the new platform."""

import asyncio
import json
import time

import pytest
from aiohttp.test_utils import TestClient, TestServer

from src.platform.announcements import (
    Announcements,
    TelegramPreview,
    announcement,
    parse_binance,
    parse_okx,
)
from src.platform.app import Platform
from src.platform.delivery import Delivery, format_message
from src.platform.settings import Settings
from src.platform.store import Store


def event(sid="one", **changes):
    value = announcement(
        "okx", sid, "OKX to list <b>TEST</b>", "Body", "https://www.okx.com/help/test", 1
    )
    return {**value, **changes}


@pytest.mark.asyncio
async def test_baseline_revision_and_restart_dedup(tmp_path):
    path = str(tmp_path / "db")
    store = Store(path)
    assert await store.add(event(), chat="private", notify=True, baseline=True)
    assert not await store.add(event(), chat="private", notify=True)
    assert await store.claim(set()) is None
    assert await store.add(event(body="revised"), chat="private", notify=True)
    row = await store.claim(set())
    assert row["updated"] == 1
    await store.close()
    store = Store(path)
    rows = await store.listing()
    assert rows[0]["status"] == "unknown"
    assert "chat" not in rows[0]
    assert not await store.add(event(body="revised"), chat="private", notify=True)
    assert await store.claim(set()) is None
    await store.close()


@pytest.mark.asyncio
async def test_cooldown_only_after_success_and_pending_reservation(tmp_path):
    store = Store(str(tmp_path / "db"))
    options = dict(chat="test", notify=True, cooldown_key="spot_BTCUSDT_3m")
    assert await store.add(event("first", kind="market"), **options)
    assert not await store.add(event("second", kind="market"), **options)
    first = await store.claim(set())
    await store.finish(first, "failed")
    assert await store.add(event("second", kind="market"), **options)
    second = await store.claim(set())
    await store.finish(second, "sent", message_id=123)
    assert not await store.add(event("third", kind="market"), **options)
    await store.close()


@pytest.mark.asyncio
async def test_retry_does_not_block_another_chat(tmp_path):
    store = Store(str(tmp_path / "db"))
    await store.add(event("a"), chat="one", notify=True)
    first = await store.claim(set())
    await store.finish(first, "pending", delay=300)
    await store.add(event("b"), chat="two", notify=True)
    assert (await store.claim({"one"}))["chat"] == "two"
    await store.close()


@pytest.mark.asyncio
async def test_store_transaction_survives_cancellation(tmp_path):
    store = Store(str(tmp_path / "db"))
    order = []

    def slow():
        time.sleep(0.02)
        order.append("first")

    task = asyncio.create_task(store.run(slow))
    await asyncio.sleep(0.005)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    await store.run(lambda: order.append("second"))
    assert order == ["first", "second"]
    await store.close()


def test_okx_first_publication_and_binance_nested_json():
    rows = parse_okx(
        {
            "code": "0",
            "data": [
                {
                    "details": [
                        {
                            "title": "OKX to list TEST",
                            "url": "https://www.okx.com/help/test",
                            "pTime": "10000",
                            "businessPTime": "999000",
                        }
                    ]
                }
            ],
        }
    )
    assert rows[0]["published"] == 10
    assert rows[0]["category"] == "listing"
    with pytest.raises(ValueError):
        parse_okx({"code": "50011"})
    message = parse_binance(
        {
            "type": "DATA",
            "topic": "com_announcement_en",
            "data": json.dumps(
                {
                    "catalogId": 161,
                    "publishDate": 10000,
                    "title": "Delisting TEST",
                    "body": "<p>text</p>",
                }
            ),
        }
    )
    assert message["category"] == "delisting"
    assert message["body"] == "text"
    assert message["url"] == "https://www.binance.com/en/support/announcement"
    with pytest.raises(ValueError):
        announcement("okx", "a", "x", "", "https://evil.example/", 1)


def test_public_channel_parser_handles_nested_html_and_edits():
    parser = TelegramPreview()
    parser.feed("""<div data-post="hyperliquid_announcements/123">
      <div class="tgme_widget_message_text js-message_text">
      <b>New market</b><br>Details &amp; links</div>
      <a><time datetime="2026-09-14T00:00:00+00:00"></time></a></div>""")
    rows = parser.events()
    assert len(rows) == 1
    assert rows[0]["title"] == "New market"
    assert rows[0]["body"] == "New market Details & links"
    assert rows[0]["source_id"] == "hyperliquid_announcements/123"
    with pytest.raises(ValueError):
        TelegramPreview().events()


@pytest.mark.asyncio
async def test_page_baseline_only_commits_after_events(tmp_path):
    store = Store(str(tmp_path / "db"))
    seen = []

    async def emit(row, baseline):
        seen.append(baseline)
        await store.add(row, chat="test", notify=True, baseline=baseline)

    collector = Announcements(Settings(telegram=False), store, emit, lambda *_: None)
    await collector.accept_page("okx", [event()])
    await collector.accept_page("okx", [event("two")])
    assert seen == [True, False]
    assert (await store.claim(set()))["source_id"] == "two"
    await store.close()


@pytest.mark.asyncio
async def test_api_read_only_filter_and_secret_redaction(tmp_path):
    app = Platform(
        Settings(
            database=str(tmp_path / "db"),
            telegram=False,
            market=False,
            announcements=False,
        )
    )
    await app.store.add(event(), chat="secret-chat", notify=False)
    async with TestClient(TestServer(app.api())) as client:
        result = await client.get(
            "/api/events?q=TEST", headers={"Origin": "https://fomobtc.example"}
        )
        # No browser client any more: no CORS grant, no live stream endpoint.
        assert "Access-Control-Allow-Origin" not in result.headers
        assert (await client.get("/api/stream")).status == 404
        body = await result.text()
        assert "secret-chat" not in body
        assert len(json.loads(body)["events"]) == 1
        assert (await client.post("/api/events")).status == 405
        assert (await client.get("/api/events?limit=bad")).status == 400
        assert (await client.get("/api/ready")).status == 200
    await app.store.close()


class Response:
    def __init__(self, status, data):
        self.status, self.data = status, data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    async def json(self, **kwargs):
        return self.data


class Session:
    def __init__(self, response):
        self.response = response

    def post(self, *args, **kwargs):
        return self.response


@pytest.mark.asyncio
async def test_delivery_ack_and_full_retry_after(tmp_path):
    store = Store(str(tmp_path / "db"))
    await store.add(event(), chat="test", notify=True)
    claimed = await store.claim(set())
    sender = Delivery(Settings(telegram=False), store)
    await sender.send(Session(Response(429, {"parameters": {"retry_after": 120}})), claimed)
    assert sender.global_pause - time.monotonic() > 119
    assert await store.claim(set()) is None
    await sender.send(Session(Response(200, {"ok": True, "result": {"message_id": 42}})), claimed)
    assert (await store.listing())[0]["status"] == "sent"
    await store.close()


def test_message_html_escaping():
    row = {**event(), "updated": 0, "id": "12345678", "title": "<script>& "}
    text = format_message(row)
    assert "<script>" not in text
    assert "&lt;script&gt;&amp;" in text


@pytest.mark.asyncio
async def test_readiness_marks_stale_streams_and_ignores_retired_shards(tmp_path):
    platform = Platform(Settings(database=str(tmp_path / "state"), telegram=False))
    platform.status("spot_stream_0", "live", "connected")
    platform.status("spot_stream_1", "retired", "rebalanced")
    platform.sources["spot_stream_0"]["checked"] -= 100
    client = TestClient(TestServer(platform.api()))
    await client.start_server()
    try:
        response = await client.get("/api/ready")
        assert response.status == 503
        data = await response.json()
        assert data["sources"]["spot_stream_0"]["state"] == "stale"
        assert "spot_stream_1" not in data["sources"]
    finally:
        await client.close()
        await platform.store.close()
