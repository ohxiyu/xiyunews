"""Protect summary visibility, notification isolation and bounded writes."""

import time

import pytest

from src.platform.market import Market
from src.platform.settings import Settings
from src.platform.store import Store


def signal(at, change=3.0, **values):
    data = dict(
        change=change,
        peak_change=change,
        threshold=2.5,
        price=103.0,
        first_hit=at,
        last_hit=at,
        hits=1,
        group="high",
        volume=200000000,
    )
    data.update(values)
    return dict(
        kind="market",
        source="binance_spot",
        source_id=str(at),
        symbol="BTCUSDT",
        title=f"BTCUSDT {change:+.2f}%",
        body="reference",
        category="price",
        published=at,
        url="",
        signal=data,
    )


@pytest.mark.asyncio
async def test_buffer_preserves_peak_and_flushes_quiet_tail(monkeypatch):
    clock = [100.0]
    monkeypatch.setattr(time, "monotonic", lambda: clock[0])
    sent = []

    async def emit(event, baseline):
        sent.append(event)

    market = Market(emit, lambda *_: None, {})
    await market.signal(signal(10000, 3))
    assert len(sent) == 1
    for i in range(50):
        await market.signal(signal(10001 + i / 100, 4 if i == 10 else 3))
    assert len(sent) == 1
    assert len(market.pending) == 1
    await market.flush("binance_spot:BTCUSDT")
    assert len(sent) == 2
    assert sent[-1]["signal"]["peak_change"] == 4
    assert sent[-1]["signal"]["hits"] == 50
    assert sent[-1]["signal"]["change"] == 3


def test_spot_only_switch_does_not_disable_announcements(monkeypatch):
    monkeypatch.setenv("FUTURES_ENABLED", "false")
    settings = Settings(telegram=False)
    assert settings.spot and not settings.futures and settings.announcements


@pytest.mark.asyncio
async def test_daily_gate_restart_reversal_boundary_and_shared_threshold(tmp_path, monkeypatch):
    now = [100000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    path = str(tmp_path / "db")
    store = Store(path)
    assert (
        await store.market_update(signal(now[0], 2.49), chat="x", notify=True) == "below_threshold"
    )
    assert await store.market_update(signal(now[0], 2.5), chat="x", notify=True) == "queued"
    notice = await store.claim(set())
    await store.finish(notice, "sent")
    now[0] += 86399
    assert await store.market_update(signal(now[0], -30), chat="x", notify=True) == "daily_limited"
    assert len(await store.listing()) == 1
    await store.close()
    store = Store(path)
    assert await store.market_update(signal(now[0], 30), chat="x", notify=True) == "daily_limited"
    other = signal(now[0])
    other["symbol"] = "ETHUSDT"
    assert await store.market_update(other, chat="x", notify=True) == "queued"
    now[0] += 1
    assert await store.market_update(signal(now[0], -3), chat="x", notify=True) == "queued"
    rows = await store.listing(activity=True)
    assert rows[0]["symbol"] == "BTCUSDT"
    assert rows[-1]["signal"]["change"] == 2.5
    await store.close()


@pytest.mark.asyncio
async def test_disabled_delivery_still_deduplicates_web_alert(tmp_path, monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 100000)
    store = Store(str(tmp_path / "db"))
    assert await store.market_update(signal(100000), chat="", notify=False) == "disabled"
    assert await store.market_update(signal(100001, -6), chat="x", notify=True) == "daily_limited"
    assert await store.claim(set()) is None
    assert len(await store.listing()) == 1
    await store.close()


@pytest.mark.asyncio
async def test_futures_history_excluded_from_live_and_announcement_independent(tmp_path):
    store = Store(str(tmp_path / "db"))
    event = signal(time.time())
    event["source"] = "binance_futures"
    await store.market_update(event, chat="", notify=False)
    assert not await store.listing(activity=True)
    assert len(await store.listing()) == 1
    announcement = dict(
        kind="announcement",
        source="okx",
        source_id="new",
        title="BTC 公告",
        symbol="BTCUSDT",
        body="中文",
        published=time.time(),
    )
    assert await store.add(announcement, chat="", notify=False)
    rows = await store.listing(activity=True)
    assert len(rows) == 1 and rows[0]["kind"] == "announcement"
    await store.close()
