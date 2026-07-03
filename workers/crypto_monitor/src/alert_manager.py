import asyncio
import logging
import time
from typing import Optional, TYPE_CHECKING

import aiohttp
from colorama import Fore

from config import config
from models import AlertLevel, StrategyType

if TYPE_CHECKING:
    from redis_manager import RedisManager

logger = logging.getLogger("cexMonitor.alert")
COOLDOWN_REDIS_KEY = "alert_cooldowns"


class TelegramRateLimitError(Exception):
    pass


class AlertManager:
    def __init__(self) -> None:
        self.last_alert_time: dict[str, float] = {}
        self.client_session: aiohttp.ClientSession | None = None
        self.queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue(maxsize=100)
        self.worker_task: asyncio.Task | None = None
        self._cooldown_enabled: bool = True
        self._redis: Optional["RedisManager"] = None
        self._http_semaphore = asyncio.Semaphore(3)

    async def init_session(self) -> None:
        if not self.client_session:
            timeout = aiohttp.ClientTimeout(total=10, connect=3)
            connector = aiohttp.TCPConnector(
                limit=20,
                limit_per_host=10,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True,
            )
            self.client_session = aiohttp.ClientSession(timeout=timeout, connector=connector)

        if not self.worker_task:
            self.worker_task = asyncio.create_task(self._worker())

    async def close(self) -> None:
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

        if self.client_session:
            await self.client_session.close()

    async def send_alert(
        self,
        level: AlertLevel,
        symbol: str,
        strategy: StrategyType,
        message: str,
        target_chat_id: str | None = None,
        bypass_cooldown: bool = False,
    ) -> bool:
        if self._cooldown_enabled and not bypass_cooldown:
            alert_key = f"{symbol}_{strategy.value}"
            current_time = time.time()
            cooldown = config.alerts.cooldown_seconds

            if alert_key in self.last_alert_time:
                if current_time - self.last_alert_time[alert_key] < cooldown:
                    return False

            self.last_alert_time[alert_key] = current_time
            asyncio.create_task(self._persist_cooldown(alert_key, current_time))

        log_color = Fore.RED if level == AlertLevel.P1 else Fore.YELLOW
        full_msg = self._format_message(level, strategy, symbol, message)
        timestamp = time.strftime("%H:%M:%S")
        print(f"{log_color}[{timestamp}] [{level.value}] [{strategy.value}] {symbol}")

        chat_id = target_chat_id or config.telegram.chat_id
        if config.telegram.bot_token and chat_id:
            await self.init_session()
            await self.queue.put((full_msg, chat_id))
            return True

        return False

    def _format_message(
        self,
        level: AlertLevel,
        strategy: StrategyType,
        symbol: str,
        message: str,
    ) -> str:
        prefix_map = {
            AlertLevel.P1: "🚨",
            AlertLevel.P2: "⚠️",
            AlertLevel.INFO: "ℹ️",
        }
        prefix = prefix_map.get(level, "ℹ️")
        return f"{prefix} [{strategy.value}] {symbol}: {message}"

    async def send_json_alert(self, alert_data: dict, telegram_enabled: bool = False) -> bool:
        try:
            import orjson

            json_str = orjson.dumps(alert_data).decode("utf-8")
            logger.info(f"ALERT_JSON: {json_str}")

            if telegram_enabled and config.telegram.bot_token and config.telegram.chat_id:
                msg = self._format_json_alert_for_telegram(alert_data)
                await self.init_session()
                await self.queue.put((msg, config.telegram.chat_id))

            return True
        except Exception as e:
            logger.error(f"Error sending JSON alert: {e}")
            return False

    def _format_json_alert_for_telegram(self, alert_data: dict) -> str:
        symbol = alert_data.get("symbol", "UNKNOWN")
        market = alert_data.get("market", "unknown").upper()
        change = alert_data.get("change3mPct", 0)
        direction = alert_data.get("direction", "N/A")
        group = alert_data.get("volumeGroup", "N/A")
        volume = alert_data.get("quoteVolume24h", 0)
        emoji = "🔺" if direction == "UP" else "🔻"
        v_str = f"${volume/1e9:.1f}B" if volume >= 1e9 else f"${volume/1e6:.1f}M"

        return (
            f"{emoji} <b>3分钟变化预警</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"交易对: {symbol} ({market})\n"
            f"变化幅度: {change:+.2f}%\n"
            f"方向: {direction}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"24h成交额: {v_str}\n"
            f"分组: {group}"
        )

    async def _worker(self) -> None:
        logger.info("Alert Worker Started")
        pending_msg: tuple[str, str] | None = None
        max_batch = config.alerts.max_batch_size
        batch_window = config.alerts.batch_window_seconds

        while True:
            try:
                if pending_msg:
                    msg, current_chat_id = pending_msg
                    pending_msg = None
                else:
                    msg, current_chat_id = await self.queue.get()

                batch = [msg]

                try:
                    while len(batch) < max_batch:
                        if self.queue.empty():
                            next_msg, next_chat_id = await asyncio.wait_for(self.queue.get(), timeout=batch_window)
                        else:
                            next_msg, next_chat_id = self.queue.get_nowait()

                        if next_chat_id == current_chat_id:
                            batch.append(next_msg)
                        else:
                            pending_msg = (next_msg, next_chat_id)
                            break
                except (TimeoutError, asyncio.QueueEmpty):
                    pass

                success = await self._send_telegram("\n\n".join(batch), current_chat_id)
                await asyncio.sleep(2.0 if success else 10.0)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker Error: {e}")
                await asyncio.sleep(1)
                pending_msg = None

    async def _send_telegram(self, message: str, chat_id: str) -> bool:
        if not self.client_session:
            await self.init_session()

        url = f"https://api.telegram.org/bot{config.telegram.bot_token}/sendMessage"
        if len(message) > 4000:
            message = message[:4000] + "\n... (Truncated)"

        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML",
        }

        async with self._http_semaphore:
            try:
                async with self.client_session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        return True
                    if resp.status == 429:
                        logger.warning("Telegram Rate Limit (429)! Cooling down...")
                        raise TelegramRateLimitError("Rate limited by Telegram")

                    logger.error(f"Failed to send Telegram: HTTP {resp.status}")
                    return False
            except TelegramRateLimitError:
                raise
            except Exception as e:
                logger.error(f"Error sending Telegram: {type(e).__name__}")
                return False

    def set_cooldown_enabled(self, enabled: bool) -> None:
        self._cooldown_enabled = enabled

    def clear_cooldowns(self) -> None:
        self.last_alert_time.clear()
        logger.info("All cooldowns cleared")

    def set_redis(self, redis_manager: "RedisManager") -> None:
        self._redis = redis_manager

    async def load_cooldowns_from_redis(self) -> None:
        if not self._redis or not self._redis.redis:
            return
        try:
            data = await self._redis.redis.hgetall(COOLDOWN_REDIS_KEY)
            if data:
                now = time.time()
                cooldown = config.alerts.cooldown_seconds
                for key, ts_str in data.items():
                    ts = float(ts_str)
                    if now - ts < cooldown:
                        self.last_alert_time[key] = ts
                logger.info(f"Loaded {len(self.last_alert_time)} active cooldowns from Redis")
        except Exception as e:
            logger.warning(f"Failed to load cooldowns from Redis (non-fatal): {e}")

    async def _persist_cooldown(self, alert_key: str, timestamp: float) -> None:
        if not self._redis or not self._redis.redis:
            return
        try:
            await self._redis.redis.hset(COOLDOWN_REDIS_KEY, alert_key, str(timestamp))
        except Exception:
            pass