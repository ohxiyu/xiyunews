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
async def test_cooldown_keeps_live_summary_and_immutable_notice(tmp_path, monkeypatch):
    now = [10000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    store = Store(str(tmp_path / "db"))
    assert await store.market_update(signal(now[0]), chat="secret", notify=True) == "queued"
    notice = await store.claim(set())
    original_title = notice["title"]
    await store.finish(notice, "sent", message_id=123)
    now[0] += 5
    assert await store.market_update(signal(now[0], 4), chat="secret", notify=True) == "cooldown"
    rows = await store.listing()
    assert len(rows) == 1 and rows[0]["signal"]["hits"] == 2
    assert rows[0]["signal"]["peak_change"] == 4
    assert rows[0]["notification_status"] == "sent"
    assert "secret" not in str(rows)
    assert (
        store.db.execute("SELECT title FROM events WHERE id=?", (notice["id"],)).fetchone()[0]
        == original_title
    )
    assert (await store.counts()) == {"archived": 1}
    await store.close()


@pytest.mark.asyncio
async def test_reversal_escalation_rate_limit_and_lower_level_suppression(tmp_path, monkeypatch):
    now = [10000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    store = Store(str(tmp_path / "db"))

    async def update(change):
        return await store.market_update(signal(now[0], change), chat="x", notify=True)

    assert await update(3) == "queued"
    await store.finish(await store.claim(set()), "sent")
    now[0] += 5
    assert await update(6) == "rate_limited"
    now[0] += 56
    assert await update(6) == "queued"
    await store.finish(await store.claim(set()), "sent")
    now[0] += 61
    assert await update(3) == "cooldown"
    assert await update(-3) == "queued"
    assert len(await store.listing()) >= 2
    await store.close()


@pytest.mark.asyncio
async def test_restart_coalesces_episode_and_preserves_unknown_guard(tmp_path, monkeypatch):
    now = [10000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    path = str(tmp_path / "db")
    store = Store(path)
    await store.market_update(signal(now[0]), chat="x", notify=True)
    await store.claim(set())
    await store.close()
    now[0] += 5
    store = Store(path)
    assert (
        await store.market_update(signal(now[0], 4), chat="x", notify=True) == "pending_or_unknown"
    )
    assert len(await store.listing()) == 1
    now[0] += 500
    assert (
        await store.market_update(signal(now[0], 4), chat="x", notify=True) == "pending_or_unknown"
    )
    assert len(await store.listing()) == 2
    await store.close()


@pytest.mark.asyncio
async def test_disabled_notifications_never_suppress_archive_or_create_cooldown(tmp_path):
    store = Store(str(tmp_path / "db"))
    await store.market_update(signal(10000), chat="", notify=False)
    await store.market_update(signal(10005, 4), chat="", notify=False)
    rows = await store.listing()
    assert len(rows) == 1 and rows[0]["signal"]["peak_change"] == 4
    assert store.db.execute("SELECT count(*) FROM cooldown").fetchone()[0] == 0
    assert await store.claim(set()) is None
    await store.close()


@pytest.mark.asyncio
async def test_live_activity_order_and_history_order(tmp_path, monkeypatch):
    now = [10000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    store = Store(str(tmp_path / "db"))
    await store.market_update(signal(10000), chat="", notify=False)
    now[0] += 1
    other = signal(10001)
    other["symbol"] = "ETHUSDT"
    other["title"] = "ETH"
    await store.market_update(other, chat="", notify=False)
    now[0] += 1
    await store.market_update(signal(10002), chat="", notify=False)
    assert (await store.listing(activity=True))[0]["symbol"] == "BTCUSDT"
    assert (await store.listing())[0]["symbol"] == "ETHUSDT"
    await store.close()


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
async def test_independent_push_threshold_and_persistent_limits(tmp_path, monkeypatch):
    now = [10000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    store = Store(str(tmp_path / "db"))
    policy = dict(chat="private", notify=True, multiplier=2, interval=600, hourly=3)
    assert await store.market_update(signal(now[0], 3), **policy) == "below_notice_threshold"
    assert len(await store.listing()) == 1
    assert await store.market_update(signal(now[0], 5), **policy) == "queued"
    notice = await store.claim(set())
    await store.finish(notice, "failed")
    now[0] += 61
    assert await store.market_update(signal(now[0], -5), **policy) == "rate_limited"
    await store.close()
    store = Store(str(tmp_path / "db"))
    now[0] += 539
    assert await store.market_update(signal(now[0], -5), **policy) == "queued"
    await store.finish(await store.claim(set()), "failed")
    now[0] += 600
    assert await store.market_update(signal(now[0], 10), **policy) == "queued"
    await store.finish(await store.claim(set()), "failed")
    now[0] += 600
    assert await store.market_update(signal(now[0], -15), **policy) == "hourly_limited"
    assert len(await store.listing()) >= 4
    await store.close()
