from enum import Enum


class AlertLevel(Enum):
    P1 = "P1"
    P2 = "P2"
    INFO = "INFO"


class StrategyType(Enum):
    CHANGE_3M = "3m变化"
    HEARTBEAT = "心跳"
