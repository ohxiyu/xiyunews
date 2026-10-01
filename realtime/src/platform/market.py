"""Event-driven Binance spot move monitoring from aggregate trades."""

import asyncio
import json
import math
import time
from collections import deque
from collections.abc import Callable
from pathlib import Path
from typing import Any

import aiohttp
import yaml

from .announcements import Emit, Status
from .signals import MoveWindow, move_gate

SHARD_SIZE = 150
ENTRY_VOLUME = 500000
# Hysteresis: a monitored pair stays until volume falls 20% below the entry level,
# so pairs hovering around the cutoff do not churn subscriptions every refresh.
EXIT_VOLUME = 400000
REST = "https://api.binance.com/api/v3"
STREAM = "wss://stream.binance.com:9443/ws"
# (time, price) of the previous alert for a spot symbol and direction, from the store.
LastAlert = Callable[[str, int], tuple[float, float | None] | None]


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


def day_ranges(tickers: list[dict[str, Any]], symbols: dict[str, Any]) -> dict[str, list[float]]:
    """Rolling 24h [high, low] of the monitored pairs at refresh time."""
    ranges = {}
    for item in tickers:
        if item.get("symbol") not in symbols:
            continue
        try:
            high, low = float(item["highPrice"]), float(item["lowPrice"])
        except (ValueError, TypeError, KeyError):
            continue
        if math.isfinite(high) and 0 < low <= high:
            ranges[item["symbol"]] = [high, low]
    return ranges


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
    def __init__(
        self,
        emit: Emit,
        status: Status,
        stats: dict[str, Any],
        last_alert: LastAlert = lambda symbol, direction: None,
    ) -> None:
        self.emit, self.status, self.stats = emit, status, stats
        self.last_alert = last_alert
        data = yaml.safe_load(
            (Path(__file__).resolve().parents[2] / "config/thresholds.yaml").read_text()
        )
        self.policy = data["market_alerts"]
        self.refresh = self.policy["universe_refresh_seconds"]
        self.universe_time: dict[str, float] = {}
        # 24h high/low per pair from the last refresh, extended by every trade since.
        self.ranges: dict[str, list[float]] = {}
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
        )

    async def run(self, market: str) -> None:
        if market != "spot":
            raise ValueError("Market alerts only support Binance spot")
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            tasks: dict[int, asyncio.Task[None]] = {}
            shards: list[list[str]] = []
            groups: dict[str, tuple[str, float]] = {}
            try:
                while True:
                    try:
                        async with session.get(REST + "/ticker/24hr") as response:
                            response.raise_for_status()
                            tickers = await response.json()
                        new_groups = eligible(tickers, int(time.time() * 1000), set(groups))
                        if not new_groups:
                            raise ValueError("No eligible pairs")
                        groups.clear()
                        groups.update(new_groups)
                        self.ranges = day_ranges(tickers, groups)
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
                                self.shard(session, market, shards[number], groups, number)
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
        symbols: list[str],
        groups: dict[str, tuple[str, float]],
        number: int,
    ) -> None:
        name = f"{market}_stream_{number}"
        policy = self.policy["move"]
        while True:
            # Pairs that left the universe stay subscribed until pruned; their data is ignored.
            windows = {
                s: MoveWindow(
                    policy["thresholds"][groups[s][0] if s in groups else "low"],
                    policy["window_seconds"],
                    policy["confirmation_ms"],
                )
                for s in symbols
            }
            try:
                self.status(name, "warming", f"{policy['window_seconds']}s live warmup")
                async with session.ws_connect(
                    STREAM,
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
                        if symbol not in windows or data.get("e") != "aggTrade":
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
                        threshold = policy["thresholds"][group]
                        if threshold != window.threshold:
                            # A volume-group change alters the threshold, not the price history.
                            window.threshold = threshold
                            window.since.clear()
                        moves = window.update(data, now_ms)
                        bounds = self.ranges.get(symbol)
                        if bounds and window.price:
                            bounds[0] = max(bounds[0], window.price)
                            bounds[1] = min(bounds[1], window.price)
                        self.stats["market_messages"] = self.stats.get("market_messages", 0) + 1
                        counters = self.stats.setdefault("per_market", {}).setdefault(
                            market,
                            {
                                "messages": 0,
                                "valid_calculations": 0,
                                "threshold_hits": 0,
                                "invalid_or_warming": 0,
                            },
                        )
                        counters["messages"] += 1
                        counters["last_received"] = time.time()
                        counters["last_trade"] = float(data.get("T", 0)) / 1000
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
                            warm = time.monotonic() - connected >= policy["window_seconds"]
                            self.status(
                                name,
                                "live" if warm else "warming",
                                f"{len(active)} pairs; {ready} ready ({recent} traded in 10s)",
                            )
                            last_status = time.monotonic()
                        for move in moves:
                            # The move stays confirmed on every trade; only a move the
                            # store's gate would accept is worth an event.
                            if not move_gate(
                                self.last_alert(symbol, move["direction"]),
                                move,
                                policy["cooldown_seconds"],
                                policy["continuation_percent"],
                            ):
                                continue
                            # The 24h high/low was set within this move's window.
                            move["extreme"] = bounds is not None and (
                                window.extreme(1) >= bounds[0]
                                if move["direction"] == 1
                                else window.extreme(-1) <= bounds[1]
                            )
                            counters["threshold_hits"] += 1
                            counters["last_threshold_hit"] = move["at"]
                            await self.emit(
                                dict(
                                    kind="market",
                                    source="binance_spot",
                                    source_id=f"{symbol}:{move['direction']}:{move['at']}",
                                    symbol=symbol,
                                    title="",
                                    body="",
                                    category="price",
                                    published=move["at"],
                                    url="",
                                    signal=dict(
                                        policy_version=3, move=move, volume=volume, group=group
                                    ),
                                ),
                                False,
                            )
                raise ConnectionError("Closed")
            except asyncio.CancelledError:
                raise
            except Exception:
                self.status(name, "error", "Disconnected; fresh warmup")
            await asyncio.sleep(3)
