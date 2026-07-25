"""Calculate three-minute price changes from Binance one-minute klines."""

import logging
from collections.abc import Sequence
from typing import Any

logger = logging.getLogger("coinsignal.change3m")


class Change3MCalculator:
    @staticmethod
    def calculate_change(klines: Sequence[Sequence[Any]]) -> float | None:
        if len(klines) < 4:
            logger.debug("Insufficient kline data: %s bars; need at least 4", len(klines))
            return None

        try:
            current_close = float(klines[-1][4])
            close_three_minutes_ago = float(klines[-4][4])
        except (IndexError, TypeError, ValueError) as exc:
            logger.error("Invalid kline data: %s", exc)
            return None

        if close_three_minutes_ago <= 0:
            logger.warning("Invalid historical close price: %s", close_three_minutes_ago)
            return None
        return (current_close / close_three_minutes_ago - 1) * 100

    @staticmethod
    def check_trigger(change_3m_pct: float, threshold_pct: float) -> bool:
        if threshold_pct <= 0:
            raise ValueError("threshold_pct must be greater than zero")
        return abs(change_3m_pct) >= threshold_pct

    @staticmethod
    def get_direction(change_3m_pct: float) -> str:
        if change_3m_pct > 0:
            return "UP"
        if change_3m_pct < 0:
            return "DOWN"
        return "FLAT"
