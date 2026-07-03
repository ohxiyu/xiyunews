import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from dotenv import load_dotenv

load_dotenv()


@dataclass
class AlertSettings:
    cooldown_seconds: int = 7200
    max_batch_size: int = 10
    batch_window_seconds: float = 2.0


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
        return {
            "DEBUG": 10,
            "INFO": 20,
            "WARNING": 30,
            "ERROR": 40,
            "CRITICAL": 50,
        }.get(self.level.upper(), 20)


@dataclass
class Change3MConfig:
    enabled: bool = True
    scan_interval_seconds: int = 60
    group_refresh_seconds: int = 600
    max_concurrent_requests: int = 20
    thresholds: dict = field(default_factory=lambda: {
        "spot_high": 2.5,
        "spot_mid": 6.0,
        "spot_low": 10.0,
        "futures_high": 4.0,
        "futures_mid": 10.0,
        "futures_low": 20.0,
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
        thresholds_file = Path(__file__).parent.parent / "config" / "thresholds.yaml"
        if not thresholds_file.exists():
            return

        try:
            with open(thresholds_file) as f:
                data = yaml.safe_load(f) or {}

            alerts = data.get("alerts", {})
            self._alerts.cooldown_seconds = alerts.get("cooldown_seconds", self._alerts.cooldown_seconds)
            self._alerts.max_batch_size = alerts.get("max_batch_size", self._alerts.max_batch_size)
            self._alerts.batch_window_seconds = alerts.get("batch_window_seconds", self._alerts.batch_window_seconds)

            c3m = data.get("change3m_alert", {})
            self._change3m.enabled = c3m.get("enabled", self._change3m.enabled)
            self._change3m.scan_interval_seconds = c3m.get("scan_interval_seconds", self._change3m.scan_interval_seconds)
            self._change3m.group_refresh_seconds = c3m.get("group_refresh_seconds", self._change3m.group_refresh_seconds)
            self._change3m.max_concurrent_requests = c3m.get("max_concurrent_requests", self._change3m.max_concurrent_requests)
            self._change3m.thresholds.update(c3m.get("thresholds", {}))
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
    def change3m(self) -> Change3MConfig:
        return self._change3m


config = Config()
