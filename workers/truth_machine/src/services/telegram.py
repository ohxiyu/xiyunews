import os
import aiohttp
import asyncio
import logging

class TelegramService:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.channel_id = os.getenv("TELEGRAM_CHAT_ID")
        self.admin_id = os.getenv("TELEGRAM_ADMIN_ID")
        self.session = None

    async def start(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()

    async def push(self, msg, target='channel', silent=False):
        if not self.token: return
        chat_id = self.admin_id if target == 'admin' else self.channel_id
        if not chat_id: return

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": msg,
            "disable_notification": silent
        }
        # Note: Removed parse_mode to avoid Markdown parsing errors
        
        if not self.session: await self.start()

        # V49.1 Safety Logic: Handle ReadTimeout gracefully (Prevent Duplicates)
        try:
            async with self.session.post(url, json=payload, timeout=30) as resp:
                if resp.status == 200: return
                # If 429 Retry After? (Simplification: Ignore)
        except asyncio.TimeoutError:
            # Swallow timeout to prevent retry loop -> duplicate message
            return 
        except Exception as e:
            # Fallback to plain text if Markdown fails
            try:
                clean_msg = msg.replace("**", "").replace("`", "")
                params_clean = {**payload, "text": clean_msg}
                async with self.session.post(url, json=params_clean, timeout=30) as r2: pass
            except: pass
