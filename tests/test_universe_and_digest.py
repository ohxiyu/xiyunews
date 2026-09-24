"""Universe hygiene, stable shards and the Telegram market digest."""

import time

import pytest

from src.platform.delivery import format_message
from src.platform.market import eligible, plan_shards
from src.platform.store import Store

NOW = 1_790_000_000_000


def ticker(symbol, volume, age_ms=1000):
    return dict(symbol=symbol, quoteVolume=str(volume), closeTime=NOW - age_ms)


def test_delisted_pairs_with_stale_statistics_are_excluded():
    groups = eligible(
        [
            ticker("LIVEUSDT", 800_000),
            ticker("DEADUSDT", 800_000, age_ms=15 * 86_400_000),
            ticker("BIGUSDT", 200_000_000),
            ticker("LIVEBTC", 900_000),
            dict(symbol="BROKENUSDT", quoteVolume="1e9"),
        ],
        NOW,
    )
    assert groups == {"LIVEUSDT": ("low", 800_000.0), "BIGUSDT": ("high", 200_000_000.0)}


def test_volume_hysteresis_keeps_monitored_pairs_near_cutoff():
    rows = [ticker("EDGEUSDT", 450_000), ticker("GONEUSDT", 390_000)]
    assert eligible(rows, NOW) == {}
    assert set(eligible(rows, NOW, {"EDGEUSDT", "GONEUSDT"})) == {"EDGEUSDT"}


def test_universe_change_restarts_only_affected_shard():
    universe = {f"S{i:03}USDT" for i in range(320)}
    shards, changed = plan_shards([], universe)
    assert [len(s) for s in shards] == [150, 150, 20] and changed == {0, 1, 2}
    # One pair leaves and one joins: only the shard receiving the new pair restarts.
    universe = (universe - {"S000USDT"}) | {"NEWUSDT"}
    shards, changed = plan_shards(shards, universe)
    assert changed == {2} and "NEWUSDT" in shards[2]
    assert "S000USDT" in shards[0]  # Ignored until enough removed pairs accumulate.
    shards, changed = plan_shards(shards, universe - set(shards[0][:31]))
    assert changed == {0} and len(shards[0]) == 150 - 31
    shards, changed = plan_shards(shards, universe | {f"X{i}USDT" for i in range(200)})
    assert len(shards) == 4 and changed == {0, 2, 3}


def signal(symbol, change, at, kind="burst"):
    return dict(
        kind="market",
        source="binance_spot",
        source_id=f"{symbol}{at}",
        symbol=symbol,
        title="",
        body="",
        category="price",
        published=at,
        url="",
        signal=dict(
            policy_version=2,
            volume=1e8,
            group="high",
            components=[
                dict(
                    type=kind,
                    direction=1 if change > 0 else -1,
                    change=change,
                    threshold=2.5 if kind == "burst" else 8,
                    window_seconds=180 if kind == "burst" else 86400,
                    at=at,
                    crossed_at=at - 3,
                    breakout=False,
                )
            ],
        ),
    )


@pytest.mark.asyncio
async def test_candle_close_cluster_becomes_one_market_wide_message(tmp_path, monkeypatch):
    now = [100_000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    store = Store(str(tmp_path / "db"))
    store.policy["digest"]["hold_seconds"] = 3
    for symbol, change in [
        ("TAOUSDT", -9),
        ("APEUSDT", -8.4),
        ("XLMUSDT", -8.1),
        ("HBARUSDT", -10.8),
    ]:
        assert (
            await store.market_update(
                signal(symbol, change, now[0], "trend"), chat="c", notify=True
            )
            == "queued"
        )
    assert (
        await store.market_update(signal("SAGAUSDT", 3.0, now[0]), chat="c", notify=True)
        == "queued"
    )
    assert await store.claim(set()) is None  # Held so simultaneous closes cluster.
    now[0] += 3
    notice = await store.claim(set())
    assert len(notice["members"]) == 5
    assert await store.claim(set()) is None  # Every due notice rides in this message.
    text = format_message(notice, 4)
    down, up = text.split("\n\n")
    assert down.splitlines()[0] == "<b>市场联动下跌 · 4 个币种</b>"
    assert down.splitlines()[1].startswith("HBAR ")  # Largest move first.
    assert up == "SAGA 3 分钟内上涨 3.00%"  # Below the market-wide threshold: no header.
    await store.finish(notice, "sent", message_id=7)
    rows = await store.listing(kind="market")
    assert len(rows) == 5  # The web still shows one event per symbol.
    assert {r["notification_status"] for r in rows} == {"sent"}


@pytest.mark.asyncio
async def test_digest_retry_and_single_notice_format(tmp_path, monkeypatch):
    now = [100_000.0]
    monkeypatch.setattr(time, "time", lambda: now[0])
    store = Store(str(tmp_path / "db"))
    await store.market_update(signal("ONEUSDT", -3, now[0]), chat="c", notify=True)
    await store.market_update(signal("NOMUSDT", -3.1, now[0]), chat="c", notify=True)
    notice = await store.claim(set())
    assert len(notice["members"]) == 2
    assert "市场联动" not in format_message(notice, 4)
    await store.finish(notice, "pending", delay=1, error="telegram_server_error")
    now[0] += 1
    again = await store.claim(set())
    assert {m["id"] for m in again["members"]} == {m["id"] for m in notice["members"]}
    await store.finish(again, "sent")
    now[0] += 1000
    await store.market_update(signal("ZECUSDT", 4, now[0]), chat="c", notify=True)
    single = await store.claim(set())
    assert format_message(single) == "ZEC 3 分钟内上涨 4.00%"
