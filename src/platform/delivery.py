"""Persistent outbox with per-chat pacing and non-blocking delayed retries."""

import asyncio
import html
import time
from typing import Any

import aiohttp

from .settings import Settings
from .store import Store


def format_message(event: dict[str, Any]) -> str:
    if event["kind"] == "market":
        return html.escape(event["title"][:500])
    heading = "行情异动" if event["kind"] == "market" else "官方公告"
    revised = " · 更新" if event["updated"] else ""
    parts = [
        f"<b>FomoBTC · {heading}{revised}</b>",
        html.escape(event["source"]),
        "",
        html.escape(event["title"][:500]),
    ]
    if event["body"]:
        # Escape after truncation so HTML entities cannot be cut in half.
        parts += ["", html.escape(event["body"][:300])]
    if event["url"]:
        parts += ["", f'<a href="{html.escape(event["url"], quote=True)}">官方来源</a>']
    parts += ["", f"事件 {event['id'][:8]}"]
    return "\n".join(parts)


class Delivery:
    def __init__(self, settings: Settings, store: Store) -> None:
        self.settings, self.store = settings, store
        self.busy: set[str] = set()
        self.next_chat: dict[str, float] = {}
        self.global_pause = 0.0
        self.tasks: set[asyncio.Task[None]] = set()

    async def run(self) -> None:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=8, connect=3)
        ) as session:
            try:
                while True:
                    for completed in list(self.tasks):
                        if completed.done():
                            self.tasks.remove(completed)
                            completed.result()
                    now = time.monotonic()
                    unavailable = self.busy | {c for c, t in self.next_chat.items() if t > now}
                    if len(self.tasks) < 3 and now >= self.global_pause:
                        event = await self.store.claim(unavailable, chinese_announcements=True)
                        if event:
                            self.busy.add(event["chat"])
                            task = asyncio.create_task(self.send(session, event))
                            self.tasks.add(task)
                            continue
                    await asyncio.sleep(0.02)
            finally:
                if self.tasks:
                    _, pending = await asyncio.wait(self.tasks, timeout=10)
                    for task in pending:
                        task.cancel()
                    await asyncio.gather(*pending, return_exceptions=True)

    async def send(self, session: aiohttp.ClientSession, event: dict[str, Any]) -> None:
        started = time.perf_counter()
        try:
            async with session.post(
                f"https://api.telegram.org/bot{self.settings.token}/sendMessage",
                json={
                    "chat_id": event["chat"],
                    "text": format_message(event),
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            ) as r:
                data = await r.json(content_type=None)
                if r.status == 200 and data.get("ok") is True:
                    await self.store.finish(
                        event,
                        "sent",
                        message_id=data["result"]["message_id"],
                        duration=(time.perf_counter() - started) * 1000,
                    )
                elif r.status == 429:
                    delay = max(1, float(data.get("parameters", {}).get("retry_after", 30)))
                    self.global_pause = time.monotonic() + delay
                    await self.retry(event, delay, "telegram_rate_limit")
                elif r.status >= 500:
                    await self.retry(
                        event, min(2 ** event["attempts"], 60), "telegram_server_error"
                    )
                else:
                    await self.store.finish(event, "failed", error="telegram_rejected")
        except asyncio.CancelledError:
            await self.store.finish(event, "unknown", error="interrupted_request")
            raise
        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError):
            # Do not blindly replay a request whose delivery may have succeeded.
            await self.store.finish(event, "unknown", error="ambiguous_transport_result")
        finally:
            self.next_chat[event["chat"]] = time.monotonic() + self.settings.chat_interval
            self.busy.discard(event["chat"])

    async def retry(self, event: dict[str, Any], delay: float, error: str) -> None:
        await self.store.finish(
            event, "pending" if event["attempts"] < 5 else "failed", delay=delay, error=error
        )
