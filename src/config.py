"""Application configuration loaded from .env and YAML."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

import yaml
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be true or false")


@dataclass(slots=True)
class AlertSettings:
    cooldown_seconds: int = 7200
    max_batch_size: int = 10
    batch_window_seconds: float = 2.0


@dataclass(slots=True)
class RedisConfig:
    host: str = "localhost"
    port: int = 6379
    password: str | None = None
    db: int = 0
    decode_responses: bool = True


@dataclass(slots=True)
class TelegramConfig:
    enabled: bool = True
    bot_token: str = ""
    chat_id: str = ""
    admin_id: str | None = None
    max_attempts: int = 4
    delivery_timeout_seconds: float = 90.0


@dataclass(slots=True)
class LoggingConfig:
    level: str = "INFO"
    format: str = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"

    @property
    def log_level_int(self) -> int:
        return {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }[self.level.upper()]


@dataclass(slots=True)
class Change3MConfig:
    scan_interval_seconds: int = 60
    group_refresh_seconds: int = 600
    max_concurrent_requests: int = 20
    thresholds: dict[str, float] = field(
        default_factory=lambda: {
            "spot_high": 2.5,
            "spot_mid": 6.0,
            "spot_low": 10.0,
            "futures_high": 4.0,
            "futures_mid": 10.0,
            "futures_low": 20.0,
        }
    )


class Config:
    _instance: ClassVar[Config | None] = None

    def __new__(cls) -> Config:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
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

        self._telegram.enabled = _env_bool("TELEGRAM_ENABLED", True)
        self._telegram.bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        self._telegram.chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
        self._telegram.admin_id = os.getenv("TELEGRAM_ADMIN_ID", "").strip() or None
        self._telegram.max_attempts = int(
            os.getenv("TELEGRAM_MAX_ATTEMPTS", str(self._telegram.max_attempts))
        )
        self._telegram.delivery_timeout_seconds = float(
            os.getenv(
                "TELEGRAM_DELIVERY_TIMEOUT_SECONDS",
                str(self._telegram.delivery_timeout_seconds),
            )
        )
        self._logging.level = os.getenv("LOG_LEVEL", self._logging.level).upper()

    def _load_from_yaml(self) -> None:
        thresholds_file = PROJECT_ROOT / "config" / "thresholds.yaml"
        if not thresholds_file.exists():
            raise FileNotFoundError(f"Missing configuration file: {thresholds_file}")

        try:
            with thresholds_file.open(encoding="utf-8") as file_handle:
                data: dict[str, Any] = yaml.safe_load(file_handle) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise RuntimeError(f"Failed to load {thresholds_file}: {exc}") from exc

        alerts = data.get("alerts", {})
        self._alerts.cooldown_seconds = int(
            alerts.get("cooldown_seconds", self._alerts.cooldown_seconds)
        )
        self._alerts.max_batch_size = int(alerts.get("max_batch_size", self._alerts.max_batch_size))
        self._alerts.batch_window_seconds = float(
            alerts.get("batch_window_seconds", self._alerts.batch_window_seconds)
        )

        change_config = data.get("change3m_alert", {})
        self._change3m.scan_interval_seconds = int(
            change_config.get("scan_interval_seconds", self._change3m.scan_interval_seconds)
        )
        self._change3m.group_refresh_seconds = int(
            change_config.get("group_refresh_seconds", self._change3m.group_refresh_seconds)
        )
        self._change3m.max_concurrent_requests = int(
            change_config.get(
                "max_concurrent_requests",
                self._change3m.max_concurrent_requests,
            )
        )
        self._change3m.thresholds.update(
            {key: float(value) for key, value in change_config.get("thresholds", {}).items()}
        )

    def _validate(self) -> None:
        if self._telegram.enabled:
            missing = [
                name
                for name, value in (
                    ("TELEGRAM_BOT_TOKEN", self._telegram.bot_token),
                    ("TELEGRAM_CHAT_ID", self._telegram.chat_id),
                )
                if not value
            ]
            if missing:
                raise ValueError(
                    "Telegram delivery is enabled but required variables are missing: "
                    + ", ".join(missing)
                    + ". Set TELEGRAM_ENABLED=false for explicit log-only mode."
                )

        if self._logging.level not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Unsupported LOG_LEVEL: {self._logging.level}")
        if not 1 <= self._redis.port <= 65535:
            raise ValueError("REDIS_PORT must be between 1 and 65535")
        if self._redis.db < 0:
            raise ValueError("REDIS_DB must be non-negative")
        if self._alerts.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative")
        if self._alerts.max_batch_size < 1:
            raise ValueError("max_batch_size must be at least 1")
        if self._alerts.batch_window_seconds < 0:
            raise ValueError("batch_window_seconds must be non-negative")
        if self._change3m.scan_interval_seconds < 1:
            raise ValueError("scan_interval_seconds must be at least 1")
        if self._change3m.group_refresh_seconds < 1:
            raise ValueError("group_refresh_seconds must be at least 1")
        if self._change3m.max_concurrent_requests < 1:
            raise ValueError("max_concurrent_requests must be at least 1")
        if any(value <= 0 for value in self._change3m.thresholds.values()):
            raise ValueError("Every change threshold must be greater than zero")
        if self._telegram.max_attempts < 1:
            raise ValueError("TELEGRAM_MAX_ATTEMPTS must be at least 1")
        if self._telegram.delivery_timeout_seconds <= 0:
            raise ValueError("TELEGRAM_DELIVERY_TIMEOUT_SECONDS must be positive")

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
