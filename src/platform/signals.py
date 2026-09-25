"""Deterministic, bounded price detector and alert gate. No network or notification effects."""
# ruff: noqa: RUF001

import math
from collections import deque
from typing import Any


class MoveWindow:
    """Change against the exact last-traded price at or before t-180s, never a minute bar."""

    def __init__(self, threshold: float, seconds: int = 180, confirmation: int = 3000) -> None:
        self.threshold = threshold
        self.seconds = seconds
        self.confirmation = confirmation
        self.points: deque[tuple[int, float]] = deque()
        self.last_id: int | None = None
        self.last_time = 0
        self.price = 0.0
        self.start: int | None = None
        self.since: dict[int, int] = {}
        self.ready = False

    def reset(self) -> None:
        self.points.clear()
        self.start = None
        self.since.clear()
        self.ready = False

    def extreme(self, direction: int) -> float:
        """Highest (rising) or lowest (falling) price traded within the window."""
        prices = [price for _, price in self.points]
        return max(prices) if direction == 1 else min(prices)

    def update(self, data: dict[str, Any], now_ms: int) -> list[dict[str, Any]]:
        """Directions whose move has stayed beyond the threshold for the confirmation time."""
        timestamp, trade_id, price = int(data["T"]), int(data["a"]), float(data["p"])
        if (
            not math.isfinite(price)
            or price <= 0
            or timestamp < self.last_time
            or (self.last_id is not None and trade_id <= self.last_id)
        ):
            return []
        if now_ms - timestamp > 10000 or timestamp > now_ms + 2000:
            self.reset()
            self.last_id, self.last_time = None, 0
            return []
        if self.last_id is not None and trade_id != self.last_id + 1:
            self.reset()
        # No observations during an idle gap cannot establish continuous confirmation.
        if timestamp - self.last_time > 2000:
            self.since.clear()
        self.last_id, self.last_time, self.price = trade_id, timestamp, price
        if self.start is None:
            self.start = timestamp
        points = self.points
        # Identical adjacent prices add no information to a last-price reference.
        if not points or points[-1][1] != price:
            if points and points[-1][0] == timestamp:
                points.pop()
            points.append((timestamp, price))
        cutoff = timestamp - self.seconds * 1000
        while len(points) > 1 and points[1][0] <= cutoff:
            points.popleft()
        if len(points) > 50000:
            # Fail closed under extreme load rather than use a truncated reference.
            self.reset()
            return []
        self.ready = self.start <= cutoff and points[0][0] <= cutoff
        if not self.ready:
            return []
        change = (price / points[0][1] - 1) * 100
        moves = []
        for direction in (1, -1):
            if direction * change + 1e-9 < self.threshold:
                self.since.pop(direction, None)
                continue
            since = self.since.setdefault(direction, timestamp)
            if timestamp - since >= self.confirmation:
                moves.append(
                    dict(
                        direction=direction,
                        change=change,
                        threshold=self.threshold,
                        window_seconds=self.seconds,
                        crossed_at=since / 1000,
                        at=timestamp / 1000,
                        price=price,
                    )
                )
        return moves


def move_gate(
    last: tuple[float, float | None] | None,
    move: dict[str, Any],
    cooldown: float,
    continuation: float,
) -> str:
    """Same coin and direction: once per cooldown, sooner only after a further move.

    `last` is the (time, price) of the previous alert in this direction; a carried-over
    alert without a price only expires. Returns "fresh", "continuation" or "".
    """
    if last is None or move["at"] - last[0] >= cooldown:
        return "fresh"
    further = move["direction"] * (move["price"] / last[1] - 1) * 100 if last[1] else 0
    return "continuation" if further + 1e-9 >= continuation else ""


def signal_title(symbol: str, move: dict[str, Any]) -> str:
    up = move["direction"] == 1
    title = (
        f"{symbol.removesuffix('USDT')} {move['window_seconds'] // 60} 分钟内"
        f"{'上涨' if up else '下跌'} {abs(move['change']):.2f}%"
    )
    if move.get("further"):
        title += f"，较上次提醒再{'涨' if up else '跌'} {move['further']:.1f}%"
    if move.get("extreme"):
        title += "，创 24 小时新高" if up else "，创 24 小时新低"
    return title
