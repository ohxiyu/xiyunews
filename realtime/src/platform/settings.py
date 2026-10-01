"""Explicit deployment settings, separate from the legacy scanner."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def flag(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).lower()
    if value not in {"true", "false", "1", "0"}:
        raise ValueError(f"Invalid boolean: {name}")
    return value in {"true", "1"}


@dataclass
class Settings:
    database: str = field(default_factory=lambda: os.getenv("FOMOBTC_DB", "data/fomobtc.sqlite3"))
    host: str = field(default_factory=lambda: os.getenv("API_HOST", "127.0.0.1"))
    port: int = field(default_factory=lambda: int(os.getenv("API_PORT", "8080")))
    telegram: bool = field(default_factory=lambda: flag("TELEGRAM_ENABLED", True))
    token: str = field(default_factory=lambda: os.getenv("TELEGRAM_BOT_TOKEN", ""))
    chat: str = field(default_factory=lambda: os.getenv("TELEGRAM_CHAT_ID", ""))
    announcement_chat: str = field(
        default_factory=lambda: os.getenv("TELEGRAM_ANNOUNCEMENT_CHAT_ID", "")
    )
    chat_interval: float = field(
        default_factory=lambda: float(os.getenv("TELEGRAM_CHAT_INTERVAL", "3.1"))
    )
    market: bool = field(default_factory=lambda: flag("MARKET_ENABLED", True))
    spot: bool = field(default_factory=lambda: flag("SPOT_ENABLED", True))
    announcements: bool = field(default_factory=lambda: flag("ANNOUNCEMENTS_ENABLED", True))
    binance_key: str = field(default_factory=lambda: os.getenv("BINANCE_ANNOUNCEMENT_API_KEY", ""))
    binance_secret: str = field(
        default_factory=lambda: os.getenv("BINANCE_ANNOUNCEMENT_API_SECRET", "")
    )
    okx_url: str = field(default_factory=lambda: os.getenv("OKX_BASE_URL", "https://www.okx.com"))
    okx_interval: float = field(default_factory=lambda: float(os.getenv("OKX_POLL_SECONDS", "6")))
    hyper_interval: float = field(
        default_factory=lambda: float(os.getenv("HYPERLIQUID_POLL_SECONDS", "15"))
    )
    revision: str = field(default_factory=lambda: os.getenv("SOURCE_COMMIT", "unknown"))
    flows: bool = field(default_factory=lambda: flag("FLOWS_ENABLED", True))
    # Forum topics (message_thread_id) in TELEGRAM_CHAT_ID; empty sends to the chat itself.
    topics: dict[str, str] = field(
        default_factory=lambda: {
            kind: os.getenv(f"TELEGRAM_TOPIC_{kind.upper()}", "").strip()
            for kind in ("market", "announcement", "flow")
        }
    )

    def validate(self) -> None:
        if self.telegram and (not self.token or not self.chat):
            raise ValueError(
                "Telegram credentials missing; explicit TELEGRAM_ENABLED=false required"
            )
        if not 1 <= self.port <= 65535 or self.chat_interval < 1:
            raise ValueError("Invalid port or Telegram interval (minimum 1 second)")
        if self.okx_interval < 5 or self.hyper_interval < 10:
            raise ValueError("Polling intervals below supported minimum")
        if self.okx_url not in {
            "https://www.okx.com",
            "https://openapi.okx.com",
            "https://us.okx.com",
            "https://eea.okx.com",
        }:
            raise ValueError("Unsupported OKX origin")


def load_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parents[2] / ".env")
    settings = Settings()
    settings.validate()
    return settings
