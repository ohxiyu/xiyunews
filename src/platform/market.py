"""Event-driven spot burst and closed-candle trend monitoring."""

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
from .signals import BurstWindow, TrendWindow, signal_title


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


SHARD_SIZE = 150
ENTRY_VOLUME = 500000
# Hysteresis: a monitored pair stays until volume falls 20% below the entry level,
# so pairs hovering around the cutoff do not churn subscriptions every refresh.
EXIT_VOLUME = 400000


def eligible(
    tickers: list[dict[str, Any]], now_ms: int, current: set[str] | frozenset[str] = frozenset()
) -> dict[str, tuple[str, float]]:
    """USDT spot pairs by 24h quote volume, excluding delisted or halted pairs.

    Binance keeps returning delisted symbols from /ticker/24hr with their last
    rolling statistics; a closeTime older than an hour means no live window.
    """
    groups = {}
    for item in tickers:
        symbol = item.get("symbol", "")
        try:
            volume = float(item["quoteVolume"])
            closed = int(item["closeTime"])
        except (ValueError, TypeError, KeyError):
            continue
        if (
            not symbol.endswith("USDT")
            or not math.isfinite(volume)
            or volume < (EXIT_VOLUME if symbol in current else ENTRY_VOLUME)
            or now_ms - closed > 3600000
        ):
            continue
        group = "high" if volume >= 100000000 else ("mid" if volume >= 10000000 else "low")
        groups[symbol] = (group, volume)
    return groups


def plan_shards(
    shards: list[list[str]], universe: set[str], size: int = SHARD_SIZE, prune: int = 30
) -> tuple[list[list[str]], set[int]]:
    """Stable shard membership so a universe change restarts only the affected streams.

    Removed pairs stay subscribed (their data is ignored) until a shard accumulates
    more than `prune` of them; new pairs fill the last shard with room.
    """
    result = [list(shard) for shard in shards]
    changed = set()
    for number, shard in enumerate(result):
        if sum(symbol not in universe for symbol in shard) > prune:
            result[number] = [symbol for symbol in shard if symbol in universe]
            changed.add(number)
    assigned = {symbol for shard in result for symbol in shard}
    for symbol in sorted(universe - assigned):
        room = [n for n in range(len(result)) if len(result[n]) < size]
        if not room:
            result.append([])
            room = [len(result) - 1]
        number = room[-1]
        result[number].append(symbol)
        changed.add(number)
    return result, changed


