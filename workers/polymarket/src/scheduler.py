import asyncio
import time
import traceback
from datetime import datetime, timezone

from src.config import POLYMARKET_ENABLE, POLYMARKET_TRENDING_LIMIT, POLYMARKET_DAILY_REPORT_TIME
from src.services.report_service import ReportService


class Scheduler:
    """Daily Polymarket breaking report scheduler."""

    def __init__(self, tg, storage=None, polymarket_api=None):
        self.tg = tg
        self.report_service = ReportService(polymarket_api, storage=storage) if polymarket_api else None
        self.start_time = time.time()
        self.daily_report_count = 0
        self.last_report = None
        self.last_heartbeat = None

    async def start(self):
        print("🚀 Polymarket Breaking Scheduler Started...")

        if self.report_service:
            await self.report_service.polymarket.start()
            print("   ✅ Polymarket breaking data client ready")
        else:
            print("   ❌ WARNING: Polymarket data client not configured!")

        if POLYMARKET_ENABLE:
            print(f"   ✅ Polymarket breaking reports enabled (UTC {POLYMARKET_DAILY_REPORT_TIME})")

        await self.tg.start()
        await self._send_heartbeat()

        while True:
            try:
                now_utc = datetime.now(timezone.utc)

                if now_utc.minute == 0:
                    current_hour = now_utc.hour
                    current_date = now_utc.date()

                    if current_hour in [0, 12]:
                        heartbeat_key = f"{current_date}_{current_hour}"
                        if self.last_heartbeat != heartbeat_key:
                            await self._send_heartbeat()
                            self.last_heartbeat = heartbeat_key

                    if POLYMARKET_ENABLE and current_hour == 0:
                        report_key = f"{current_date}_polymarket_breaking"
                        if self.last_report != report_key:
                            await self._run_daily_report()
                            self.last_report = report_key

                    await asyncio.sleep(65)
                    continue

                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"🔥 Scheduler Error: {e}")
                traceback.print_exc()
                await asyncio.sleep(60)

    async def _run_daily_report(self):
        start_time = time.time()
        now_utc = datetime.now(timezone.utc)
        print(f"📰 Job: Polymarket Breaking Report (UTC {now_utc.strftime('%H:%M')})...")

        if not self.report_service:
            print("❌ ReportService not initialized")
            return

        payload = await self.report_service.build_latest_report(limit=POLYMARKET_TRENDING_LIMIT)
        if not payload:
            print("❌ No Polymarket breaking markets available for report")
            return

        telegram_message = self.report_service.format_for_telegram(payload)
        if telegram_message:
            await self.tg.push(telegram_message, target='channel')
            elapsed = time.time() - start_time
            self.daily_report_count += 1
            print(f"✅ Polymarket breaking report sent (report_id={payload.report_id}, {payload.items_count} items, {elapsed:.1f}s)")
        else:
            print("❌ No content to send")

    async def _send_heartbeat(self):
        uptime_h = int((time.time() - self.start_time) / 3600)
        now_utc = datetime.now(timezone.utc)
        msg = (
            f"🖥️ **Polymarket Breaking Scheduler**\n"
            f"`{now_utc.strftime('%Y-%m-%d %H:%M')} UTC`\n"
            f"⏳ Uptime: `{uptime_h}h`\n"
            f"📰 Reports: `{self.daily_report_count}`\n"
            f"📋 Platform: Polymarket Breaking (UTC {POLYMARKET_DAILY_REPORT_TIME})"
        )
        await self.tg.push(msg, target='admin', silent=True)
        print(f"💓 Heartbeat sent at {now_utc.strftime('%H:%M')} UTC")
