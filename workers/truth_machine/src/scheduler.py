import asyncio
import time
import json
import traceback
from datetime import datetime, timedelta, timezone
from src.config import (
    VOLATILITY_THRESHOLD,
    POLYMARKET_ENABLE, POLYMARKET_TRENDING_LIMIT, POLYMARKET_DAILY_REPORT_TIME,
    OPINION_ENABLE, OPINION_TRENDING_LIMIT, OPINION_DAILY_REPORT_TIME
)
# SSOT: Use ReportService as the ONLY entry point for report generation
from src.services.report_service import ReportService


class Scheduler:
    """
    V74: Multi-Platform Scheduler (SSOT via Polyrouter)

    IMPORTANT: All data MUST come from Polyrouter API.
    No direct access to third-party platforms.

    - Polymarket: UTC 00:00 (北京时间 08:00)
    - Opinion: UTC 12:00 (北京时间 20:00)
    """

    def __init__(self, polymarket_api, opinion_api, ai, tg, storage=None, poly_router_api=None):
        # DEPRECATED: These legacy APIs are kept for backward compatibility
        # but should NOT be used for report generation
        self.polymarket_api = polymarket_api  # DEPRECATED: Use poly_router_api
        self.opinion_api = opinion_api        # DEPRECATED: Use poly_router_api
        self.ai = ai                          # AIService
        self.tg = tg                          # TelegramService
        self.storage = storage                # ReportRepository (数据持久化)
        self.poly_router_api = poly_router_api  # SSOT: The ONLY data source

        # Initialize ReportService (SSOT + Opinion direct API)
        self.report_service = ReportService(
            polyrouter_api=poly_router_api,
            ai_service=ai,
            storage=storage,
            opinion_api=opinion_api  # Direct Opinion API access
        ) if poly_router_api else None

        self.start_time = time.time()
        self.daily_report_count = 0
        self.polymarket_report_count = 0
        self.opinion_report_count = 0
        self.alerted_markets = {}  # {id: last_alert_time}
        self.last_polymarket_report = None
        self.last_opinion_report = None
        self.last_heartbeat = None

    async def start(self):
        print("🚀 System V74 (SSOT via Polyrouter) Started...")

        # SSOT: Initialize Polyrouter as the ONLY data source
        if self.poly_router_api:
            await self.poly_router_api.start()
            print(f"   ✅ Polyrouter connected (SSOT data source)")
        else:
            print("   ❌ WARNING: Polyrouter not configured!")

        if POLYMARKET_ENABLE:
            print(f"   ✅ Polymarket reports enabled (UTC {POLYMARKET_DAILY_REPORT_TIME})")

        await self.ai.start()
        await self.tg.start()

        # Initial Heartbeat
        await self._send_heartbeat()

        # Main Loop
        while True:
            try:
                now_utc = datetime.now(timezone.utc)

                # On the hour
                if now_utc.minute == 0:
                    current_hour = now_utc.hour
                    current_date = now_utc.date()

                    # Heartbeat every 12 hours (UTC 0, 12)
                    if current_hour in [0, 12]:
                        heartbeat_key = f"{current_date}_{current_hour}"
                        if self.last_heartbeat != heartbeat_key:
                            await self._send_heartbeat()
                            self.last_heartbeat = heartbeat_key

                    # Volatility check every hour (保持原有逻辑)
                    await self._run_volatility_check()

                    # Polymarket Daily Report at UTC 00:00
                    if POLYMARKET_ENABLE and current_hour == 0:
                        report_key = f"{current_date}_polymarket"
                        if self.last_polymarket_report != report_key:
                            await self._run_polymarket_daily_report()
                            self.last_polymarket_report = report_key

                    # Opinion Daily Report at UTC 12:00
                    if OPINION_ENABLE and current_hour == 12:
                        report_key = f"{current_date}_opinion"
                        if self.last_opinion_report != report_key:
                            await self._run_opinion_daily_report()
                            self.last_opinion_report = report_key

                    await asyncio.sleep(65)
                    continue

                # Idle loop
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"🔥 Scheduler Error: {e}")
                traceback.print_exc()
                await asyncio.sleep(60)

    async def _run_polymarket_daily_report(self):
        """Polymarket Trending Top20 日报 - 使用统一 pipeline"""
        await self._run_platform_daily_report("polymarket", POLYMARKET_TRENDING_LIMIT)

    async def _run_opinion_daily_report(self):
        """Opinion Trending Top20 日报 - 使用统一 pipeline"""
        await self._run_platform_daily_report("opinion", OPINION_TRENDING_LIMIT)

    async def _run_platform_daily_report(self, platform_id: str, limit: int):
        """
        SSOT: 使用 ReportService (Polyrouter) 生成日报

        All data MUST come from Polyrouter API.
        No direct access to third-party platforms.

        Args:
            platform_id: 平台 ID (polymarket, kalshi, limitless, etc.)
            limit: 获取市场数量
        """
        start_time = time.time()
        now_utc = datetime.now(timezone.utc)

        platform_name = ReportService.PLATFORM_NAMES.get(platform_id, platform_id.title())
        print(f"📰 [SSOT] Job: {platform_name} Daily Report (UTC {now_utc.strftime('%H:%M')})...")

        if not self.report_service:
            print(f"❌ [SSOT] ReportService not initialized (poly_router_api missing)")
            return

        # SSOT: Use ReportService to generate report via Polyrouter
        payload = await self.report_service.build_latest_report(
            platform_id=platform_id,
            limit=limit,
            lang="zh",  # Default to Chinese
            with_ai=True,
        )

        if not payload:
            print(f"❌ [SSOT] No {platform_name} markets available for daily report")
            return

        # Format and push to Telegram (using same payload as Web API)
        telegram_message = self.report_service.format_for_telegram(payload)
        if telegram_message:
            await self.tg.push(telegram_message, target='channel')

            elapsed = time.time() - start_time
            self.daily_report_count += 1
            if platform_id == "polymarket":
                self.polymarket_report_count += 1
            elif platform_id == "opinion":
                self.opinion_report_count += 1

            degraded_str = " (AI降级)" if payload.degraded else ""
            print(f"✅ [SSOT] {platform_name} report sent "
                  f"(report_id={payload.report_id}, {payload.items_count} items, {elapsed:.1f}s){degraded_str}")
        else:
            print("❌ [SSOT] No content to send")

    def _build_telegram_messages_from_payload(self, payload):
        """
        从 ReportPayload 构建 Telegram 消息

        Args:
            payload: ReportPayload 对象

        Returns:
            List[str]: Telegram 消息列表
        """
        messages = []

        for item in payload.items:
            rank = item.get('rank', '?')
            title = item.get('title', 'Unknown')
            yes = item.get('yes')
            no = item.get('no')
            vol = item.get('volume_24h')
            url = item.get('url', '')
            summary = item.get('summary')

            # 格式化赔率
            if yes is not None and no is not None:
                yes_pct = yes * 100
                no_pct = no * 100
                odds_str = f"Yes {yes_pct:.1f}% / No {no_pct:.1f}%"
            elif yes is not None:
                yes_pct = yes * 100
                odds_str = f"Yes {yes_pct:.1f}%"
            else:
                odds_str = "N/A"

            # 格式化交易量
            if vol is not None and vol > 0:
                if vol >= 1_000_000:
                    vol_str = f"${vol/1_000_000:.1f}M"
                elif vol >= 1_000:
                    vol_str = f"${vol/1_000:.0f}K"
                else:
                    vol_str = f"${vol:.0f}"
            else:
                vol_str = "N/A"

            # 构建消息
            msg = f"**#{rank}** ❓ **{title}**\n"
            msg += f"📊 赔率：{odds_str}\n"
            msg += f"💰 24h交易量：{vol_str}\n"

            if summary:
                msg += f"💡 {summary}\n"

            msg += f"🔗 {url}"

            messages.append(msg)

        return messages

    async def _send_heartbeat(self):
        uptime_h = int((time.time() - self.start_time) / 3600)
        now_utc = datetime.now(timezone.utc)

        platforms = []
        if POLYMARKET_ENABLE:
            platforms.append(f"Polymarket (UTC {POLYMARKET_DAILY_REPORT_TIME})")
        if OPINION_ENABLE:
            platforms.append(f"Opinion (UTC {OPINION_DAILY_REPORT_TIME})")
        platforms_str = ", ".join(platforms)

        msg = (
            f"🖥️ **Truth Machine V73 (Multi-Platform)**\n"
            f"`{now_utc.strftime('%Y-%m-%d %H:%M')} UTC`\n"
            f"⏳ Uptime: `{uptime_h}h`\n"
            f"📰 Total Reports: `{self.daily_report_count}`\n"
            f"   • Polymarket: `{self.polymarket_report_count}`\n"
            f"   • Opinion: `{self.opinion_report_count}`\n"
            f"📋 Platforms: {platforms_str}"
        )
        await self.tg.push(msg, target='admin', silent=True)
        print(f"💓 Heartbeat sent at {now_utc.strftime('%H:%M')} UTC")

    async def _run_volatility_check(self):
        """波动监控 - 保持原有逻辑"""
        print("⚡ Job: Hourly Volatility Check...")
        if not self.poly_router_api:
            return

        # 1. Fetch top markets from Polyrouter
        raw = await self.poly_router_api.get_multi_platform_markets(
            platforms=["polymarket", "kalshi", "limitless"],
            limit_per_platform=30
        )

        # 2. Check each market
        for m in raw:
            m_id = str(m.get('id'))
            platform = m.get('platform')
            title = m.get('title') or m.get('question')

            if not title:
                continue

            # Anti-spam: Only alert once every 4 hours
            last_alert = self.alerted_markets.get(m_id)
            if last_alert and (time.time() - last_alert) < 14400:
                continue

            # 3. Get History
            history = await self.poly_router_api.get_price_history(m_id, platform=platform, interval="1h", limit=2)
            if len(history) < 2:
                continue

            prev_price = float(history[1].get('close', 0))
            new_price = float(history[0].get('close', 0))

            if prev_price <= 0:
                continue

            change = (new_price - prev_price) / prev_price

            # 4. Detect Volatility
            if abs(change) >= VOLATILITY_THRESHOLD:
                print(f"🚨 Volatility Detected: {title} ({platform}) | {prev_price} -> {new_price} ({change:+.1%})")

                report = await self.ai.analyze_volatility({
                    "title": title,
                    "platform": platform,
                    "old_price": prev_price,
                    "new_price": new_price,
                    "change": change
                })

                if report:
                    await self.tg.push(report, target='channel')
                    self.alerted_markets[m_id] = time.time()

            # Rate limit courtesy
            await asyncio.sleep(0.5)
