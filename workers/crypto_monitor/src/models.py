from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AlertLevel(Enum):
    P1 = "P1"      # Critical
    P2 = "P2"      # Warning
    INFO = "INFO"  # Informational


class StrategyType(Enum):
    CHANGE_3M = "3m变化"    # 3-minute price change alert
    HEARTBEAT = "日报"       # Daily heartbeat report


@dataclass
class AlertMessage:
    level: AlertLevel
    symbol: str
    strategy: StrategyType
    message: str
    target_chat_id: str | None = None
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    def format_for_telegram(self) -> str:
        prefix_map = {
            AlertLevel.P1: "🚨",
            AlertLevel.P2: "⚠️",
            AlertLevel.INFO: "ℹ️"
        }
        prefix = prefix_map.get(self.level, "ℹ️")
        return f"{prefix} [{self.strategy.value}] {self.symbol}: {self.message}"
