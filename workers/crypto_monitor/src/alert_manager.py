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

# Redis key for cooldown persistence
COOLDOWN_REDIS_KEY = "alert_cooldowns"


class TelegramRateLimitError(Exception):
    pass


class AlertManager:
    def __init__(self) -> None:
        self.last_alert_time: dict[str, float] = {}
        self.client_session: aiohttp.ClientSession | None = None
        self.queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue(maxsize=100)  # Bounded queue
        self.worker_task: asyncio.Task | None = None
        self._cooldown_enabled: bool = True
        self._redis: Optional["RedisManager"] = None  # 可选的 Redis 引用

        # Performance optimization: Semaphore for concurrent HTTP requests
        self._http_semaphore = asyncio.Semaphore(3)  # Max 3 concurrent requests
        self._batch_queue: asyncio.Queue[tuple[str, str]] = asyncio.Queue(maxsize=50)

    async def init_session(self) -> None:
        if not self.client_session:
            # Optimize session configuration
            timeout = aiohttp.ClientTimeout(total=10, connect=3)
            connector = aiohttp.TCPConnector(
                limit=20,
                limit_per_host=10,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            )
            self.client_session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )

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
        bypass_cooldown: bool = False
    ) -> bool:
        if self._cooldown_enabled and not bypass_cooldown:
            alert_key = f"{symbol}_{strategy.value}"
            current_time = time.time()
            cooldown = config.alerts.cooldown_seconds

            if alert_key in self.last_alert_time:
                if current_time - self.last_alert_time[alert_key] < cooldown:
                    return False

            self.last_alert_time[alert_key] = current_time
            # 异步持久化到 Redis（不阻塞）
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
        message: str
    ) -> str:
        prefix_map = {
            AlertLevel.P1: "🚨",
            AlertLevel.P2: "⚠️",
            AlertLevel.INFO: "ℹ️"
        }
        prefix = prefix_map.get(level, "ℹ️")
        return f"{prefix} [{strategy.value}] {symbol}: {message}"

    async def send_json_alert(self, alert_data: dict, telegram_enabled: bool = False) -> bool:
        """
        Send structured JSON alert.

        Args:
            alert_data: Alert data dictionary with keys: ts, market, symbol, quoteVolume24h,
                       volumeGroup, thresholdPct, change3mPct, direction, triggered
            telegram_enabled: If True, also send formatted alert to Telegram

        Returns:
            Success status

        Example:
            await alert_manager.send_json_alert({
                "ts": 1705233615,
                "market": "spot",
                "symbol": "BTCUSDT",
                "quoteVolume24h": 1234567890,
                "volumeGroup": "HIGH",
                "thresholdPct": 3,
                "change3mPct": -3.42,
                "direction": "DOWN",
                "triggered": True
            })
        """
        try:
            # Primary output: JSON to stdout/log
            import orjson
            json_str = orjson.dumps(alert_data).decode('utf-8')
            logger.info(f"ALERT_JSON: {json_str}")

            # Optional: Send to Telegram
            if telegram_enabled and config.telegram.bot_token and config.telegram.chat_id:
                msg = self._format_json_alert_for_telegram(alert_data)
                await self.init_session()
                await self.queue.put((msg, config.telegram.chat_id))

            return True

        except Exception as e:
            logger.error(f"Error sending JSON alert: {e}")
            return False

    def _format_json_alert_for_telegram(self, alert_data: dict) -> str:
        """
        Format JSON alert for Telegram readability.

        Args:
            alert_data: Alert data dictionary

        Returns:
            Formatted Telegram message with HTML markup
        """
        symbol = alert_data.get('symbol', 'UNKNOWN')
        market = alert_data.get('market', 'unknown').upper()
        change = alert_data.get('change3mPct', 0)
        direction = alert_data.get('direction', 'N/A')
        group = alert_data.get('volumeGroup', 'N/A')
        volume = alert_data.get('quoteVolume24h', 0)

        # Emoji based on direction
        emoji = "🔺" if direction == "UP" else "🔻"

        # Format volume
        if volume >= 1e9:
            v_str = f"${volume/1e9:.1f}B"
        else:
            v_str = f"${volume/1e6:.1f}M"

        msg = (
            f"{emoji} <b>3分钟变化预警</b>\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"交易对: {symbol} ({market})\n"
            f"变化幅度: {change:+.2f}%\n"
            f"方向: {direction}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"24h成交额: {v_str}\n"
            f"分组: {group}"
        )

        return msg

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
                    msg_data = await self.queue.get()
                    msg, current_chat_id = msg_data

                batch = [msg]

                try:
                    while len(batch) < max_batch:
                        if self.queue.empty():
                            msg_data = await asyncio.wait_for(self.queue.get(), timeout=batch_window)
                        else:
                            msg_data = self.queue.get_nowait()

                        next_msg, next_chat_id = msg_data

                        if next_chat_id == current_chat_id:
                            batch.append(next_msg)
                        else:
                            pending_msg = msg_data
                            break
                except (TimeoutError, asyncio.QueueEmpty):
                    pass

                final_text = "\n\n".join(batch)

                success = await self._send_telegram(final_text, current_chat_id)

                if success:
                    await asyncio.sleep(2.0)
                else:
                    await asyncio.sleep(10.0)

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
            "parse_mode": "HTML"
        }

        async with self._http_semaphore:  # Limit concurrent requests
            try:
                async with self.client_session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        return True
                    elif resp.status == 429:
                        logger.warning(f"Telegram Rate Limit (429)! Cooling down...")
                        raise TelegramRateLimitError("Rate limited by Telegram")
                    else:
                        # 脱敏处理：只记录状态码，不记录完整响应（可能包含敏感信息）
                        logger.error(f"Failed to send Telegram: HTTP {resp.status}")
                        return False
            except TelegramRateLimitError:
                raise
            except Exception as e:
                # 脱敏处理：只记录异常类型，不记录完整异常信息
                logger.error(f"Error sending Telegram: {type(e).__name__}")
                return False

    def set_cooldown_enabled(self, enabled: bool) -> None:
        self._cooldown_enabled = enabled

    def clear_cooldowns(self) -> None:
        self.last_alert_time.clear()
        logger.info("All cooldowns cleared")

    def set_redis(self, redis_manager: "RedisManager") -> None:
        """设置 Redis 引用，用于冷却时间持久化"""
        self._redis = redis_manager

    async def load_cooldowns_from_redis(self) -> None:
        """从 Redis 加载冷却时间（启动时调用，防止重启刷屏）"""
        if not self._redis or not self._redis.redis:
            return
        try:
            data = await self._redis.redis.hgetall(COOLDOWN_REDIS_KEY)
            if data:
                now = time.time()
                cooldown = config.alerts.cooldown_seconds
                # 只加载未过期的冷却记录
                for key, ts_str in data.items():
                    ts = float(ts_str)
                    if now - ts < cooldown:
                        self.last_alert_time[key] = ts
                logger.info(f"Loaded {len(self.last_alert_time)} active cooldowns from Redis")
        except Exception as e:
            logger.warning(f"Failed to load cooldowns from Redis (non-fatal): {e}")

    async def _persist_cooldown(self, alert_key: str, timestamp: float) -> None:
        """异步持久化单个冷却记录到 Redis"""
        if not self._redis or not self._redis.redis:
            return
        try:
            await self._redis.redis.hset(COOLDOWN_REDIS_KEY, alert_key, str(timestamp))
        except Exception:
            pass  # 静默失败，不影响主流程
