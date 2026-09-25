"""Single market alerts as a chart photo with a bilingual caption and market cap."""
# ruff: noqa: RUF001

import time

import aiohttp
import pytest

from src.platform.chart import render
from src.platform.delivery import Delivery, market_caption
from src.platform.market_cap import MarketCap, compact
from src.platform.settings import Settings
from src.platform.store import Store


def member(kind="burst", direction=1, change=4.2, window=180, breakout=False):
    return dict(
        id="n1",
        symbol="ZECUSDT",
        signal=dict(
            components=[
                dict(
                    type=kind,
                    direction=direction,
                    change=change,
                    window_seconds=window,
                    breakout=breakout,
                )
            ]
        ),
    )


def test_caption_matches_reference_format():
    assert market_caption(member(), 21.1e9) == (
        "🇨🇳 🟢 [ZECUSDT] 币安现货价格在过去 180 秒内上涨了 4.20%\n"
        "🇺🇸 🟢 [ZECUSDT] Binance spot price surged 4.20% in the past 180 seconds\n"
        "\n💰 市值\nZEC  MarketCap: 21.1B"
    )
    down = market_caption(member("trend", -1, -9.04, 86400, True))
    assert down == (
        "🇨🇳 🔴 [ZECUSDT] 币安现货持续走弱，过去 24 小时下跌了 9.04%，跌破 24 小时新低\n"
        "🇺🇸 🔴 [ZECUSDT] Binance spot kept falling, down 9.04% over the past 24 hours, "
        "breaking the 24h low"
    )
    assert (compact(812.34e6), compact(1.67e12), compact(950)) == ("812.3M", "1.7T", "950")


def test_market_cap_from_circulating_supply_and_staleness():
    caps = MarketCap()
    caps.load(
        {"data": [{"s": "ZECUSDT", "cs": "16328269", "c": "1540.37"}, {"s": "X", "cs": None}]}
    )
    assert round(caps.get("ZECUSDT") / 1e9, 2) == 25.15 and caps.get("X") is None
    caps.checked = time.time() - 4000
    assert caps.get("ZECUSDT") is None
    with pytest.raises(ValueError):
        caps.load({"data": []})


def test_chart_png():
    rows = [
        [i * 60000, 100 + i % 7, 103 + i % 7, 98 + i % 5, 101 + i % 3, 10 + i] for i in range(60)
    ]
    png = render(rows, "ZECUSDT · 1m · Binance Spot")
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and len(png) > 2000
    with pytest.raises(ValueError):
        render(rows[:3], "x")


@pytest.mark.asyncio
async def test_single_alert_photo_fallback_and_digest(tmp_path, monkeypatch):
    store = Store(str(tmp_path / "db"))
    caps = MarketCap()
    caps.load({"data": [{"s": "ZECUSDT", "cs": "10", "c": "2e9"}]})
    delivery = Delivery(Settings(telegram=False), store, caps)
    event = dict(kind="market", chat="c", members=[member()], title="t", id="n1")

    async def chart(session, m):
        return b"\x89PNG fake"

    monkeypatch.setattr(delivery, "chart", chart)
    method, args = await delivery.request(None, event)
    assert method == "sendPhoto" and isinstance(args["data"], aiohttp.FormData)

    async def broken(session, m):
        raise ValueError("Klines unavailable")

    monkeypatch.setattr(delivery, "chart", broken)
    method, args = await delivery.request(None, event)
    assert method == "sendMessage" and "MarketCap: 20.0B" in args["json"]["text"]
    two = dict(event, members=[dict(member(), title="ZEC 3 分钟内上涨 4.20%", direction=1)] * 2)
    method, args = await delivery.request(None, two)
    assert method == "sendMessage" and args["json"]["text"].startswith("ZEC 3 分钟内上涨")
    await store.close()
