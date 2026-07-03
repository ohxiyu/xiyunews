import asyncio
import os

import aiohttp


class TelegramService:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.channel_id = os.getenv("TELEGRAM_CHAT_ID")
        self.admin_id = os.getenv("TELEGRAM_ADMIN_ID")
        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def push(self, msg: str, target: str = "channel", silent: bool = False):
        if not self.token:
            return

        chat_id = self.admin_id if target == "admin" else self.channel_id
        if not chat_id:
            return

        if not self.session:
            await self.start()

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": msg,
            "disable_notification": silent,
        }

        try:
            async with self.session.post(url, json=payload, timeout=30) as resp:
                if resp.status != 200:
                    print(f"⚠️ Telegram send failed: HTTP {resp.status}")
        except asyncio.TimeoutError:
            return
        except Exception as e:
            print(f"⚠️ Telegram send error: {type(e).__name__}")
