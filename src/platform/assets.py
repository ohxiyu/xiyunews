"""Optional public market-cap cache; never blocks event ingestion."""

import asyncio
import re
import time
from typing import Any

import aiohttp


class Assets:
    def __init__(self) -> None:
        self.coins: list[dict[str, Any]] = []
        self.checked = 0.0
        self.matches: dict[str, list[dict[str, Any]]] = {}

    async def run(self) -> None:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            while True:
                try:
                    async with session.get("https://api.coinpaprika.com/v1/tickers") as response:
                        response.raise_for_status()
                        data = await response.json()
                    if isinstance(data, list) and data:
                        self.coins = data
                        self.checked = time.time()
                        self.matches.clear()
                except (aiohttp.ClientError, TimeoutError, ValueError):
                    pass  # Optional enrichment must not stop the collector.
                await asyncio.sleep(600)

    def match(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        key = str(
            (event["kind"], event.get("symbol"), event["title"], time.time() - self.checked < 1800)
        )
        if key in self.matches:
            return self.matches[key]
        market = event["kind"] == "market"
        symbol = event.get("symbol", "").removesuffix("USDT")
        title = event["title"]
        tokens = set(re.findall(r"[A-Za-z0-9]+", title))
        tokens |= {t.removesuffix("USDT") for t in tokens}
        hits = []
        for coin in self.coins:
            ticker = coin.get("symbol", "")
            name = coin.get("name", "")
            if not ticker:
                continue
            if market:
                matched = ticker == symbol
            else:
                matched = len(ticker) >= 2 and ticker in tokens
                if len(name) >= 4 and name.lower() in title.lower():
                    matched = matched or bool(
                        re.search(
                            r"(?<![A-Za-z0-9])" + re.escape(name) + r"(?![A-Za-z0-9])",
                            title,
                            re.IGNORECASE,
                        )
                    )
            if matched:
                hits.append(coin)
        result = []
        for coin in hits[:5]:
            cap = coin.get("quotes", {}).get("USD", {}).get("market_cap")
            ambiguous = sum(c.get("symbol") == coin["symbol"] for c in self.coins) > 1
            fresh = time.time() - self.checked < 1800
            result.append(
                dict(
                    symbol=coin["symbol"],
                    name=coin["name"],
                    market_cap=cap if fresh and not ambiguous and cap else None,
                    ambiguous=ambiguous,
                    checked=self.checked,
                    updated=coin.get("last_updated"),
                    provider="CoinPaprika",
                )
            )
        if market and not result:
            result.append(dict(symbol=symbol, market_cap=None, checked=self.checked))
        if len(self.matches) >= 512:
            self.matches.clear()
        self.matches[key] = result
        return result
