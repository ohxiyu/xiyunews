import asyncio
import time
import traceback
from datetime import datetime, timezone
from src.config import (
    POLYMARKET_ENABLE, POLYMARKET_TRENDING_LIMIT, POLYMARKET_DAILY_REPORT_TIME,
)
from src.services.report_service import ReportService


class Scheduler:
    """
    Polymarket Scheduler (SSOT via Polyrouter)

    - Polymarket: UTC 00:00 (北京时间 08:00)
    """

    def __init__(self, tg, storage=None, poly_router_api=None):
        self.tg = tg
        self.storage = storage
        self.poly_router_api = poly_router_api

        self.report_service = ReportService(
            polyrouter_api=poly_router_api,
            storage=storage,
        ) if poly_router_api else None

        self.start_time = time.time()
        self.daily_report_count = 0
        self.last_polymarket_report = None
        self.last_heartbeat = None

    async def start(self):
        print("🚀 Polymarket Scheduler Started...")

        if self.poly_router_api:
            await self.poly_router_api.start()
            print(f"   ✅ Polyrouter connected")
        else:
            print("   ❌ WARNING: Polyrouter not configured!")

        if POLYMARKET_ENABLE:
            print(f"   ✅ Polymarket reports enabled (UTC {POLYMARKET_DAILY_REPORT_TIME})")

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

                    # Polymarket Daily Report at UTC 00:00
                    if POLYMARKET_ENABLE and current_hour == 0:
                        report_key = f"{current_date}_polymarket"
                        if self.last_polymarket_report != report_key:
                            await self._run_daily_report()
                            self.last_polymarket_report = report_key

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

    async def _run_daily_report(self):
        """Polymarket daily report via Polyrouter."""
        start_time = time.time()
        now_utc = datetime.now(timezone.utc)
        print(f"📰 Job: Polymarket Daily Report (UTC {now_utc.strftime('%H:%M')})...")

        if not self.report_service:
            print(f"❌ ReportService not initialized (poly_router_api missing)")
            return

        payload = await self.report_service.build_latest_report(
            platform_id="polymarket",
            limit=POLYMARKET_TRENDING_LIMIT,
        )

        if not payload:
            print(f"❌ No Polymarket markets available for daily report")
            return

        telegram_message = self.report_service.format_for_telegram(payload)
        if telegram_message:
            await self.tg.push(telegram_message, target='channel')

            elapsed = time.time() - start_time
            self.daily_report_count += 1
            print(f"✅ Polymarket report sent "
                  f"(report_id={payload.report_id}, {payload.items_count} items, {elapsed:.1f}s)")
        else:
            print("❌ No content to send")

    async def _send_heartbeat(self):
        uptime_h = int((time.time() - self.start_time) / 3600)
        now_utc = datetime.now(timezone.utc)

        msg = (
            f"🖥️ **Polymarket Scheduler**\n"
            f"`{now_utc.strftime('%Y-%m-%d %H:%M')} UTC`\n"
            f"⏳ Uptime: `{uptime_h}h`\n"
            f"📰 Reports: `{self.daily_report_count}`\n"
            f"📋 Platform: Polymarket (UTC {POLYMARKET_DAILY_REPORT_TIME})"
        )
        await self.tg.push(msg, target='admin', silent=True)
        print(f"💓 Heartbeat sent at {now_utc.strftime('%H:%M')} UTC")
