"""Event-driven Binance prices; preserve minute-bar reference, never call it rolling 180s."""

import asyncio
import json
import math
import time
from collections import deque
from pathlib import Path
from typing import Any

import aiohttp
import yaml

from .announcements import Emit, Status


class MinuteWindow:
    def __init__(self) -> None:
        self.bars: dict[int, float] = {}
        self.last_id: int | None = None
        self.last_time = 0
        self.gap = False

    def seed(self, klines: list[list[Any]], now_ms: int) -> None:
        closed = {}
        for row in klines:
            start, close_time, price = int(row[0]), int(row[6]), float(row[4])
            if start % 60000 or close_time >= now_ms or price <= 0 or not math.isfinite(price):
                continue
            closed[start // 60000] = price
        for minute, price in closed.items():
            self.bars[minute] = price
        self.bars = dict(sorted(self.bars.items())[-5:])
        self.gap = False

    def update(self, data: dict[str, Any], now_ms: int) -> float | None:
        timestamp, trade_id, price = int(data["T"]), int(data["a"]), float(data["p"])
        if not math.isfinite(price) or price <= 0:
            return None
        if timestamp < self.last_time or (self.last_id is not None and trade_id <= self.last_id):
            return None
        if now_ms - timestamp > 10000 or timestamp - now_ms > 2000:
            self.bars.clear()
            self.gap = True
            return None
        if self.last_id is not None and trade_id != self.last_id + 1:
            self.bars.clear()
            self.gap = True
        self.last_id, self.last_time = trade_id, timestamp
        minute = timestamp // 60000
        # A continuous aggregate-trade sequence proves empty intervening minutes had no trades.
        if self.bars and not self.gap:
            previous = max(self.bars)
            previous_price = self.bars[previous]
            for empty in range(max(previous + 1, minute - 3), minute):
                self.bars[empty] = previous_price
        self.bars[minute] = price
        self.bars = {m: p for m, p in self.bars.items() if m >= minute - 4}
        if self.gap or not all(m in self.bars for m in range(minute - 3, minute + 1)):
            return None
        return (price / self.bars[minute - 3] - 1) * 100


class Market:
    def __init__(self, emit: Emit, status: Status, stats: dict[str, Any]) -> None:
        self.emit, self.status, self.stats = emit, status, stats
        data = yaml.safe_load(
            (Path(__file__).resolve().parents[2] / "config/thresholds.yaml").read_text()
        )
        self.thresholds = data["change3m_alert"]["thresholds"]
        self.refresh = data["change3m_alert"]["group_refresh_seconds"]
        self.universe_time: dict[str, float] = {}
        self.pending: dict[str, dict[str, Any]] = {}
        self.last_flush: dict[str, float] = {}
        self.last_shape: dict[str, tuple[int, int]] = {}
        self.rates: dict[str, dict[int, int]] = {}
        self.started = time.time()
        self.latencies: deque[float] = deque(maxlen=5000)

    def metrics(self) -> dict[str, Any]:
        now = time.time()
        per_market = {}
        for market, values in self.stats.get("per_market", {}).items():
            buckets = self.rates.get(market, {})
            per_market[market] = dict(
                values,
                messages_per_second=sum(
                    v for t, v in buckets.items() if int(now) - 10 <= t < int(now)
                )
                / min(10, max(1, now - self.started)),
            )
        return dict(
            per_market=per_market,
            notification_decisions=self.stats.get("notification_decisions", {}),
            summary_buffer=len(self.pending),
        )

    async def flush(self, key: str) -> None:
        event = self.pending.pop(key, None)
        if event:
            self.last_flush[key] = time.monotonic()
            await self.emit(event, False)

    async def flush_loop(self) -> None:
        while True:
            for key in list(self.pending):
                if time.monotonic() - self.last_flush.get(key, 0) >= 5:
                    await self.flush(key)
            await asyncio.sleep(1)

    async def signal(self, event: dict[str, Any]) -> None:
        key = event["source"] + ":" + event["symbol"]
        value = event["signal"]
        direction = 1 if value["change"] > 0 else -1
        level = min(3, max(1, int(abs(value["change"]) / value["threshold"])))
        old_shape = self.last_shape.get(key)
        immediate = old_shape is None or direction != old_shape[0] or level > old_shape[1]
        previous = self.pending.get(key)
        if previous and (
            previous["signal"]["change"] * value["change"] < 0
            or value["first_hit"] - previous["signal"]["last_hit"] > 60
        ):
            await self.flush(key)
            previous = None
        if previous:
            prior = previous["signal"]
            value["first_hit"] = prior["first_hit"]
            value["hits"] += prior["hits"]
            if abs(prior["peak_change"]) > abs(value["peak_change"]):
                value["peak_change"] = prior["peak_change"]
        self.pending[key] = event
        self.last_shape[key] = (
            direction,
            max(level, old_shape[1]) if old_shape and old_shape[0] == direction else level,
        )
        if immediate or time.monotonic() - self.last_flush.get(key, 0) >= 5:
            await self.flush(key)

    async def run(self, market: str) -> None:
        base = "https://api.binance.com" if market == "spot" else "https://fapi.binance.com"
        prefix = "/api/v3" if market == "spot" else "/fapi/v1"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            tasks: list[asyncio.Task[None]] = []
            groups: dict[str, tuple[str, float]] = {}
            symbols: set[str] = set()
            try:
                while True:
                    try:
                        async with session.get(base + prefix + "/ticker/24hr") as response:
                            response.raise_for_status()
                            tickers = await response.json()
                        new_groups = {}
                        for item in tickers:
                            symbol = item.get("symbol", "")
                            try:
                                volume = float(item["quoteVolume"])
                            except (ValueError, TypeError, KeyError):
                                continue
                            if (
                                not symbol.endswith("USDT")
                                or not math.isfinite(volume)
                                or volume < 500000
                            ):
                                continue
                            high = 100000000 if market == "spot" else 200000000
                            group = (
                                "high"
                                if volume >= high
                                else ("mid" if volume >= 10000000 else "low")
                            )
                            new_groups[symbol] = (group, volume)
                        if not new_groups:
                            raise ValueError("No eligible pairs")
                        groups.clear()
                        groups.update(new_groups)
                        self.universe_time[market] = time.monotonic()
                        self.status(market + "_universe", "live", f"{len(groups)} eligible pairs")
                        if symbols != set(groups):
                            for task in tasks:
                                task.cancel()
                            await asyncio.gather(*tasks, return_exceptions=True)
                            for number in range(len(tasks)):
                                self.status(f"{market}_stream_{number}", "retired", "Rebalancing")
                            symbols = set(groups)
                            ordered = sorted(symbols)
                            tasks = [
                                asyncio.create_task(
                                    self.shard(
                                        session,
                                        market,
                                        base + prefix,
                                        ordered[i : i + 150],
                                        groups,
                                        i // 150,
                                    )
                                )
                                for i in range(0, len(ordered), 150)
                            ]
                    except (aiohttp.ClientError, TimeoutError, ValueError, TypeError, KeyError):
                        self.status(market + "_universe", "error", "Volume universe refresh failed")
                    await asyncio.sleep(self.refresh if groups else 15)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    async def shard(
        self,
        session: aiohttp.ClientSession,
        market: str,
        rest: str,
        symbols: list[str],
        groups: dict[str, tuple[str, float]],
        number: int,
    ) -> None:
        name = f"{market}_stream_{number}"
        endpoint = (
            "wss://stream.binance.com:9443/ws"
            if market == "spot"
            else "wss://fstream.binance.com/market/ws"
        )
        semaphore = asyncio.Semaphore(3)
        while True:
            windows = {s: MinuteWindow() for s in symbols}
            for window in windows.values():
                window.gap = True
            repairs: dict[str, asyncio.Task[None]] = {}

            async def seed(symbol: str, windows: dict[str, MinuteWindow] = windows) -> None:
                try:
                    async with semaphore:
                        async with session.get(
                            rest + "/klines",
                            params={
                                "symbol": symbol,
                                "interval": "1m",
                                "limit": 5,
                            },
                        ) as response:
                            response.raise_for_status()
                            rows = await response.json()
                        windows[symbol].seed(rows, int(time.time() * 1000))
                        await asyncio.sleep(0.1)
                except (aiohttp.ClientError, TimeoutError, ValueError, TypeError, KeyError):
                    windows[symbol].gap = True

            try:
                self.status(name, "warming", "Connecting and loading reference bars")
                async with session.ws_connect(
                    endpoint,
                    heartbeat=20,
                    max_msg_size=1024 * 1024,
                    timeout=aiohttp.ClientWSTimeout(ws_receive=45, ws_close=5),
                ) as ws:
                    await ws.send_json(
                        {
                            "method": "SUBSCRIBE",
                            "params": [s.lower() + "@aggTrade" for s in symbols],
                            "id": 1,
                        }
                    )
                    for symbol in symbols:
                        repairs[symbol] = asyncio.create_task(seed(symbol))
                    last_status = 0.0
                    async for message in ws:
                        if message.type == aiohttp.WSMsgType.ERROR:
                            raise ConnectionError("Market stream failed")
                        if message.type != aiohttp.WSMsgType.TEXT:
                            continue
                        data = json.loads(message.data)
                        if "code" in data:
                            raise ValueError("Market subscription rejected")
                        if data.get("e") != "aggTrade" or data.get("s") not in windows:
                            continue
                        received = time.perf_counter()
                        symbol = data["s"]
                        window = windows[symbol]
                        change = window.update(data, int(time.time() * 1000))
                        if window.gap and repairs[symbol].done():
                            repairs[symbol] = asyncio.create_task(seed(symbol))
                        self.stats["market_messages"] = self.stats.get("market_messages", 0) + 1
                        counters = self.stats.setdefault("per_market", {}).setdefault(
                            market,
                            {
                                "messages": 0,
                                "valid_calculations": 0,
                                "threshold_hits": 0,
                                "invalid_or_warming": 0,
                                "stale_universe": 0,
                            },
                        )
                        counters["messages"] += 1
                        counters["last_received"] = time.time()
                        counters["last_trade"] = float(data["T"]) / 1000
                        bucket = int(time.time())
                        buckets = self.rates.setdefault(market, {})
                        buckets[bucket] = buckets.get(bucket, 0) + 1
                        self.rates[market] = {t: n for t, n in buckets.items() if t >= bucket - 11}
                        counters[
                            "valid_calculations" if change is not None else "invalid_or_warming"
                        ] += 1
                        self.latencies.append((time.perf_counter() - received) * 1000)
                        if time.monotonic() - last_status > 1:
                            gaps = sum(w.gap for w in windows.values())
                            ready = sum(
                                not w.gap
                                and w.last_time > 0
                                and int(time.time() * 1000) - w.last_time <= 10000
                                and all(
                                    m in w.bars
                                    for m in range(
                                        w.last_time // 60000 - 3, w.last_time // 60000 + 1
                                    )
                                )
                                for w in windows.values()
                            )
                            self.status(
                                name,
                                "degraded" if gaps else "live",
                                f"{len(symbols)} subscriptions; {gaps} gaps; "
                                f"{ready} fresh complete windows",
                            )
                            last_status = time.monotonic()
                        if (
                            change is None
                            or symbol not in groups
                            or time.monotonic() - self.universe_time.get(market, 0)
                            > 2 * self.refresh
                        ):
                            if change is not None:
                                counters["stale_universe"] += 1
                            continue
                        group, volume = groups[symbol]
                        if abs(change) < float(self.thresholds[f"{market}_{group}"]):
                            continue
                        counters["threshold_hits"] += 1
                        counters["last_threshold_hit"] = float(data["T"]) / 1000
                        await self.signal(
                            dict(
                                kind="market",
                                source="binance_" + market,
                                source_id=f"{symbol}:{data['a']}",
                                symbol=symbol,
                                title=f"{symbol} {change:+.2f}% · {market}",
                                body=f"Minute-bar reference (not rolling 180s). "
                                f"24h quote volume: {volume:.0f} USDT; group: {group.upper()}",
                                category="price",
                                published=float(data["T"]) / 1000,
                                url="",
                                signal=dict(
                                    change=change,
                                    peak_change=change,
                                    price=float(data["p"]),
                                    threshold=float(self.thresholds[f"{market}_{group}"]),
                                    volume=volume,
                                    group=group,
                                    hits=1,
                                    first_hit=float(data["T"]) / 1000,
                                    last_hit=float(data["T"]) / 1000,
                                ),
                            ),
                        )
                raise ConnectionError("Closed")
            except asyncio.CancelledError:
                raise
            except Exception:
                self.status(name, "error", "Disconnected; reference bars will be reloaded")
            finally:
                for task in repairs.values():
                    task.cancel()
                await asyncio.gather(*repairs.values(), return_exceptions=True)
            await asyncio.sleep(3)
