"""Group symbols by 24-hour quote volume and assign alert thresholds."""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

logger = logging.getLogger("coinsignal.volume")


class VolumeGroup(Enum):
    HIGH = "HIGH"
    MID = "MID"
    LOW = "LOW"


@dataclass(frozen=True, slots=True)
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

    def __init__(self, refresh_interval: int = 600) -> None:
        self.refresh_interval = refresh_interval
        self.last_refresh = 0.0
        self.spot_groups: dict[str, SymbolGroupInfo] = {}
        self.futures_groups: dict[str, SymbolGroupInfo] = {}
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

    async def refresh_groups(
        self,
        spot_tickers: list[dict[str, Any]],
        futures_tickers: list[dict[str, Any]],
    ) -> None:
        new_spot_groups = self._calculate_groups(spot_tickers, "spot")
        new_futures_groups = self._calculate_groups(futures_tickers, "futures")
        self.spot_groups = new_spot_groups
        self.futures_groups = new_futures_groups
        self.last_refresh = time.time()
        self._log_group_distribution()

    def _calculate_groups(
        self,
        tickers: list[dict[str, Any]],
        market: str,
    ) -> dict[str, SymbolGroupInfo]:
        if market == "spot":
            min_volume = self.SPOT_MIN_VOLUME
            mid_threshold = self.SPOT_MID_VOLUME_THRESHOLD
            high_threshold = self.SPOT_HIGH_VOLUME_THRESHOLD
            alert_thresholds = self.spot_thresholds
        elif market == "futures":
            min_volume = self.FUTURES_MIN_VOLUME
            mid_threshold = self.FUTURES_MID_VOLUME_THRESHOLD
            high_threshold = self.FUTURES_HIGH_VOLUME_THRESHOLD
            alert_thresholds = self.futures_thresholds
        else:
            raise ValueError(f"Unsupported market: {market}")

        groups: dict[str, SymbolGroupInfo] = {}
        for ticker in tickers:
            try:
                symbol = str(ticker["symbol"])
                volume = float(ticker["quoteVolume"])
            except (KeyError, TypeError, ValueError):
                logger.warning("Skipping malformed %s ticker: %r", market, ticker)
                continue

            if not symbol or volume < min_volume:
                continue
            if volume >= high_threshold:
                group = VolumeGroup.HIGH
            elif volume >= mid_threshold:
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

    def _log_group_distribution(self) -> None:
        for market, groups in (
            ("spot", self.spot_groups),
            ("futures", self.futures_groups),
        ):
            counts = {
                group: sum(1 for item in groups.values() if item.group == group)
                for group in VolumeGroup
            }
            logger.info(
                "%s distribution: HIGH=%s, MID=%s, LOW=%s",
                market.capitalize(),
                counts[VolumeGroup.HIGH],
                counts[VolumeGroup.MID],
                counts[VolumeGroup.LOW],
            )

    def _groups_for_market(self, market: str) -> dict[str, SymbolGroupInfo]:
        if market == "spot":
            return self.spot_groups
        if market == "futures":
            return self.futures_groups
        raise ValueError(f"Unsupported market: {market}")

    def get_group_info(self, symbol: str, market: str) -> SymbolGroupInfo | None:
        return self._groups_for_market(market).get(symbol)

    def get_all_symbols(self, market: str) -> list[str]:
        return list(self._groups_for_market(market))

    def update_spot_thresholds(self, high: float, mid: float, low: float) -> None:
        self._set_thresholds(self.spot_thresholds, high, mid, low)

    def update_futures_thresholds(self, high: float, mid: float, low: float) -> None:
        self._set_thresholds(self.futures_thresholds, high, mid, low)

    @staticmethod
    def _set_thresholds(
        destination: dict[VolumeGroup, float],
        high: float,
        mid: float,
        low: float,
    ) -> None:
        if min(high, mid, low) <= 0:
            raise ValueError("Alert thresholds must be greater than zero")
        destination.update(
            {
                VolumeGroup.HIGH: high,
                VolumeGroup.MID: mid,
                VolumeGroup.LOW: low,
            }
        )
