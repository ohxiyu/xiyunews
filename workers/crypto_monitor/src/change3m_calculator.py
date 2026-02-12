"""
3-Minute Change Calculator Module

Calculates percentage change from Binance 1m klines data.
"""

from typing import List, Optional
import logging

logger = logging.getLogger("cexMonitor.change3m")


class Change3MCalculator:
    """Calculate 3-minute percentage change from klines data"""

    @staticmethod
    def calculate_change(klines: List[list]) -> Optional[float]:
        """
        Calculate 3-minute percentage change.

        Args:
            klines: List of kline data [[open_time, open, high, low, close, volume, ...], ...]
                    Must have at least 4 bars (4 minutes of 1m data)

        Returns:
            change3mPct: Percentage change (e.g., 5.23 for +5.23%, -3.42 for -3.42%)
            None if invalid data

        Formula:
            close_now = klines[-1][4]  # Most recent close price
            close_3m = klines[-4][4]   # Close price 3 minutes ago
            change3mPct = (close_now / close_3m - 1) * 100

        Example:
            klines = [[timestamp, open, high, low, close, volume, ...], ...]
            If close_now=100, close_3m=95, then change3mPct = (100/95-1)*100 = 5.26%
        """
        if not klines or len(klines) < 4:
            logger.debug(f"Insufficient klines data: {len(klines) if klines else 0} bars (need 4+)")
            return None

        try:
            # Extract close prices (index 4 in Binance kline data)
            # kline format: [open_time, open, high, low, close, volume, close_time, ...]
            close_now = float(klines[-1][4])
            close_3m = float(klines[-4][4])

            if close_3m == 0:
                logger.warning(f"Zero close price 3 minutes ago (close_3m={close_3m})")
                return None

            # Calculate percentage change
            change3mPct = (close_now / close_3m - 1) * 100

            return change3mPct

        except (IndexError, ValueError, TypeError) as e:
            logger.error(f"Error calculating 3m change: {e}, klines length: {len(klines) if klines else 0}")
            return None

    @staticmethod
    def check_trigger(change3mPct: float, threshold_pct: float) -> bool:
        """
        Check if absolute change exceeds threshold.

        Args:
            change3mPct: Percentage change (e.g., 5.23 or -3.42)
            threshold_pct: Threshold to compare (e.g., 3 for 3%)

        Returns:
            True if abs(change3mPct) >= threshold_pct

        Example:
            check_trigger(5.23, 3) -> True (5.23 > 3)
            check_trigger(-3.42, 3) -> True (|-3.42| > 3)
            check_trigger(2.1, 3) -> False (2.1 < 3)
        """
        return abs(change3mPct) >= threshold_pct

    @staticmethod
    def get_direction(change3mPct: float) -> str:
        """
        Get direction of change.

        Args:
            change3mPct: Percentage change

        Returns:
            "UP" if positive, "DOWN" if negative or zero

        Example:
            get_direction(5.23) -> "UP"
            get_direction(-3.42) -> "DOWN"
            get_direction(0) -> "DOWN"
        """
        return "UP" if change3mPct > 0 else "DOWN"
