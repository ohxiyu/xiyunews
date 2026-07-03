"""Group symbols by 24h quote volume and assign alert thresholds."""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

logger = logging.getLogger("cexMonitor.volumeGrouper")


class VolumeGroup(Enum):
    HIGH = "HIGH"
    MID = "MID"
    LOW = "LOW"


@dataclass
class SymbolGroupInfo:
    symbol: str
    market: str
    quote_volume_24h: float
    group: VolumeGroup
    threshold_pct: float


class VolumeGrouper:
    SPOT_MIN_VOLUME = 500_000
    SPOT_MID_VOLUME_THRESHOLD = 10_000_000
    SPOT_HIGH_VOLUME_THRESHOLD = 100_000_000

    FUTURES_MIN_VOLUME = 500_000
    FUTURES_MID_VOLUME_THRESHOLD = 10_000_000
    FUTURES_HIGH_VOLUME_THRESHOLD = 200_000_000

    def __init__(self, refresh_interval: int = 600):
        self.refresh_interval = refresh_interval
        self.last_refresh: float = 0
        self.spot_groups: Dict[str, SymbolGroupInfo] = {}
        self.futures_groups: Dict[str, SymbolGroupInfo] = {}
        self.spot_thresholds = {
            VolumeGroup.HIGH: 2.5,
            VolumeGroup.MID: 6.0,
            VolumeGroup.LOW: 10.0,
        }
        self.futures_thresholds = {
            VolumeGroup.HIGH: 4.0,
            VolumeGroup.MID: 10.0,
            VolumeGroup.LOW: 20.0,
        }
        logger.info(
            f"Initialized VolumeGrouper (refresh_interval={refresh_interval}s, "
            f"spot_thresholds={self.spot_thresholds}, futures_thresholds={self.futures_thresholds})"
        )

    async def refresh_groups(self, spot_tickers: List[dict], futures_tickers: List[dict]):
        try:
            self.spot_groups = self._calculate_groups(spot_tickers, "spot")
            self.futures_groups = self._calculate_groups(futures_tickers, "futures")
            self.last_refresh = time.time()
            logger.info(
                f"Groups refreshed: {len(self.spot_groups)} spot symbols, "
                f"{len(self.futures_groups)} futures symbols"
            )
            self._log_group_distribution()
        except Exception as e:
            logger.error(f"Failed to refresh groups: {e}", exc_info=True)

    def _calculate_groups(self, tickers: List[dict], market: str) -> Dict[str, SymbolGroupInfo]:
        if not tickers:
            logger.warning(f"No tickers provided for {market} grouping")
            return {}

        if market == "spot":
            min_volume = self.SPOT_MIN_VOLUME
            mid_threshold = self.SPOT_MID_VOLUME_THRESHOLD
            high_threshold = self.SPOT_HIGH_VOLUME_THRESHOLD
            alert_thresholds = self.spot_thresholds
        else:
            min_volume = self.FUTURES_MIN_VOLUME
            mid_threshold = self.FUTURES_MID_VOLUME_THRESHOLD
            high_threshold = self.FUTURES_HIGH_VOLUME_THRESHOLD
            alert_thresholds = self.futures_thresholds

        groups = {}
        for ticker in tickers:
            symbol = ticker["symbol"]
            volume = float(ticker["quoteVolume"])
            if volume < min_volume:
                continue

            if volume > high_threshold:
                group = VolumeGroup.HIGH
            elif volume > mid_threshold:
                group = VolumeGroup.MID
            else:
                group = VolumeGroup.LOW

            groups[symbol] = SymbolGroupInfo(
                symbol=symbol,
                market=market,
                quote_volume_24h=volume,
                group=group,
                threshold_pct=alert_thresholds[group],
            )

        return groups

    def _log_group_distribution(self):
        spot_high = sum(1 for g in self.spot_groups.values() if g.group == VolumeGroup.HIGH)
        spot_mid = sum(1 for g in self.spot_groups.values() if g.group == VolumeGroup.MID)
        spot_low = sum(1 for g in self.spot_groups.values() if g.group == VolumeGroup.LOW)
        futures_high = sum(1 for g in self.futures_groups.values() if g.group == VolumeGroup.HIGH)
        futures_mid = sum(1 for g in self.futures_groups.values() if g.group == VolumeGroup.MID)
        futures_low = sum(1 for g in self.futures_groups.values() if g.group == VolumeGroup.LOW)

        logger.info(f"Spot distribution: HIGH={spot_high}, MID={spot_mid}, LOW={spot_low}")
        logger.info(f"Futures distribution: HIGH={futures_high}, MID={futures_mid}, LOW={futures_low}")

    def get_group_info(self, symbol: str, market: str) -> Optional[SymbolGroupInfo]:
        groups = self.spot_groups if market == "spot" else self.futures_groups
        return groups.get(symbol)

    def get_all_symbols(self, market: str) -> List[str]:
        groups = self.spot_groups if market == "spot" else self.futures_groups
        return list(groups.keys())

    def update_spot_thresholds(self, high: float, mid: float, low: float):
        self.spot_thresholds[VolumeGroup.HIGH] = high
        self.spot_thresholds[VolumeGroup.MID] = mid
        self.spot_thresholds[VolumeGroup.LOW] = low
        logger.info(f"Updated spot thresholds: HIGH={high}%, MID={mid}%, LOW={low}%")

    def update_futures_thresholds(self, high: float, mid: float, low: float):
        self.futures_thresholds[VolumeGroup.HIGH] = high
        self.futures_thresholds[VolumeGroup.MID] = mid
        self.futures_thresholds[VolumeGroup.LOW] = low
        logger.info(f"Updated futures thresholds: HIGH={high}%, MID={mid}%, LOW={low}%")
