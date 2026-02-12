import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AlertSettings:
    """Alert-related settings"""
    cooldown_seconds: int = 3600           # Default 1 hour cooldown
    max_batch_size: int = 10               # Max messages per batch
    batch_window_seconds: float = 2.0      # Aggregation window


@dataclass
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    password: str | None = None
    db: int = 0
    decode_responses: bool = True


@dataclass
class TelegramConfig:
    bot_token: str = ""
    chat_id: str = ""
    admin_id: str | None = None


@dataclass
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(levelname)s - %(message)s"

    @property
    def log_level_int(self) -> int:
        level_map = {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50
        }
        return level_map.get(self.level.upper(), 20)


@dataclass
class BinanceConfig:
    spot_api: str = "https://api.binance.com/api/v3/ticker/24hr"
    futures_api: str = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    ws_url: str = "wss://stream.binance.com:9443"
    futures_ws_url: str = "wss://fstream.binance.com/ws"


@dataclass
class Change3MConfig:
    """Configuration for 3-minute change alert system"""
    enabled: bool = True
    scan_interval_seconds: int = 60
    group_refresh_seconds: int = 600
    max_concurrent_requests: int = 20
    thresholds: dict = field(default_factory=lambda: {
        # Spot market thresholds
        "spot_high": 3.0,
        "spot_mid": 8.0,
        "spot_low": 15.0,
        # Futures market thresholds
        "futures_high": 5.0,
        "futures_mid": 15.0,
        "futures_low": 30.0
    })


class Config:
    _instance: Optional["Config"] = None

    def __new__(cls) -> "Config":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        self._alerts = AlertSettings()
        self._redis = RedisConfig()
        self._telegram = TelegramConfig()
        self._logging = LoggingConfig()
        self._binance = BinanceConfig()
        self._change3m = Change3MConfig()

        self._load_from_env()
        self._load_from_yaml()
        self._validate()

        self._initialized = True

    def _load_from_env(self) -> None:
        self._redis.host = os.getenv("REDIS_HOST", self._redis.host)
        self._redis.port = int(os.getenv("REDIS_PORT", str(self._redis.port)))
        self._redis.password = os.getenv("REDIS_PASSWORD") or None
        self._redis.db = int(os.getenv("REDIS_DB", str(self._redis.db)))

        self._telegram.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self._telegram.chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        self._telegram.admin_id = os.getenv("TELEGRAM_ADMIN_ID") or None

        self._logging.level = os.getenv("LOG_LEVEL", self._logging.level)

    def _load_from_yaml(self) -> None:
        config_dir = Path(__file__).parent.parent / "config"
        thresholds_file = config_dir / "thresholds.yaml"

        if thresholds_file.exists():
            try:
                with open(thresholds_file) as f:
                    data = yaml.safe_load(f) or {}

                # Load alert settings
                if "alerts" in data:
                    alerts = data["alerts"]
                    self._alerts.cooldown_seconds = alerts.get("cooldown_seconds", self._alerts.cooldown_seconds)
                    self._alerts.max_batch_size = alerts.get("max_batch_size", self._alerts.max_batch_size)
                    self._alerts.batch_window_seconds = alerts.get("batch_window_seconds", self._alerts.batch_window_seconds)

                # Load 3-minute change alert settings
                if "change3m_alert" in data:
                    c3m = data["change3m_alert"]
                    self._change3m.enabled = c3m.get("enabled", self._change3m.enabled)
                    self._change3m.scan_interval_seconds = c3m.get("scan_interval_seconds", self._change3m.scan_interval_seconds)
                    self._change3m.group_refresh_seconds = c3m.get("group_refresh_seconds", self._change3m.group_refresh_seconds)
                    self._change3m.max_concurrent_requests = c3m.get("max_concurrent_requests", self._change3m.max_concurrent_requests)

                    if "thresholds" in c3m:
                        thresholds = c3m["thresholds"]
                        # Spot thresholds
                        self._change3m.thresholds["spot_high"] = thresholds.get("spot_high", 3.0)
                        self._change3m.thresholds["spot_mid"] = thresholds.get("spot_mid", 8.0)
                        self._change3m.thresholds["spot_low"] = thresholds.get("spot_low", 15.0)
                        # Futures thresholds
                        self._change3m.thresholds["futures_high"] = thresholds.get("futures_high", 5.0)
                        self._change3m.thresholds["futures_mid"] = thresholds.get("futures_mid", 15.0)
                        self._change3m.thresholds["futures_low"] = thresholds.get("futures_low", 30.0)

            except Exception as e:
                print(f"Warning: Failed to load thresholds.yaml: {e}")

    def _validate(self) -> None:
        if not self._telegram.bot_token:
            print("Warning: TELEGRAM_BOT_TOKEN not set, alerts will be disabled")
        if not self._telegram.chat_id:
            print("Warning: TELEGRAM_CHAT_ID not set, alerts will be disabled")

    @property
    def alerts(self) -> AlertSettings:
        return self._alerts

    # Keep thresholds property for backward compatibility
    @property
    def thresholds(self) -> AlertSettings:
        return self._alerts

    @property
    def redis(self) -> RedisConfig:
        return self._redis

    @property
    def telegram(self) -> TelegramConfig:
        return self._telegram

    @property
    def logging(self) -> LoggingConfig:
        return self._logging

    @property
    def binance(self) -> BinanceConfig:
        return self._binance

    @property
    def change3m(self) -> Change3MConfig:
        return self._change3m


config = Config()
