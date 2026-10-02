"""Replay a Binance aggregate-trade stream through subscription, detector, gate and outbox."""
# ruff: noqa: RUF001

import asyncio
import json
import time
from types import SimpleNamespace

import aiohttp
import pytest

from src.platform.delivery import format_message
from src.platform.market import Market
from src.platform.store import Store


def price(t):
    # Flat, then +6% (confirmed 3s later), then a further +10.4% over the alerted price.
    return "100" if t < 87297 else ("106" if t < 87305 else "117")


@pytest.mark.asyncio
async def test_stream_alerts_once_per_move_and_again_after_a_further_move(tmp_path, monkeypatch):
    clock = [87116.0]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    store = Store(str(tmp_path / "db"))
    reasons = []

    async def emit(event, baseline):
        reasons.append(await store.market_update(event, chat="private", notify=True))

    market = Market(emit, lambda *_: None, {}, store.last_alert)
    market.universe_time["spot"] = time.monotonic()
    market.ranges = {"ZECUSDT": [105.0, 95.0]}
    finished = asyncio.Event()
    subscribed = []

    class Socket:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def send_json(self, value):
            subscribed.extend(value["params"])

        async def __aiter__(self):
            for t in range(87116, 87312):
                clock[0] = float(t)
                yield SimpleNamespace(
                    type=aiohttp.WSMsgType.TEXT,
                    data=json.dumps(dict(e="aggTrade", s="ZECUSDT", T=t * 1000, a=t, p=price(t))),
                )
            finished.set()
            await asyncio.Event().wait()

    class Session:
        def ws_connect(self, *args, **kwargs):
            return Socket()

    # GONEUSDT left the universe but stays subscribed until its shard is pruned.
    task = asyncio.create_task(
        market.shard(Session(), "spot", ["ZECUSDT", "GONEUSDT"], {"ZECUSDT": ("high", 2e8)}, 0)
    )
    try:
        await asyncio.wait_for(finished.wait(), 2)
        assert subscribed == ["zecusdt@aggTrade", "goneusdt@aggTrade"]
        # Confirmed on every later trade, but only moves the gate accepts become events.
        assert reasons == ["queued", "queued"]
        rows = await store.listing()
        assert [r["title"] for r in rows] == [
            "ZEC 3 分钟内上涨 17.00%，较上次提醒再涨 10.4%，创 24 小时新高",
            "ZEC 3 分钟内上涨 6.00%，创 24 小时新高",
        ]
        assert market.ranges["ZECUSDT"] == [117.0, 95.0]
        notice = await store.claim(set())
        assert format_message(notice) == "\n".join(r["title"] for r in rows)
        assert await store.claim(set()) is None
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await store.close()
