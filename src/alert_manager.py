"""Reliable Telegram delivery and alert cooldown management."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import aiohttp
import orjson
from colorama import Fore

from .config import config
from .models import AlertLevel, StrategyType

if TYPE_CHECKING:
    from .redis_manager import RedisManager

logger = logging.getLogger("coinsignal.alert")
COOLDOWN_REDIS_KEY = "coinsignal:alert_cooldowns"
TELEGRAM_MESSAGE_LIMIT = 4096
TELEGRAM_BATCH_LIMIT = 3900


@dataclass(slots=True)
class QueuedMessage:
    message: str
    chat_id: str
    result: asyncio.Future[bool]


class AlertManager:
    def __init__(self) -> None:
        self.last_alert_time: dict[str, float] = {}
        self.client_session: aiohttp.ClientSession | None = None
        self.queue: asyncio.Queue[QueuedMessage] = asyncio.Queue(maxsize=100)
        self.worker_task: asyncio.Task[None] | None = None
        self._cooldown_enabled = True
        self._redis: RedisManager | None = None
        self._http_semaphore = asyncio.Semaphore(3)

    async def init_session(self) -> None:
        if not config.telegram.enabled:
            return

        if self.client_session is None or self.client_session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=5)
            connector = aiohttp.TCPConnector(
                limit=20,
                limit_per_host=10,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )
            self.client_session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
            )

        if self.worker_task is None or self.worker_task.done():
            self.worker_task = asyncio.create_task(
                self._worker(),
                name="coinsignal-telegram-worker",
            )

    async def close(self) -> None:
        if self.worker_task is not None:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None

        while not self.queue.empty():
            item = self.queue.get_nowait()
            if not item.result.done():
                item.result.set_result(False)
            self.queue.task_done()

        if self.client_session is not None:
            await self.client_session.close()
            self.client_session = None

    async def send_alert(
        self,
        level: AlertLevel,
        symbol: str,
        strategy: StrategyType,
        message: str,
        target_chat_id: str | None = None,
        bypass_cooldown: bool = False,
    ) -> bool:
        alert_key = f"{symbol}_{strategy.value}"
        if self._cooldown_enabled and not bypass_cooldown and self.is_in_cooldown(alert_key):
            return False

        log_color = Fore.RED if level == AlertLevel.P1 else Fore.YELLOW
        full_message = self._format_message(level, strategy, symbol, message)
        timestamp = time.strftime("%H:%M:%S")
        print(f"{log_color}[{timestamp}] [{level.value}] [{strategy.value}] {symbol}")

        chat_id = target_chat_id or config.telegram.chat_id
        delivered = await self._enqueue_and_wait(full_message, chat_id)
        if delivered and self._cooldown_enabled and not bypass_cooldown:
            await self.record_cooldown(alert_key)
        return delivered

    async def send_json_alert(
        self,
        alert_data: dict[str, Any],
        *,
        telegram_enabled: bool,
    ) -> bool:
        try:
            logger.info("ALERT_JSON: %s", orjson.dumps(alert_data).decode("utf-8"))
        except (TypeError, orjson.JSONEncodeError) as exc:
            logger.error("Failed to serialize alert: %s", exc)
            return False

        if not telegram_enabled:
            return True

        message = self._format_json_alert_for_telegram(alert_data)
        return await self._enqueue_and_wait(message, config.telegram.chat_id)

    async def _enqueue_and_wait(self, message: str, chat_id: str) -> bool:
        if not config.telegram.enabled or not config.telegram.bot_token or not chat_id:
            logger.error("Telegram delivery requested without an enabled destination")
            return False

        await self.init_session()
        result = asyncio.get_running_loop().create_future()
        queued_message = QueuedMessage(
            message=message,
            chat_id=chat_id,
            result=result,
        )

        try:
            await asyncio.wait_for(self.queue.put(queued_message), timeout=5)
            return await asyncio.wait_for(
                asyncio.shield(result),
                timeout=config.telegram.delivery_timeout_seconds,
            )
        except TimeoutError:
            logger.error("Telegram delivery timed out")
            if not result.done():
                result.cancel()
            return False
        except asyncio.CancelledError:
            if not result.done():
                result.cancel()
            raise

    def _format_message(
        self,
        level: AlertLevel,
        strategy: StrategyType,
        symbol: str,
        message: str,
    ) -> str:
        prefix = {
            AlertLevel.P1: "🚨",
            AlertLevel.P2: "⚠️",
            AlertLevel.INFO: "💬",
        }.get(level, "💬")
        return f"{prefix} [{strategy.value}] {symbol}: {message}"

    def _format_json_alert_for_telegram(self, alert_data: dict[str, Any]) -> str:
        symbol = alert_data.get("symbol", "UNKNOWN")
        market = str(alert_data.get("market", "unknown")).upper()
        change = float(alert_data.get("change3mPct", 0))
        direction = alert_data.get("direction", "N/A")
        group = alert_data.get("volumeGroup", "N/A")
        volume = float(alert_data.get("quoteVolume24h", 0))
        emoji = "🔺" if direction == "UP" else "🔻"
        volume_text = f"${volume / 1e9:.1f}B" if volume >= 1e9 else f"${volume / 1e6:.1f}M"

        return (
            f"{emoji} <b>3 分钟变化预警</b>\n"
            "━━━━━━━━━━━━━━━━\n"
            f"交易对: {symbol} ({market})\n"
            f"变化幅度: {change:+.2f}%\n"
            f"方向: {direction}\n"
            "━━━━━━━━━━━━━━━━\n"
            f"24h 成交额: {volume_text}\n"
            f"分组: {group}"
        )

    async def _worker(self) -> None:
        logger.info("Telegram delivery worker started")
        pending: QueuedMessage | None = None

        while True:
            batch: list[QueuedMessage] = []
            try:
                first = pending or await self.queue.get()
                pending = None
                batch.append(first)
                batch_length = len(first.message)

                while len(batch) < config.alerts.max_batch_size:
                    try:
                        next_item = await asyncio.wait_for(
                            self.queue.get(),
                            timeout=config.alerts.batch_window_seconds,
                        )
                    except TimeoutError:
                        break

                    projected_length = batch_length + len(next_item.message) + 2
                    if (
                        next_item.chat_id != first.chat_id
                        or projected_length > TELEGRAM_BATCH_LIMIT
                    ):
                        pending = next_item
                        break

                    batch.append(next_item)
                    batch_length = projected_length

                delivered = await self._send_telegram(
                    "\n\n".join(item.message for item in batch),
                    first.chat_id,
                )
                for item in batch:
                    if not item.result.done():
                        item.result.set_result(delivered)
                    self.queue.task_done()

            except asyncio.CancelledError:
                for item in batch:
                    if not item.result.done():
                        item.result.set_result(False)
                    self.queue.task_done()
                if pending is not None and not pending.result.done():
                    pending.result.set_result(False)
                raise
            except Exception:
                logger.exception("Unexpected Telegram worker failure")
                for item in batch:
                    if not item.result.done():
                        item.result.set_result(False)
                    self.queue.task_done()
                await asyncio.sleep(1)

    async def _send_telegram(self, message: str, chat_id: str) -> bool:
        if self.client_session is None:
            raise RuntimeError("Telegram session is not initialized")

        if len(message) > TELEGRAM_MESSAGE_LIMIT:
            message = message[: TELEGRAM_MESSAGE_LIMIT - 20] + "\n... (truncated)"

        url = f"https://api.telegram.org/bot{config.telegram.bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        async with self._http_semaphore:
            for attempt in range(1, config.telegram.max_attempts + 1):
                try:
                    async with self.client_session.post(url, json=payload) as response:
                        if response.status == 200:
                            return True

                        response_text = await response.text()
                        if response.status == 429:
                            retry_after = await self._read_retry_after(response)
                            logger.warning(
                                "Telegram rate limited delivery; retrying in %ss",
                                retry_after,
                            )
                            if attempt < config.telegram.max_attempts:
                                await asyncio.sleep(retry_after)
                                continue

                        if 500 <= response.status < 600:
                            logger.warning(
                                "Telegram HTTP %s on attempt %s/%s",
                                response.status,
                                attempt,
                                config.telegram.max_attempts,
                            )
                            if attempt < config.telegram.max_attempts:
                                await asyncio.sleep(min(2 ** (attempt - 1), 8))
                                continue

                        logger.error(
                            "Telegram delivery failed: HTTP %s: %s",
                            response.status,
                            response_text[:200],
                        )
                        return False
                except (TimeoutError, aiohttp.ClientError) as exc:
                    logger.warning(
                        "Telegram request failed on attempt %s/%s: %s",
                        attempt,
                        config.telegram.max_attempts,
                        type(exc).__name__,
                    )
                    if attempt < config.telegram.max_attempts:
                        await asyncio.sleep(min(2 ** (attempt - 1), 8))
                        continue
                    return False

        return False

    async def _read_retry_after(self, response: aiohttp.ClientResponse) -> int:
        try:
            payload = await response.json(content_type=None)
            value = int(payload.get("parameters", {}).get("retry_after", 1))
            return max(1, min(value, 60))
        except (TypeError, ValueError, aiohttp.ContentTypeError):
            return 1

    def is_in_cooldown(self, alert_key: str, now: float | None = None) -> bool:
        last_alert = self.last_alert_time.get(alert_key)
        if last_alert is None:
            return False
        return (now or time.time()) - last_alert < config.alerts.cooldown_seconds

    async def record_cooldown(
        self,
        alert_key: str,
        timestamp: float | None = None,
    ) -> None:
        recorded_at = timestamp or time.time()
        self.last_alert_time[alert_key] = recorded_at
        await self._persist_cooldown(alert_key, recorded_at)

    def set_cooldown_enabled(self, enabled: bool) -> None:
        self._cooldown_enabled = enabled

    def clear_cooldowns(self) -> None:
        self.last_alert_time.clear()
        logger.info("In-memory cooldowns cleared")

    def set_redis(self, redis_manager: RedisManager) -> None:
        self._redis = redis_manager

    async def load_cooldowns_from_redis(self) -> None:
        if self._redis is None or self._redis.redis is None:
            return
        try:
            data = await self._redis.redis.hgetall(COOLDOWN_REDIS_KEY)
            now = time.time()
            for key, raw_timestamp in data.items():
                timestamp = float(raw_timestamp)
                if now - timestamp < config.alerts.cooldown_seconds:
                    self.last_alert_time[str(key)] = timestamp
            logger.info(
                "Loaded %s active cooldowns from Redis",
                len(self.last_alert_time),
            )
        except Exception as exc:
            logger.warning("Failed to load cooldowns from Redis: %s", exc)

    async def _persist_cooldown(self, alert_key: str, timestamp: float) -> None:
        if self._redis is None or self._redis.redis is None:
            return
        try:
            await self._redis.redis.hset(
                COOLDOWN_REDIS_KEY,
                alert_key,
                str(timestamp),
            )
        except Exception as exc:
            logger.warning("Failed to persist cooldown %s: %s", alert_key, exc)
