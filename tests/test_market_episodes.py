"""Policy gates persist across restarts and share API/Telegram events."""

import time

import pytest

from src.platform.delivery import format_message
from src.platform.market import Market
from src.platform.settings import Settings
from src.platform.store import Store


def signal(at, change=3.0, kind="burst", breakout=False, **values):
    component = dict(
        type=kind,
        direction=1 if change > 0 else -1,
        change=change,
        threshold=2.5 if kind == "burst" else 5,
        window_seconds=180 if kind == "burst" else 21600,
        at=at,
        crossed_at=at - 3,
        breakout=breakout,
    )
    component.update(values)
    return dict(
        kind="market",
        source="binance_spot",
        source_id=str(at),
        symbol="BTCUSDT",
        title="",
        body="",
        category="price",
        published=at,
        url="",
        signal=dict(policy_version=2, components=[component], volume=200000000, group="high"),
    )


@pytest.mark.asyncio
async def test_buffer_combines_same_direction_but_isolates_reversal():
    sent = []

    async def emit(event, baseline):
        sent.append(event)

    market = Market(emit, lambda *_: None, {})
    await market.signal(signal(10000))
    await market.signal(signal(10000, 6, kind="trend", breakout=True))
    await market.signal(signal(10000, -3))
    assert not sent
    assert len(market.pending) == 2
    await market.flush("binance_spot:BTCUSDT:1")
    assert len(sent) == 1
    assert len(sent[0]["signal"]["components"]) == 2
    assert "3 分钟内上涨" in sent[0]["title"] and "新高" in sent[0]["title"]


def test_spot_only_switch_does_not_disable_announcements(monkeypatch):
    monkeypatch.setenv("FUTURES_ENABLED", "false")
    settings = Settings(telegram=False)
    assert settings.spot and not settings.futures and settings.announcements


@pytest.mark.asyncio
async def test_burst_restart_rearm_cooldown_direction_and_delivery(tmp_path, monkeypatch):
    now = [100000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    path = str(tmp_path / "db")
    store = Store(path)
    assert (
        await store.market_update(signal(now[0], 2.49), chat="x", notify=True) == "policy_limited"
    )
    assert await store.market_update(signal(now[0], 2.5), chat="x", notify=True) == "queued"
    notice = await store.claim(set())
    assert format_message(notice) == "BTC 3 分钟内上涨 2.50%"
    await store.finish(notice, "sent")
    delivered = (await store.listing())[0]
    assert delivered["notification_status"] == "sent"
    assert delivered["notification_sent"] == now[0]
    assert delivered["sent"] is None
    # Opposite direction independent, same direction cannot bypass gate after restart.
    now[0] += 1
    assert await store.market_update(signal(now[0], -3), chat="x", notify=True) == "queued"
    await store.close()
    store = Store(path)
    now[0] += 1000
    assert await store.market_update(signal(now[0]), chat="x", notify=True) == "policy_limited"
    await store.market_rearm("binance_spot", "BTCUSDT", 1)
    assert await store.market_update(signal(now[0]), chat="x", notify=True) == "queued"
    await store.market_rearm("binance_spot", "BTCUSDT", 1)
    now[0] += 899
    assert await store.market_update(signal(now[0]), chat="x", notify=True) == "policy_limited"
    now[0] += 4  # 3s confirmation after the 900s boundary
    assert await store.market_update(signal(now[0]), chat="x", notify=True) == "queued"
    await store.close()


@pytest.mark.asyncio
async def test_trend_independent_extra_breakout_once_and_six_hour_boundary(tmp_path, monkeypatch):
    now = [100000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    store = Store(str(tmp_path / "db"))
    assert await store.market_update(signal(now[0]), chat="", notify=False) == "disabled"
    assert (
        await store.market_update(signal(now[0], 6, kind="trend"), chat="", notify=False)
        == "disabled"
    )
    now[0] += 900
    assert (
        await store.market_update(
            signal(now[0], 6, kind="trend", breakout=True), chat="", notify=False
        )
        == "disabled"
    )
    now[0] += 900
    assert (
        await store.market_update(
            signal(now[0], 7, kind="trend", breakout=True), chat="", notify=False
        )
        == "policy_limited"
    )
    now[0] = 121599
    assert (
        await store.market_update(signal(now[0], 7, kind="trend"), chat="", notify=False)
        == "policy_limited"
    )
    now[0] += 1
    assert (
        await store.market_update(signal(now[0], 7, kind="trend"), chat="", notify=False)
        == "disabled"
    )
    assert await store.claim(set()) is None
    await store.close()


@pytest.mark.asyncio
async def test_combined_partial_gate_regenerates_title_and_disabled_no_backfill(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(time, "time", lambda: 100000)
    store = Store(str(tmp_path / "db"))
    await store.market_update(signal(100000), chat="", notify=False)
    event = signal(100000)
    event["signal"]["components"] += signal(100000, 6, kind="trend")["signal"]["components"]
    assert await store.market_update(event, chat="x", notify=True) == "queued"
    rows = await store.listing()
    assert len(rows) == 2
    notice = await store.claim(set())
    assert "持续走强" in notice["title"] and "分钟" not in notice["title"]
    assert len([r for r in rows if r["notification_sent"] is None]) == 2
    await store.close()


@pytest.mark.asyncio
async def test_stale_and_future_signals_rejected_and_announcements_independent(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(time, "time", lambda: 100000)
    store = Store(str(tmp_path / "db"))
    for at in (99989, 100003):
        assert await store.market_update(signal(at), chat="", notify=False) == "policy_limited"
    event = signal(100000)
    event["source"] = "binance_futures"
    assert await store.market_update(event, chat="", notify=False) == "unsupported_policy"
    await store.market_update(signal(100000), chat="", notify=False)
    announcement = dict(
        kind="announcement",
        source="okx",
        source_id="new",
        title="BTC 公告",
        symbol="BTCUSDT",
        body="中文",
        published=100000,
    )
    assert await store.add(announcement, chat="", notify=False)
    assert len(await store.listing(activity=True)) == 2
    await store.close()


@pytest.mark.asyncio
async def test_migration_preserves_recent_direction_and_expires_old_pending(tmp_path, monkeypatch):
    now = [100000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    path = str(tmp_path / "db")
    store = Store(path)
    await store.market_update(signal(now[0]), chat="x", notify=True)
    # Emulate the schema before v2; old episode records already contain direction.
    store.db.execute("DELETE FROM meta WHERE key='alert_policy_v2'")
    store.db.execute("DELETE FROM alert_policy_state")
    store.db.commit()
    await store.close()
    store = Store(path)
    assert await store.claim(set()) is None
    assert await store.market_update(signal(now[0]), chat="x", notify=True) == "policy_limited"
    assert await store.market_update(signal(now[0], -3), chat="x", notify=True) == "queued"
    # Subsequent restart does not re-run migration or expire new pending notices.
    await store.close()
    store = Store(path)
    assert (await store.claim(set()))["title"] == "BTC 3 分钟内下跌 3.00%"
    await store.close()
