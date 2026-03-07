"""
Alert Engine Module

Main orchestrator for 3-minute change alert system.
Coordinates REST API clients, volume grouper, calculator, and alert manager.
"""

import asyncio
import logging
import time
from typing import Optional

from alert_manager import AlertManager
from redis_manager import RedisManager
from binance_rest_client import BinanceSpotClient, BinanceFuturesClient
from volume_grouper import VolumeGrouper
from change3m_calculator import Change3MCalculator
from config import config

logger = logging.getLogger("cexMonitor.alertEngine")


class AlertEngine:
    """
    Main orchestrator for 3-minute change alert system.

    Features:
    - Main scan loop (configurable interval, default 15s)
    - Background group refresh (configurable interval, default 600s)
    - Concurrent klines fetching with rate limiting
    - Alert generation with JSON output
    - Integration with AlertManager for Telegram notifications
    - Optional Redis persistence
    """

    def __init__(self, alert_manager: AlertManager, redis_manager: Optional[RedisManager] = None):
        """
        Initialize alert engine.

        Args:
            alert_manager: AlertManager instance for sending alerts
            redis_manager: Optional RedisManager for persistence
        """
        self.alert_manager = alert_manager
        self.redis_manager = redis_manager

        # REST API clients
        max_concurrent = config.change3m.max_concurrent_requests
        self.spot_client = BinanceSpotClient(max_concurrent=max_concurrent)
        self.futures_client = BinanceFuturesClient(max_concurrent=max_concurrent)

        # Volume grouper
        self.grouper = VolumeGrouper(refresh_interval=config.change3m.group_refresh_seconds)

        # Update grouper thresholds from config (spot uses config, futures uses hardcoded values)
        thresholds = config.change3m.thresholds
        self.grouper.update_spot_thresholds(
            high=thresholds.get("spot_high", 3.0),
            mid=thresholds.get("spot_mid", 8.0),
            low=thresholds.get("spot_low", 15.0)
        )
        self.grouper.update_futures_thresholds(
            high=thresholds.get("futures_high", 5.0),
            mid=thresholds.get("futures_mid", 15.0),
            low=thresholds.get("futures_low", 30.0)
        )

        # Calculator (stateless utility)
        self.calculator = Change3MCalculator()

        # Configuration
        self.scan_interval = config.change3m.scan_interval_seconds
        self.group_refresh_interval = config.change3m.group_refresh_seconds

        # Background tasks
        self._scan_task: Optional[asyncio.Task] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
        self._start_time = time.time()

        # Statistics
        self.stats_scans_completed = 0
        self.stats_alerts_triggered = 0
        self.stats_api_errors = 0

        # Stale data detection: track last change value per symbol
        # If change3mPct is identical across consecutive alerts, data is frozen
        self._last_change_values: dict[str, tuple[float, int]] = {}  # key -> (change_pct, repeat_count)

        logger.info(
            f"AlertEngine initialized "
            f"(scan_interval={self.scan_interval}s, "
            f"group_refresh={self.group_refresh_interval}s, "
            f"max_concurrent={max_concurrent})"
        )

    async def start(self):
        """
        Start the alert engine.

        Initializes REST clients, performs initial group refresh,
        and starts background tasks for scanning and group refresh.
        """
        logger.info("Starting Alert Engine...")

        try:
            # Initialize REST clients
            await self.spot_client.init_session()
            await self.futures_client.init_session()
            logger.info("REST API clients initialized")

            # Initial group refresh
            await self._refresh_groups()

            # Start background tasks
            self._running = True
            self._scan_task = asyncio.create_task(self._scan_loop())
            self._refresh_task = asyncio.create_task(self._refresh_loop())
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            logger.info("Alert Engine started successfully")

            # Wait for tasks (runs indefinitely)
            await asyncio.gather(self._scan_task, self._refresh_task, self._heartbeat_task)

        except Exception as e:
            logger.critical(f"Fatal error starting Alert Engine: {e}", exc_info=True)
            await self.stop()
            raise

    async def stop(self):
        """
        Stop the alert engine.

        Cancels background tasks and closes REST client sessions.
        """
        logger.info("Stopping Alert Engine...")
        self._running = False

        # Cancel background tasks
        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass

        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass

        # Close REST clients
        await self.spot_client.close()
        await self.futures_client.close()

        logger.info(
            f"Alert Engine stopped "
            f"(scans={self.stats_scans_completed}, "
            f"alerts={self.stats_alerts_triggered}, "
            f"errors={self.stats_api_errors})"
        )

    async def _refresh_loop(self):
        """
        Background task: refresh volume groups periodically.

        Runs every group_refresh_interval seconds (default: 600s = 10 minutes).
        """
        while self._running:
            try:
                await asyncio.sleep(self.group_refresh_interval)

                if not self._running:
                    break

                await self._refresh_groups()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Group refresh error: {e}", exc_info=True)
                # Continue after error with brief pause
                await asyncio.sleep(60)

    async def _refresh_groups(self):
        """
        Fetch 24hr tickers and refresh volume groups.

        Updates grouper with latest 24h quoteVolume data from both markets.
        """
        try:
            logger.info("Refreshing volume groups...")

            # Fetch tickers concurrently from both markets
            spot_tickers, futures_tickers = await asyncio.gather(
                self.spot_client.get_24hr_tickers(),
                self.futures_client.get_24hr_tickers(),
                return_exceptions=True
            )

            # Handle errors
            if isinstance(spot_tickers, Exception):
                logger.error(f"Failed to fetch spot tickers: {spot_tickers}")
                spot_tickers = []

            if isinstance(futures_tickers, Exception):
                logger.error(f"Failed to fetch futures tickers: {futures_tickers}")
                futures_tickers = []

            # Refresh groups
            await self.grouper.refresh_groups(spot_tickers, futures_tickers)

            logger.info(
                f"Groups refreshed: {len(self.grouper.spot_groups)} spot, "
                f"{len(self.grouper.futures_groups)} futures"
            )

        except Exception as e:
            logger.error(f"Failed to refresh groups: {e}", exc_info=True)
            self.stats_api_errors += 1

    async def _heartbeat_loop(self):
        """
        Background task: send heartbeat at fixed UTC times (0:00 and 12:00).

        Sends system status report to Telegram twice daily.
        """
        from datetime import datetime, timezone, timedelta

        logger.info("Heartbeat task started (scheduled for UTC 0:00 and 12:00)")

        while self._running:
            try:
                # Get current UTC time
                now_utc = datetime.now(timezone.utc)
                current_hour = now_utc.hour
                current_minute = now_utc.minute

                # Calculate next heartbeat time
                if current_hour < 12:
                    # Next heartbeat is at 12:00 today
                    next_hour = 12
                    target_time = now_utc.replace(hour=12, minute=0, second=0, microsecond=0)
                else:
                    # Next heartbeat is at 0:00 tomorrow
                    next_hour = 0
                    target_time = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

                # Calculate sleep duration
                sleep_seconds = (target_time - now_utc).total_seconds()

                logger.info(f"Next heartbeat scheduled at UTC {target_time.strftime('%Y-%m-%d %H:%M:%S')} "
                           f"(in {sleep_seconds/3600:.1f} hours)")

                # Sleep until next heartbeat time
                await asyncio.sleep(sleep_seconds)

                if not self._running:
                    break

                # Send heartbeat
                await self._send_heartbeat()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}", exc_info=True)
                # On error, retry after 5 minutes
                await asyncio.sleep(300)

    async def _send_heartbeat(self):
        """
        Send heartbeat status message to Telegram.

        Includes system uptime, scan statistics, and current monitoring status.
        """
        try:
            from datetime import datetime, timezone

            # Calculate uptime
            uptime_seconds = time.time() - self._start_time
            uptime_hours = uptime_seconds / 3600
            uptime_days = uptime_hours / 24

            # Format uptime string
            if uptime_days >= 1:
                uptime_str = f"{uptime_days:.1f} days"
            else:
                uptime_str = f"{uptime_hours:.1f} hours"

            # Get current UTC time
            current_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

            # Build heartbeat message
            message = (
                f"💚 <b>System Heartbeat</b>\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"⏰ Time: {current_time}\n"
                f"🟢 Status: <b>Online</b>\n"
                f"⏱ Uptime: {uptime_str}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📊 Statistics:\n"
                f"  • Scans: {self.stats_scans_completed:,}\n"
                f"  • Alerts: {self.stats_alerts_triggered:,}\n"
                f"  • Errors: {self.stats_api_errors:,}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"📈 Monitoring:\n"
                f"  • Spot: {len(self.grouper.spot_groups)} symbols\n"
                f"  • Futures: {len(self.grouper.futures_groups)} symbols\n"
                f"  • Total: {len(self.grouper.spot_groups) + len(self.grouper.futures_groups)} pairs\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"QweCryptoMonitor V3.0"
            )

            # Send to Telegram admin (not channel)
            from models import AlertLevel, StrategyType

            # Use admin_id if available, otherwise fallback to chat_id
            target_chat = config.telegram.admin_id or config.telegram.chat_id

            success = await self.alert_manager.send_alert(
                level=AlertLevel.INFO,
                symbol="SYSTEM",
                strategy=StrategyType.HEARTBEAT,
                message=message,
                target_chat_id=target_chat,
                bypass_cooldown=True
            )

            if success:
                logger.info(f"Heartbeat sent successfully (uptime: {uptime_str}, scans: {self.stats_scans_completed})")
            else:
                logger.warning("Failed to send heartbeat message")

        except Exception as e:
            logger.error(f"Error sending heartbeat: {e}", exc_info=True)

    async def _scan_loop(self):
        """
        Main scan loop: check all symbols periodically.

        Runs every scan_interval seconds (default: 15s).
        Scans all symbols in both spot and futures markets concurrently.
        """
        while self._running:
            try:
                scan_start = time.time()

                # Get all symbols from groups
                spot_symbols = self.grouper.get_all_symbols("spot")
                futures_symbols = self.grouper.get_all_symbols("futures")

                if not spot_symbols and not futures_symbols:
                    logger.warning("No symbols to scan, waiting for group refresh...")
                    await asyncio.sleep(self.scan_interval)
                    continue

                # Scan both markets concurrently
                await asyncio.gather(
                    self._scan_market("spot", spot_symbols),
                    self._scan_market("futures", futures_symbols),
                    return_exceptions=True
                )

                scan_duration = time.time() - scan_start
                self.stats_scans_completed += 1

                logger.debug(
                    f"Scan #{self.stats_scans_completed} completed in {scan_duration:.2f}s "
                    f"({len(spot_symbols)} spot + {len(futures_symbols)} futures symbols)"
                )

                # Wait for next scan
                await asyncio.sleep(self.scan_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scan loop error: {e}", exc_info=True)
                await asyncio.sleep(5)  # Brief pause on error

    async def _scan_market(self, market: str, symbols: list[str]):
        """
        Scan all symbols in one market.

        Args:
            market: Market type ("spot" or "futures")
            symbols: List of symbol strings to scan

        Fetches klines concurrently with rate limiting (semaphore-controlled).
        """
        if not symbols:
            return

        # Get appropriate client
        client = self.spot_client if market == "spot" else self.futures_client

        # Create tasks for all symbols
        tasks = []
        for symbol in symbols:
            task = self._check_symbol(symbol, market, client)
            tasks.append(task)

        # Wait for all checks to complete (gather with return_exceptions to prevent cascade failures)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log errors
        errors = [r for r in results if isinstance(r, Exception)]
        if errors:
            logger.debug(f"{market} scan: {len(errors)} errors out of {len(symbols)} symbols")
            self.stats_api_errors += len(errors)

    async def _check_symbol(self, symbol: str, market: str, client):
        """
        Check one symbol for 3-minute change and trigger alert if threshold exceeded.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            market: Market type ("spot" or "futures")
            client: BinanceRESTClient instance (spot or futures)

        Flow:
        1. Get group info (volume group, threshold)
        2. Fetch 4 bars of 1m klines
        3. Calculate 3-minute change
        4. Check if abs(change) >= threshold
        5. If triggered, generate and send JSON alert
        """
        try:
            # Get group info (includes threshold)
            group_info = self.grouper.get_group_info(symbol, market)
            if not group_info:
                logger.debug(f"{symbol} ({market}): not in groups")
                return

            # Fetch klines (4 bars of 1-minute data)
            klines = await client.get_klines(symbol, interval="1m", limit=4)

            if not klines or len(klines) < 4:
                logger.debug(f"{symbol} ({market}): insufficient klines (got {len(klines) if klines else 0})")
                return

            # Calculate 3-minute change
            change3mPct = self.calculator.calculate_change(klines)
            if change3mPct is None:
                return

            # Check trigger
            triggered = self.calculator.check_trigger(change3mPct, group_info.threshold_pct)

            if triggered:
                # Generate alert
                alert_data = {
                    "ts": int(time.time()),
                    "market": market,
                    "symbol": symbol,
                    "quoteVolume24h": group_info.quote_volume_24h,
                    "volumeGroup": group_info.group.value,
                    "thresholdPct": group_info.threshold_pct,
                    "change3mPct": round(change3mPct, 2),
                    "direction": self.calculator.get_direction(change3mPct),
                    "triggered": True
                }

                # Send alert
                await self._send_alert(alert_data)

        except Exception as e:
            logger.error(f"Error checking {symbol} ({market}): {e}")
            raise  # Re-raise to be caught by gather() in _scan_market

    async def _send_alert(self, alert_data: dict):
        """
        Send alert via AlertManager with cooldown mechanism.

        Outputs JSON to logger and optionally sends to Telegram.
        Implements cooldown to prevent spamming for the same symbol.

        Args:
            alert_data: Alert data dictionary
        """
        try:
            # Check cooldown to prevent repeated alerts for same symbol
            alert_key = f"{alert_data['market']}_{alert_data['symbol']}_3m"
            current_time = time.time()
            cooldown_seconds = config.alerts.cooldown_seconds  # Default: 3600s (1 hour)

            # Check if symbol is in cooldown period
            if alert_key in self.alert_manager.last_alert_time:
                time_since_last = current_time - self.alert_manager.last_alert_time[alert_key]
                if time_since_last < cooldown_seconds:
                    logger.debug(
                        f"Alert for {alert_data['symbol']} ({alert_data['market']}) suppressed "
                        f"(cooldown: {int(time_since_last)}s / {cooldown_seconds}s)"
                    )
                    return

            # Stale data detection: suppress if change3mPct is identical to last alert
            # This catches frozen/delisted coins that return the same klines repeatedly
            stale_key = f"{alert_data['market']}_{alert_data['symbol']}"
            current_change = alert_data['change3mPct']
            if stale_key in self._last_change_values:
                last_change, repeat_count = self._last_change_values[stale_key]
                if last_change == current_change:
                    repeat_count += 1
                    self._last_change_values[stale_key] = (current_change, repeat_count)
                    if repeat_count >= 2:
                        logger.info(
                            f"Stale data suppressed: {alert_data['symbol']} ({alert_data['market']}) "
                            f"change3mPct={current_change}% repeated {repeat_count} times"
                        )
                        return
                else:
                    # Value changed, reset counter
                    self._last_change_values[stale_key] = (current_change, 1)
            else:
                self._last_change_values[stale_key] = (current_change, 1)

            # Filter out low volume symbols (likely delisted or low liquidity)
            min_volume_threshold = 500000  # Minimum $500k 24h volume
            if alert_data['quoteVolume24h'] < min_volume_threshold:
                logger.debug(
                    f"Alert for {alert_data['symbol']} suppressed "
                    f"(volume ${alert_data['quoteVolume24h']:,.0f} < ${min_volume_threshold:,})"
                )
                return

            # Send JSON alert (primary output to logs and Telegram)
            success = await self.alert_manager.send_json_alert(
                alert_data,
                telegram_enabled=True  # Send to Telegram channel
            )

            if success:
                # Update cooldown timestamp
                self.alert_manager.last_alert_time[alert_key] = current_time
                self.stats_alerts_triggered += 1

                logger.info(
                    f"Alert sent: {alert_data['symbol']} ({alert_data['market']}) "
                    f"{alert_data['change3mPct']:+.2f}% (cooldown: {cooldown_seconds}s)"
                )

            # Optional: Store in Redis
            if self.redis_manager and self.redis_manager.redis:
                try:
                    import orjson
                    key = f"alert_3m:{alert_data['market']}:{alert_data['symbol']}:{alert_data['ts']}"
                    json_str = orjson.dumps(alert_data).decode('utf-8')
                    await self.redis_manager.redis.setex(key, 3600, json_str)  # TTL: 1 hour
                except Exception as e:
                    logger.debug(f"Failed to store alert in Redis: {e}")

        except Exception as e:
            logger.error(f"Error sending alert: {e}")
