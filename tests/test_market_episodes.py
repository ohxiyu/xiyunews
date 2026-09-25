"""The per-coin, per-direction gate persists across restarts and shares API/Telegram events."""
# ruff: noqa: RUF001

import time

import pytest

from src.platform.delivery import format_message
from src.platform.settings import Settings
from src.platform.store import Store


def signal(at, change=3.0, price=100.0, symbol="BTCUSDT", extreme=False):
    return dict(
        kind="market",
        source="binance_spot",
        source_id=str(at),
        symbol=symbol,
        title="",
        body="",
        category="price",
        published=at,
        url="",
        signal=dict(
            policy_version=3,
            move=dict(
                direction=1 if change > 0 else -1,
                change=change,
                threshold=2.0,
                window_seconds=180,
                crossed_at=at - 3,
                at=at,
                price=price,
                extreme=extreme,
            ),
            volume=200000000,
            group="high",
        ),
    )


def test_spot_only_switch_does_not_disable_announcements():
    settings = Settings(telegram=False)
    assert settings.spot and settings.announcements


@pytest.mark.asyncio
async def test_once_per_hour_per_direction_survives_restart(tmp_path, monkeypatch):
    now = [100000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    path = str(tmp_path / "db")
    store = Store(path)
    assert (
        await store.market_update(signal(now[0], 1.99), chat="x", notify=True) == "invalid_signal"
    )
    assert await store.market_update(signal(now[0]), chat="x", notify=True) == "queued"
    assert store.last_alert("BTCUSDT", 1) == (now[0], 100.0)
    notice = await store.claim(set())
    assert format_message(notice) == "BTC 3 分钟内上涨 3.00%"
    await store.finish(notice, "sent")
    delivered = (await store.listing())[0]
    assert delivered["notification_status"] == "sent"
    assert delivered["notification_sent"] == now[0]
    assert delivered["signal"]["move"]["price"] == 100.0
    # The opposite direction is independent.
    now[0] += 1
    assert await store.market_update(signal(now[0], -3), chat="x", notify=True) == "queued"
    await store.close()
    store = Store(path)
    assert store.last_alert("BTCUSDT", 1) == (100000.0, 100.0)
    now[0] += 1000
    assert (
        await store.market_update(signal(now[0], 6, price=109.9), chat="x", notify=True)
        == "policy_limited"
    )
    now[0] = 100000.0 + 3599
    assert await store.market_update(signal(now[0]), chat="x", notify=True) == "policy_limited"
    now[0] += 1
    assert await store.market_update(signal(now[0]), chat="x", notify=True) == "queued"
    await store.close()


@pytest.mark.asyncio
async def test_further_ten_percent_alerts_again_within_the_hour(tmp_path, monkeypatch):
    now = [100000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    store = Store(str(tmp_path / "db"))
    assert await store.market_update(signal(now[0], 5), chat="x", notify=True) == "queued"
    now[0] += 600
    assert (
        await store.market_update(signal(now[0], 4, price=109), chat="x", notify=True)
        == "policy_limited"
    )
    assert (
        await store.market_update(signal(now[0], 6, price=112, extreme=True), chat="x", notify=True)
        == "queued"
    )
    # The next further move is measured from the latest alert price.
    now[0] += 60
    assert (
        await store.market_update(signal(now[0], 3, price=121), chat="x", notify=True)
        == "policy_limited"
    )
    assert (
        await store.market_update(signal(now[0], 3, price=123.2), chat="x", notify=True) == "queued"
    )
    assert [r["title"] for r in await store.listing(kind="market")] == [
        "BTC 3 分钟内上涨 3.00%，较上次提醒再涨 10.0%",
        "BTC 3 分钟内上涨 6.00%，较上次提醒再涨 12.0%，创 24 小时新高",
        "BTC 3 分钟内上涨 5.00%",
    ]
    await store.close()


@pytest.mark.asyncio
async def test_invalid_and_old_policy_signals_rejected_and_disabled_records_gate(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(time, "time", lambda: 100000)
    store = Store(str(tmp_path / "db"))
    for at in (99989, 100003):
        assert await store.market_update(signal(at), chat="", notify=False) == "invalid_signal"
    event = signal(100000)
    event["source"] = "binance_futures"
    assert await store.market_update(event, chat="", notify=False) == "unsupported_policy"
    event = signal(100000)
    event["signal"]["policy_version"] = 2
    assert await store.market_update(event, chat="", notify=False) == "unsupported_policy"
    # With notifications off the gate is still recorded, and nothing is sent later.
    assert await store.market_update(signal(100000), chat="", notify=False) == "disabled"
    assert await store.market_update(signal(100000), chat="x", notify=True) == "policy_limited"
    assert await store.claim(set()) is None
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
async def test_migration_carries_recent_alerts_and_expires_old_pending(tmp_path, monkeypatch):
    now = [100000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    path = str(tmp_path / "db")
    store = Store(path)
    # Emulate a policy v2 database: episodes 30 minutes and 2 hours ago, one pending notice.
    store.db.executemany(
        "INSERT INTO market_episodes VALUES (?,?,?,?,?,?,?)",
        [
            ("a", "binance_spot", "ZECUSDT", 1, now[0] - 1800, "{}", ""),
            ("b", "binance_spot", "SOLUSDT", -1, now[0] - 7200, "{}", ""),
        ],
    )
    store.db.execute(
        "INSERT INTO events(id,kind,source,source_id,title,url,body,category,symbol,detected,"
        "updated,status,chat,due,expires) VALUES ('p','market','binance_spot','p','old','',"
        "'','price_notice','ZECUSDT',?,0,'pending','x',?,?)",
        (now[0], now[0], now[0] + 120),
    )
    store.db.execute("DELETE FROM meta WHERE key='alert_policy_v3'")
    store.db.execute("DELETE FROM market_alert_state")
    store.db.commit()
    await store.close()
    store = Store(path)
    assert store.last_alert("ZECUSDT", 1) == (now[0] - 1800, None)
    assert store.last_alert("SOLUSDT", -1) is None
    assert await store.claim(set()) is None
    # Without an old price only the end of the hour releases the carried-over direction.
    zec = signal(now[0], 50, price=1e9, symbol="ZECUSDT")
    assert await store.market_update(zec, chat="x", notify=True) == "policy_limited"
    sol = signal(now[0], -3, symbol="SOLUSDT")
    assert await store.market_update(sol, chat="x", notify=True) == "queued"
    now[0] += 1800
    zec = signal(now[0], symbol="ZECUSDT")
    assert await store.market_update(zec, chat="x", notify=True) == "queued"
    # A later restart does not run the migration again.
    await store.close()
    store = Store(path)
    assert store.last_alert("ZECUSDT", 1) == (now[0], 100.0)
    await store.close()
