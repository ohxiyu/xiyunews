"""Deterministic, bounded price detectors. No network or notification side effects."""
# ruff: noqa: RUF001

import math
from collections import deque
from typing import Any


class BurstWindow:
    """Exact last-traded prices at or before t-60s/t-180s, never minute-bar proxies."""

    def __init__(self, thresholds: dict[int, float], confirmation: int = 3000) -> None:
        self.thresholds = thresholds
        self.confirmation = confirmation
        self.points: dict[int, deque[tuple[int, float]]] = {60: deque(), 180: deque()}
        self.last_id: int | None = None
        self.last_time = 0
        self.start: int | None = None
        self.candidates: dict[int, int] = {}
        self.fired: set[int] = set()
        self.below: set[int] = set()
        self.ready = False

    def reset(self) -> None:
        for points in self.points.values():
            points.clear()
        self.start = None
        self.candidates.clear()
        self.fired.clear()
        self.below.clear()
        self.ready = False

    def update(self, data: dict[str, Any], now_ms: int) -> tuple[list[dict[str, Any]], list[int]]:
        timestamp, trade_id, price = int(data["T"]), int(data["a"]), float(data["p"])
        if (
            not math.isfinite(price)
            or price <= 0
            or timestamp < self.last_time
            or (self.last_id is not None and trade_id <= self.last_id)
        ):
            return [], []
        if now_ms - timestamp > 10000 or timestamp > now_ms + 2000:
            self.reset()
            self.last_id, self.last_time = None, 0
            return [], []
        if self.last_id is not None and trade_id != self.last_id + 1:
            self.reset()
        # No observations during an idle gap cannot establish continuous 3s confirmation.
        if timestamp - self.last_time > 2000:
            self.candidates.clear()
        self.last_id, self.last_time = trade_id, timestamp
        if self.start is None:
            self.start = timestamp
        changes = {}
        for seconds, points in self.points.items():
            # Identical adjacent prices add no information to a last-price reference.
            if not points or points[-1][1] != price:
                if points and points[-1][0] == timestamp:
                    points.pop()
                points.append((timestamp, price))
            cutoff = timestamp - seconds * 1000
            while len(points) > 1 and points[1][0] <= cutoff:
                points.popleft()
            if len(points) > 50000:
                # Fail closed under extreme load rather than use a truncated reference.
                self.reset()
                return [], []
            if self.start <= cutoff and points[0][0] <= cutoff:
                changes[seconds] = (price / points[0][1] - 1) * 100
        self.ready = len(changes) == 2
        if not self.ready:
            return [], []
        hits, resets = [], []
        for direction in (1, -1):
            matches = [
                (seconds, change)
                for seconds, change in changes.items()
                if direction * change + 1e-9 >= self.thresholds[seconds]
            ]
            if not matches:
                self.candidates.pop(direction, None)
                self.fired.discard(direction)
                if direction not in self.below:
                    resets.append(direction)
                self.below.add(direction)
                continue
            self.below.discard(direction)
            since = self.candidates.setdefault(direction, timestamp)
            if direction in self.fired or timestamp - since < self.confirmation:
                continue
            seconds, change = max(matches, key=lambda pair: abs(pair[1]) / self.thresholds[pair[0]])
            self.fired.add(direction)
            hits.append(
                dict(
                    type="burst",
                    direction=direction,
                    change=change,
                    window_seconds=seconds,
                    threshold=self.thresholds[seconds],
                    crossed_at=since / 1000,
                    at=timestamp / 1000,
                    breakout=False,
                )
            )
        return hits, resets


class TrendWindow:
    def __init__(self, six: float = 5, day: float = 8, edge: float = 0.1) -> None:
        self.bars: dict[int, tuple[float, float, float]] = {}
        self.six, self.day, self.edge = six, day, edge

    def seed(self, rows: list[list[Any]], now_ms: int) -> None:
        for row in rows:
            start, end = int(row[0]), int(row[6])
            high, low, close = float(row[2]), float(row[3]), float(row[4])
            if (
                start % 900000 == 0
                and end == start + 899999
                and end < now_ms
                and all(math.isfinite(v) and v > 0 for v in (high, low, close))
                and low <= close <= high
            ):
                self.bars.setdefault(start, (high, low, close))
        self.bars = dict(sorted(self.bars.items())[-97:])

    def update(self, k: dict[str, Any], now_ms: int) -> dict[str, Any] | None:
        if not k.get("x"):
            return None
        start, end = int(k["t"]), int(k["T"])
        if start in self.bars or (self.bars and start <= max(self.bars)):
            return None
        previous = [self.bars.get(start - i * 900000) for i in range(96, 0, -1)]
        self.seed([[start, 0, k["h"], k["l"], k["c"], 0, end]], now_ms)
        if (
            start not in self.bars
            or now_ms - end > 10000
            or end > now_ms
            or any(bar is None for bar in previous)
        ):
            return None
        bars = [bar for bar in previous if bar is not None]
        price = self.bars[start][2]
        six = (price / bars[-24][2] - 1) * 100
        day = (price / bars[0][2] - 1) * 100
        current = [*bars[1:], self.bars[start]]
        high, low = max(b[0] for b in current), min(b[1] for b in current)
        if high <= low:
            return None
        position = (price - low) / (high - low)
        for direction in (1, -1):
            qualified = [(21600, six, self.six), (86400, day, self.day)]
            qualified = [q for q in qualified if direction * q[1] + 1e-9 >= q[2]]
            at_edge = position >= 1 - self.edge if direction == 1 else position <= self.edge
            if not qualified or not at_edge:
                continue
            seconds, change, threshold = max(qualified, key=lambda q: abs(q[1]) / q[2])
            breakout = (
                price > max(b[0] for b in bars)
                if direction == 1
                else (price < min(b[1] for b in bars))
            )
            return dict(
                type="trend",
                direction=direction,
                change=change,
                window_seconds=seconds,
                threshold=threshold,
                at=end / 1000,
                breakout=breakout,
                change_6h=six,
                change_24h=day,
            )
        return None


def signal_title(symbol: str, components: list[dict[str, Any]]) -> str:
    coin = symbol.removesuffix("USDT")
    burst = next((s for s in components if s["type"] == "burst"), None)
    trend = next((s for s in components if s["type"] == "trend"), None)
    selected = burst or trend
    assert selected is not None
    direction = "上涨" if selected["direction"] == 1 else "下跌"
    if burst:
        title = (
            f"{coin} {burst['window_seconds'] // 60} 分钟内{direction} {abs(burst['change']):.2f}%"
        )
    else:
        assert trend is not None
        movement = "持续走强" if trend["direction"] == 1 else "持续走弱"
        title = (
            f"{coin} {movement}，{trend['window_seconds'] // 3600} 小时"
            f"{direction} {abs(trend['change']):.2f}%"
        )
    if trend and trend["breakout"]:
        title += "，突破 24 小时新高" if trend["direction"] == 1 else "，跌破 24 小时新低"
    return title