class Market:
    def __init__(self, emit: Emit, status: Status, stats: dict[str, Any]) -> None:
        self.emit, self.status, self.stats = emit, status, stats
        data = yaml.safe_load(
            (Path(__file__).resolve().parents[2] / "config/thresholds.yaml").read_text()
        )
        self.policy = data["market_alerts"]
        self.seed_semaphore = asyncio.Semaphore(3)
        self.refresh = self.policy["universe_refresh_seconds"]
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
                if time.monotonic() - self.last_flush[key] >= 1:
                    await self.flush(key)
            await asyncio.sleep(0.1)

    async def signal(self, event: dict[str, Any]) -> None:
        component = event["signal"]["components"][0]
        key = f"{event['source']}:{event['symbol']}:{component['direction']}"
        previous = self.pending.get(key)
        if previous:
            parts = {c["type"]: c for c in previous["signal"]["components"]}
            parts[component["type"]] = component
            event["signal"]["components"] = list(parts.values())
        else:
            self.last_flush[key] = time.monotonic()
        event["title"] = signal_title(event["symbol"], event["signal"]["components"])
        self.pending[key] = event

    async def run(self, market: str) -> None:
        if market != "spot":
            raise ValueError("Alert policy v2 only supports spot")
        base = "https://api.binance.com" if market == "spot" else "https://fapi.binance.com"
        prefix = "/api/v3" if market == "spot" else "/fapi/v1"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            tasks: dict[int, asyncio.Task[None]] = {}
            shards: list[list[str]] = []
            groups: dict[str, tuple[str, float]] = {}
            try:
                while True:
                    try:
                        async with session.get(base + prefix + "/ticker/24hr") as response:
                            response.raise_for_status()
                            tickers = await response.json()
                        new_groups = eligible(tickers, int(time.time() * 1000), set(groups))
                        if not new_groups:
                            raise ValueError("No eligible pairs")
                        groups.clear()
                        groups.update(new_groups)
                        self.universe_time[market] = time.monotonic()
                        self.status(market + "_universe", "live", f"{len(groups)} eligible pairs")
                        shards, changed = plan_shards(shards, set(groups))
                        for number in sorted(changed):
                            old = tasks.pop(number, None)
                            if old:
                                old.cancel()
                                await asyncio.gather(old, return_exceptions=True)
                            if not shards[number]:
                                self.status(f"{market}_stream_{number}", "retired", "Empty")
                                continue
                            tasks[number] = asyncio.create_task(
                                self.shard(
                                    session,
                                    market,
                                    base + prefix,
                                    shards[number],
                                    groups,
                                    number,
                                )
                            )
                    except (aiohttp.ClientError, TimeoutError, ValueError, TypeError, KeyError):
                        self.status(market + "_universe", "error", "Volume universe refresh failed")
                    await asyncio.sleep(self.refresh if groups else 15)
            finally:
                for task in tasks.values():
                    task.cancel()
                await asyncio.gather(*tasks.values(), return_exceptions=True)

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
        while True:
            windows = {
                s: BurstWindow(
                    dict(self.policy["burst"]["thresholds"][groups[s][0]]),
                    self.policy["burst"]["confirmation_ms"],
                )
                for s in symbols
            }
            trends = {
                s: TrendWindow(
                    self.policy["trend"]["change_6h"],
                    self.policy["trend"]["change_24h"],
                    self.policy["trend"]["edge_fraction"],
                )
                for s in symbols
            }
            repairs: dict[str, asyncio.Task[None]] = {}
            seed_attempt: dict[str, float] = {}
            listings: set[str] = set()

            async def seed(
                symbol: str,
                trends: dict[str, TrendWindow] = trends,
                seed_attempt: dict[str, float] = seed_attempt,
                listings: set[str] = listings,
            ) -> None:
                seed_attempt[symbol] = time.monotonic()
                try:
                    async with self.seed_semaphore:
                        async with session.get(
                            rest + "/klines",
                            params={
                                "symbol": symbol,
                                "interval": "15m",
                                "limit": 98,
                            },
                        ) as response:
                            response.raise_for_status()
                            rows = await response.json()
                            trends[symbol].seed(rows, int(time.time() * 1000))
                        # Pairs listed less than 24h ago cannot have trend history yet.
                        if len(rows) < 97:
                            listings.add(symbol)
                        else:
                            listings.discard(symbol)
                        await asyncio.sleep(0.1)
                except (aiohttp.ClientError, TimeoutError, ValueError, TypeError, KeyError):
                    pass  # Incomplete history fails closed and is retried on the next candle.

            try:
                self.status(name, "warming", "Loading trend history; 180s live burst warmup")
                async with session.ws_connect(
                    endpoint,
                    heartbeat=20,
                    max_msg_size=1024 * 1024,
                    timeout=aiohttp.ClientWSTimeout(ws_receive=45, ws_close=5),
                ) as ws:
                    await ws.send_json(
                        {
                            "method": "SUBSCRIBE",
                            "params": [
                                s.lower() + suffix
                                for s in symbols
                                for suffix in ("@aggTrade", "@kline_15m")
                            ],
                            "id": 1,
                        }
                    )
                    for symbol in symbols:
                        repairs[symbol] = asyncio.create_task(seed(symbol))
                    last_status = 0.0
                    connected = time.monotonic()
                    async for message in ws:
                        if message.type == aiohttp.WSMsgType.ERROR:
                            raise ConnectionError("Market stream failed")
                        if message.type != aiohttp.WSMsgType.TEXT:
                            continue
                        data = json.loads(message.data)
                        if "code" in data:
                            raise ValueError("Market subscription rejected")
                        symbol = data.get("s")
                        if symbol not in windows or data.get("e") not in ("aggTrade", "kline"):
                            continue
                        received = time.perf_counter()
                        now_ms = int(time.time() * 1000)
                        window = windows[symbol]
                        if (
                            symbol not in groups
                            or time.monotonic() - self.universe_time.get(market, 0)
                            > 2 * self.refresh
                        ):
                            window.reset()
                            continue
                        group, volume = groups[symbol]
                        thresholds = dict(self.policy["burst"]["thresholds"][group])
                        if thresholds != window.thresholds:
                            # A volume-group change alters thresholds, not the price history.
                            window.thresholds = thresholds
                            window.candidates.clear()
                        hits: list[dict[str, Any]] = []
                        if data["e"] == "aggTrade":
                            hits, resets = window.update(data, now_ms)
                            for direction in resets:
                                await self.flush(f"binance_spot:{symbol}:{direction}")
                                await self.emit(
                                    dict(
                                        kind="market_reset",
                                        source="binance_spot",
                                        symbol=symbol,
                                        direction=direction,
                                    ),
                                    False,
                                )
                        else:
                            hit = trends[symbol].update(data["k"], now_ms)
                            if hit:
                                hits.append(hit)
                            latest = now_ms // 900000 * 900000 - 900000
                            if (
                                not trends[symbol].complete(latest, window.last_time)
                                and repairs[symbol].done()
                                and time.monotonic() - seed_attempt.get(symbol, 0) >= 60
                            ):
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
                        counters["last_trade"] = float(data.get("T", data.get("E", 0))) / 1000
                        counters[
                            "valid_calculations" if window.ready else "invalid_or_warming"
                        ] += 1
                        bucket = int(time.time())
                        buckets = self.rates.setdefault(market, {})
                        buckets[bucket] = buckets.get(bucket, 0) + 1
                        self.rates[market] = {t: n for t, n in buckets.items() if t >= bucket - 11}
                        self.latencies.append((time.perf_counter() - received) * 1000)
                        if time.monotonic() - last_status > 1:
                            # A quiet pair keeps a valid window between trades; readiness is
                            # not "traded within the last 10 seconds".
                            active = [s for s in symbols if s in groups]
                            ready = sum(windows[s].ready for s in active)
                            recent = sum(now_ms - windows[s].last_time <= 10000 for s in active)
                            latest = now_ms // 900000 * 900000 - 900000
                            history = sum(
                                trends[s].complete(latest, windows[s].last_time) for s in active
                            )
                            young = len(listings.intersection(active))
                            warm = time.monotonic() - connected >= 180
                            self.status(
                                name,
                                "live" if warm and history + young >= len(active) else "warming",
                                f"{len(active)} pairs; {ready} burst ready "
                                f"({recent} traded in 10s); "
                                f"{history} trend ready; {young} listed <24h",
                            )
                            last_status = time.monotonic()
                        for hit in hits:
                            counters["threshold_hits"] += 1
                            counters["last_threshold_hit"] = hit["at"]
                            await self.signal(
                                dict(
                                    kind="market",
                                    source="binance_spot",
                                    source_id=f"{symbol}:{hit['type']}:{hit['at']}",
                                    symbol=symbol,
                                    title="",
                                    body="",
                                    category="price",
                                    published=hit["at"],
                                    url="",
                                    signal=dict(
                                        policy_version=2,
                                        components=[hit],
                                        volume=volume,
                                        group=group,
                                    ),
                                )
                            )
                raise ConnectionError("Closed")
            except asyncio.CancelledError:
                raise
            except Exception:
                self.status(name, "error", "Disconnected; fresh burst warmup and trend reload")
            finally:
                for task in repairs.values():
                    task.cancel()
                await asyncio.gather(*repairs.values(), return_exceptions=True)
            await asyncio.sleep(3)
