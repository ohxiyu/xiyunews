"""
Volume Grouper Module

Groups symbols by 24h quote volume (absolute thresholds) and assigns alert thresholds.
Spot and Futures markets have different volume thresholds and alert thresholds.
"""

import time
import logging
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger("cexMonitor.volumeGrouper")


class VolumeGroup(Enum):
    """Volume group enumeration based on absolute 24h quote volume"""
    HIGH = "HIGH"   # Highest volume tier
    MID = "MID"     # Medium volume tier
    LOW = "LOW"     # Lower volume tier (above minimum)


@dataclass
class SymbolGroupInfo:
    """
    Information about a symbol's volume group assignment.

    Attributes:
        symbol: Trading symbol (e.g., "BTCUSDT")
        market: Market type ("spot" or "futures")
        quote_volume_24h: 24-hour quote volume in USDT
        group: Volume group (HIGH/MID/LOW)
        threshold_pct: Threshold percentage for alerts
    """
    symbol: str
    market: str
    quote_volume_24h: float
    group: VolumeGroup
    threshold_pct: float


class VolumeGrouper:
    """
    Groups symbols by 24h quote volume and assigns alert thresholds.

    Volume groups are calculated separately for Spot and Futures markets
    using ABSOLUTE volume thresholds (not percentile-based).

    Spot Market Thresholds:
    - HIGH: > $100M → 3% alert threshold
    - MID: $10M - $100M → 8% alert threshold
    - LOW: $500k - $10M → 15% alert threshold
    - Below $500k: filtered out

    Futures Market Thresholds:
    - HIGH: > $200M → 5% alert threshold
    - MID: $10M - $200M → 15% alert threshold
    - LOW: $500k - $10M → 30% alert threshold
    - Below $500k: filtered out
    """

    # Spot market volume thresholds (in USDT)
    SPOT_MIN_VOLUME = 500_000              # $500k minimum
    SPOT_MID_VOLUME_THRESHOLD = 10_000_000      # $10M
    SPOT_HIGH_VOLUME_THRESHOLD = 100_000_000    # $100M

    # Futures market volume thresholds (in USDT)
    FUTURES_MIN_VOLUME = 500_000                # $500k minimum
    FUTURES_MID_VOLUME_THRESHOLD = 10_000_000   # $10M
    FUTURES_HIGH_VOLUME_THRESHOLD = 200_000_000 # $200M

    def __init__(self, refresh_interval: int = 600):
        """
        Initialize volume grouper.

        Args:
            refresh_interval: Seconds between group refreshes (default: 600 = 10 minutes)
        """
        self.refresh_interval = refresh_interval
        self.last_refresh: float = 0

        # Separate mappings for spot and futures
        self.spot_groups: Dict[str, SymbolGroupInfo] = {}
        self.futures_groups: Dict[str, SymbolGroupInfo] = {}

        # Spot market alert thresholds
        self.spot_thresholds = {
            VolumeGroup.HIGH: 3.0,   # 3% for high-volume spot
            VolumeGroup.MID: 8.0,    # 8% for mid-volume spot
            VolumeGroup.LOW: 15.0    # 15% for low-volume spot
        }

        # Futures market alert thresholds
        self.futures_thresholds = {
            VolumeGroup.HIGH: 5.0,   # 5% for high-volume futures
            VolumeGroup.MID: 15.0,   # 15% for mid-volume futures
            VolumeGroup.LOW: 30.0    # 30% for low-volume futures
        }

        logger.info(
            f"Initialized VolumeGrouper (refresh_interval={refresh_interval}s, "
            f"spot_thresholds={self.spot_thresholds}, "
            f"futures_thresholds={self.futures_thresholds})"
        )

    async def refresh_groups(self, spot_tickers: List[dict], futures_tickers: List[dict]):
        """
        Refresh volume groups for both markets.

        Args:
            spot_tickers: List of spot 24hr ticker dicts with keys: symbol, quoteVolume
            futures_tickers: List of futures 24hr ticker dicts with keys: symbol, quoteVolume

        Updates:
            self.spot_groups
            self.futures_groups
            self.last_refresh
        """
        try:
            # Calculate groups for each market
            self.spot_groups = self._calculate_groups(spot_tickers, "spot")
            self.futures_groups = self._calculate_groups(futures_tickers, "futures")

            self.last_refresh = time.time()

            logger.info(
                f"Groups refreshed: {len(self.spot_groups)} spot symbols, "
                f"{len(self.futures_groups)} futures symbols"
            )

            # Log group distribution
            self._log_group_distribution()

        except Exception as e:
            logger.error(f"Failed to refresh groups: {e}", exc_info=True)

    def _calculate_groups(self, tickers: List[dict], market: str) -> Dict[str, SymbolGroupInfo]:
        """
        Calculate groups for one market based on absolute volume thresholds.

        Args:
            tickers: List of ticker dicts (already filtered for USDT pairs with quoteVolume > 0)
            market: Market type ("spot" or "futures")

        Returns:
            Dict mapping symbol -> SymbolGroupInfo

        Spot Volume Groups (based on absolute 24h quoteVolume in USDT):
        - HIGH: > $100M → 3% threshold
        - MID: $10M - $100M → 8% threshold
        - LOW: $500k - $10M → 15% threshold
        - Below $500k: filtered out

        Futures Volume Groups:
        - HIGH: > $200M → 5% threshold
        - MID: $10M - $200M → 15% threshold
        - LOW: $500k - $10M → 30% threshold
        - Below $500k: filtered out
        """
        if not tickers:
            logger.warning(f"No tickers provided for {market} grouping")
            return {}

        # Select thresholds based on market type
        if market == "spot":
            min_volume = self.SPOT_MIN_VOLUME
            mid_threshold = self.SPOT_MID_VOLUME_THRESHOLD
            high_threshold = self.SPOT_HIGH_VOLUME_THRESHOLD
            alert_thresholds = self.spot_thresholds
        else:  # futures
            min_volume = self.FUTURES_MIN_VOLUME
            mid_threshold = self.FUTURES_MID_VOLUME_THRESHOLD
            high_threshold = self.FUTURES_HIGH_VOLUME_THRESHOLD
            alert_thresholds = self.futures_thresholds

        groups = {}

        for ticker in tickers:
            symbol = ticker['symbol']
            volume = float(ticker['quoteVolume'])

            # Filter out symbols below minimum threshold
            if volume < min_volume:
                continue

            # Determine group based on absolute volume
            if volume > high_threshold:
                group = VolumeGroup.HIGH
            elif volume > mid_threshold:
                group = VolumeGroup.MID
            else:
                group = VolumeGroup.LOW

            # Create SymbolGroupInfo with market-specific alert threshold
            groups[symbol] = SymbolGroupInfo(
                symbol=symbol,
                market=market,
                quote_volume_24h=volume,
                group=group,
                threshold_pct=alert_thresholds[group]
            )

        return groups

    def _log_group_distribution(self):
        """Log distribution of symbols across groups"""
        # Count symbols in each group for spot
        spot_high = sum(1 for g in self.spot_groups.values() if g.group == VolumeGroup.HIGH)
        spot_mid = sum(1 for g in self.spot_groups.values() if g.group == VolumeGroup.MID)
        spot_low = sum(1 for g in self.spot_groups.values() if g.group == VolumeGroup.LOW)

        # Count symbols in each group for futures
        futures_high = sum(1 for g in self.futures_groups.values() if g.group == VolumeGroup.HIGH)
        futures_mid = sum(1 for g in self.futures_groups.values() if g.group == VolumeGroup.MID)
        futures_low = sum(1 for g in self.futures_groups.values() if g.group == VolumeGroup.LOW)

        logger.info(
            f"Spot distribution: HIGH={spot_high}, MID={spot_mid}, LOW={spot_low}"
        )
        logger.info(
            f"Futures distribution: HIGH={futures_high}, MID={futures_mid}, LOW={futures_low}"
        )

    def get_threshold(self, symbol: str, market: str) -> Optional[float]:
        """
        Get alert threshold for a symbol.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            market: Market type ("spot" or "futures")

        Returns:
            Threshold percentage (e.g., 3.0 for 3%)
            None if symbol not found

        Example:
            get_threshold("BTCUSDT", "spot") -> 3.0 (if BTCUSDT is in HIGH group)
        """
        groups = self.spot_groups if market == "spot" else self.futures_groups
        info = groups.get(symbol)
        return info.threshold_pct if info else None

    def get_group_info(self, symbol: str, market: str) -> Optional[SymbolGroupInfo]:
        """
        Get full group info for a symbol.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            market: Market type ("spot" or "futures")

        Returns:
            SymbolGroupInfo object
            None if symbol not found

        Example:
            info = get_group_info("BTCUSDT", "spot")
            # info.group -> VolumeGroup.HIGH
            # info.threshold_pct -> 3.0
            # info.quote_volume_24h -> 1234567890.0
        """
        groups = self.spot_groups if market == "spot" else self.futures_groups
        return groups.get(symbol)

    def get_all_symbols(self, market: str) -> List[str]:
        """
        Get list of all symbols for a market.

        Args:
            market: Market type ("spot" or "futures")

        Returns:
            List of symbol strings

        Example:
            symbols = get_all_symbols("spot")
            # ["BTCUSDT", "ETHUSDT", ...]
        """
        groups = self.spot_groups if market == "spot" else self.futures_groups
        return list(groups.keys())

    def needs_refresh(self) -> bool:
        """
        Check if groups need to be refreshed.

        Returns:
            True if time since last refresh >= refresh_interval

        Example:
            if grouper.needs_refresh():
                await grouper.refresh_groups(spot_tickers, futures_tickers)
        """
        return (time.time() - self.last_refresh) >= self.refresh_interval

    def update_spot_thresholds(self, high: float, mid: float, low: float):
        """
        Update spot market alert thresholds.

        Args:
            high: Threshold for HIGH volume group (e.g., 3.0 for 3%)
            mid: Threshold for MID volume group (e.g., 8.0 for 8%)
            low: Threshold for LOW volume group (e.g., 15.0 for 15%)

        Note:
            Call refresh_groups() after updating to apply new thresholds.
        """
        self.spot_thresholds[VolumeGroup.HIGH] = high
        self.spot_thresholds[VolumeGroup.MID] = mid
        self.spot_thresholds[VolumeGroup.LOW] = low

        logger.info(f"Updated spot thresholds: HIGH={high}%, MID={mid}%, LOW={low}%")

    def update_futures_thresholds(self, high: float, mid: float, low: float):
        """
        Update futures market alert thresholds.

        Args:
            high: Threshold for HIGH volume group (e.g., 5.0 for 5%)
            mid: Threshold for MID volume group (e.g., 15.0 for 15%)
            low: Threshold for LOW volume group (e.g., 30.0 for 30%)

        Note:
            Call refresh_groups() after updating to apply new thresholds.
        """
        self.futures_thresholds[VolumeGroup.HIGH] = high
        self.futures_thresholds[VolumeGroup.MID] = mid
        self.futures_thresholds[VolumeGroup.LOW] = low

        logger.info(f"Updated futures thresholds: HIGH={high}%, MID={mid}%, LOW={low}%")
