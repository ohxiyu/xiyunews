"""Circulating market cap from Binance's public product list; optional, never blocks alerts."""

import asyncio
import time
from typing import Any

import aiohttp

PRODUCTS = "https://www.binance.com/bapi/asset/v2/public/asset-service/product/get-products"


def compact(value: float) -> str:
    for size, unit in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if value >= size:
            return f"{value / size:.1f}{unit}"
    return f"{value:.0f}"


class MarketCap:
    """Symbol -> circulating supply x last price, refreshed every 10 minutes."""

    def __init__(self) -> None:
        self.caps: dict[str, float] = {}
        self.checked = 0.0

    def load(self, payload: dict[str, Any]) -> None:
        caps = {}
        for row in payload["data"]:
            try:
                cap = float(row["cs"]) * float(row["c"])
            except (KeyError, TypeError, ValueError):
                continue
            if cap > 0:
                caps[row["s"]] = cap
        if not caps:
            raise ValueError("No circulating supply data")
        self.caps, self.checked = caps, time.time()

    def get(self, symbol: str) -> float | None:
        # Stale figures are worse than none: drop them after an hour without refresh.
        return self.caps.get(symbol) if time.time() - self.checked < 3600 else None

    async def run(self) -> None:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            while True:
                try:
                    async with session.get(PRODUCTS, params={"includeEtf": "true"}) as response:
                        if response.status != 200:
                            raise ValueError("Product list unavailable")
                        self.load(await response.json(content_type=None))
                    await asyncio.sleep(600)
                except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError):
                    await asyncio.sleep(60)
