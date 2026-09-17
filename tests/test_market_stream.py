"""Replay both Binance stream shapes through subscription, detectors, buffer and outbox."""

import asyncio
import json
import time
from types import SimpleNamespace

import aiohttp
import pytest

from src.platform.delivery import format_message
from src.platform.market import Market
from src.platform.store import Store


@pytest.mark.asyncio
async def test_stream_to_one_web_event_and_one_identical_telegram_title(tmp_path, monkeypatch):
    clock = [87116.0]
    monkeypatch.setattr(time, "time", lambda: clock[0])
    store = Store(str(tmp_path / "db"))

    async def emit(event, baseline):
        if event["kind"] == "market_reset":
            await store.market_rearm(event["source"], event["symbol"], event["direction"])
        else:
            await store.market_update(event, chat="private", notify=True)

    market = Market(emit, lambda *_: None, {})
    market.universe_time["spot"] = time.monotonic()
    finished = asyncio.Event()
    subscribed = []

    class Response:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def raise_for_status(self):
            pass

        async def json(self):
            return [[i * 900000, 100, 100, 100, 100, 0, (i + 1) * 900000 - 1] for i in range(96)]

    class Socket(Response):
        async def send_json(self, value):
            subscribed.extend(value["params"])

        async def __aiter__(self):
            await asyncio.sleep(0)  # REST history loads before live close.
            for t in range(87116, 87301):
                clock[0] = float(t)
                yield SimpleNamespace(
                    type=aiohttp.WSMsgType.TEXT,
                    data=json.dumps(
                        dict(
                            e="aggTrade",
                            s="ZECUSDT",
                            T=t * 1000,
                            a=t,
                            p="106" if t >= 87297 else "100",
                        )
                    ),
                )
            yield SimpleNamespace(
                type=aiohttp.WSMsgType.TEXT,
                data=json.dumps(
                    dict(
                        e="kline",
                        s="ZECUSDT",
                        E=87300000,
                        k=dict(t=86400000, T=87299999, h="106", l="106", c="106", x=True),
                    )
                ),
            )
            finished.set()
            await asyncio.Event().wait()

    class Session:
        def get(self, url, params):
            assert params["interval"] == "15m" and params["limit"] == 98
            return Response()

        def ws_connect(self, *args, **kwargs):
            return Socket()

    task = asyncio.create_task(
        market.shard(
            Session(), "spot", "https://example.invalid", ["ZECUSDT"], {"ZECUSDT": ("high", 2e8)}, 0
        )
    )
    try:
        await asyncio.wait_for(finished.wait(), 2)
        assert subscribed == ["zecusdt@aggTrade", "zecusdt@kline_15m"]
        await market.flush("binance_spot:ZECUSDT:1")
        rows = await store.listing()
        assert len(rows) == 1 and len(rows[0]["signal"]["components"]) == 2
        notice = await store.claim(set())
        assert format_message(notice) == rows[0]["title"]
        assert "分钟内上涨" in notice["title"] and "24 小时新高" in notice["title"]
        assert await store.claim(set()) is None
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        await store.close()
