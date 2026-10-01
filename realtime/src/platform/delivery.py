"""Persistent outbox with per-chat pacing and non-blocking delayed retries."""

import asyncio
import html
import re
import time
from typing import Any

import aiohttp

from .chart import render
from .market_cap import MarketCap, compact
from .settings import Settings
from .store import Store


def _magnitude(title: str) -> float:
    match = re.search(r"(\d+(?:\.\d+)?)%", title)
    return float(match[1]) if match else 0.0


def format_digest(members: list[dict[str, Any]], market_wide: int) -> str:
    """One message per delivery slot; a same-direction cluster gets a market-wide header."""
    sections = []
    for direction, label in ((-1, "下跌"), (1, "上涨"), (0, "")):
        titles = sorted(
            (m["title"] for m in members if m.get("direction", 0) == direction),
            key=_magnitude,
            reverse=True,
        )
        if not titles:
            continue
        symbols = {m["symbol"] for m in members if m.get("direction", 0) == direction}
        lines = [html.escape(t[:200]) for t in titles]
        if label and len(symbols) >= market_wide:
            lines.insert(0, f"<b>市场联动{label} · {len(symbols)} 个币种</b>")
        sections.append("\n".join(lines))
    return "\n\n".join(sections)


def format_flow(event: dict[str, Any]) -> str:
    """Bilingual on-chain flow alert: 🔴 inflow (sell pressure), 🟢 outflow."""
    versions = event.get("versions") or {}
    zh, en = versions.get("zh"), versions.get("en")
    icon = "🔴" if event["category"] == "inflow" else "🟢"
    lines = []
    if zh:
        lines.append(f"{icon} 🇨🇳 <b>{html.escape(zh['title'])}</b>")
    if en:
        lines.append(f"{icon} 🇺🇸 {html.escape(en['title'])}")
    lines += ["", html.escape((zh or en or {}).get("summary") or event["body"])]
    if event.get("url"):
        lines += ["", f'<a href="{html.escape(event["url"], quote=True)}">交易详情 / Tx ↗</a>']
    return "\n".join(lines)


def format_message(event: dict[str, Any], market_wide: int = 4) -> str:
    if event["kind"] == "flow":
        return format_flow(event)
    if event["kind"] == "market":
        members = event.get("members") or []
        if len(members) > 1:
            return format_digest(members, market_wide)
        return html.escape(event["title"][:500])
    return format_announcement(event)


SOURCES = {
    "binance": "Binance",
    "okx": "OKX",
    "bybit": "Bybit",
    "bitget": "Bitget",
    "bithumb": "Bithumb",
    "upbit": "Upbit",
    "gate": "Gate",
    "mexc": "MEXC",
    "hyperliquid": "Hyperliquid",
}
LABELS = {"zh": ("要点\uff1a", "原文"), "en": ("Key points: ", "Source")}


def format_announcement(event: dict[str, Any]) -> str:
    """Title, summary and key points in the best official language (Chinese first)."""
    version = event.get("i18n") or dict(
        title=event["title"], summary=event.get("body", "")[:300], points="", url=event["url"]
    )
    points_label, link_label = LABELS.get(event.get("lang", ""), LABELS["en"])
    revised = " · 更新" if event.get("updated") else ""
    parts = [
        f"<b>{html.escape(SOURCES.get(event['source'], event['source']))}{revised} · "
        f"{html.escape(version['title'][:300])}</b>"
    ]
    if version.get("summary"):
        parts += ["", html.escape(version["summary"][:600])]
    if version.get("points"):
        parts += ["", f"📌 {points_label}{html.escape(version['points'][:400])}"]
    if version.get("url"):
        parts += ["", f'<a href="{html.escape(version["url"], quote=True)}">{link_label} ↗</a>']
    return "\n".join(parts)


def market_caption(member: dict[str, Any], cap: float | None = None) -> str:
    """Bilingual single-alert caption, as in the reference channel format."""
    move = member["signal"]["move"]
    up = move["direction"] == 1
    dot, pct = ("🟢" if up else "🔴"), f"{abs(move['change']):.2f}%"
    seconds = move["window_seconds"]
    zh = f"币安现货价格在过去 {seconds} 秒内{'上涨' if up else '下跌'}了 {pct}"
    en = f"Binance spot price {'surged' if up else 'dropped'} {pct} in the past {seconds} seconds"
    if move.get("further"):
        further = f"{move['further']:.1f}%"
        zh += f"\uff0c较上次提醒再{'涨' if up else '跌'} {further}"
        en += f", {'up' if up else 'down'} another {further} since the last alert"
    if move.get("extreme"):
        zh += "\uff0c创 24 小时新高" if up else "\uff0c创 24 小时新低"
        en += ", a new 24h high" if up else ", a new 24h low"
    symbol = html.escape(member["symbol"])
    lines = [f"🇨🇳 {dot} [{symbol}] {zh}", f"🇺🇸 {dot} [{symbol}] {en}"]
    if cap:
        coin = html.escape(member["symbol"].removesuffix("USDT"))
        lines += ["", "💰 市值", f"{coin}  MarketCap: {compact(cap)}"]
    return "\n".join(lines)


class Delivery:
    def __init__(self, settings: Settings, store: Store, caps: MarketCap | None = None) -> None:
        self.settings, self.store, self.caps = settings, store, caps
        self.busy: set[str] = set()
        self.next_chat: dict[str, float] = {}
        self.global_pause = 0.0
        self.tasks: set[asyncio.Task[None]] = set()

    async def run(self) -> None:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=8, connect=3)
        ) as session:
            last_edit = 0.0
            try:
                while True:
                    if time.monotonic() - last_edit > 5 and time.monotonic() >= self.global_pause:
                        last_edit = time.monotonic()
                        for sent in await self.store.pending_edits(time.time() - 1800):
                            await self.edit(session, sent)
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

    async def chart(self, session: aiohttp.ClientSession, member: dict[str, Any]) -> bytes:
        # The last 5 hours of 1m candles.
        async with session.get(
            "https://api.binance.com/api/v3/klines",
            params={"symbol": member["symbol"], "interval": "1m", "limit": 300},
        ) as r:
            if r.status != 200:
                raise ValueError("Klines unavailable")
            rows = await r.json()
        title = f"{member['symbol']} · 1m · Binance Spot"
        return await asyncio.to_thread(render, rows, title)

    async def request(
        self, session: aiohttp.ClientSession, event: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """Telegram method and arguments; a single market alert becomes a chart photo."""
        members = event.get("members") or []
        if event["kind"] == "market" and len(members) == 1 and members[0].get("signal"):
            member = members[0]
            caption = market_caption(member, self.caps.get(member["symbol"]) if self.caps else None)
            try:
                form = aiohttp.FormData()
                form.add_field("chat_id", str(event["chat"]))
                if self.settings.topics.get("market"):
                    form.add_field("message_thread_id", self.settings.topics["market"])
                form.add_field("caption", caption)
                form.add_field("parse_mode", "HTML")
                form.add_field(
                    "photo",
                    await self.chart(session, member),
                    filename="chart.png",
                    content_type="image/png",
                )
                return "sendPhoto", {"data": form}
            except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError, OSError):
                text = caption  # The chart is optional; the alert itself is not.
        else:
            text = format_message(event, self.store.policy["digest"]["market_wide_symbols"])
        body = {
            "chat_id": event["chat"],
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        # Each kind posts into its own forum topic of the shared group.
        if self.settings.topics.get(event["kind"]):
            body["message_thread_id"] = int(self.settings.topics[event["kind"]])
        return "sendMessage", {"json": body}

    async def send(self, session: aiohttp.ClientSession, event: dict[str, Any]) -> None:
        started = time.perf_counter()
        try:
            method, arguments = await self.request(session, event)
            async with session.post(
                f"https://api.telegram.org/bot{self.settings.token}/{method}", **arguments
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

    async def edit(self, session: aiohttp.ClientSession, event: dict[str, Any]) -> None:
        """Replace an earlier non-Chinese push once the official Chinese version exists."""
        state = "failed"
        try:
            async with session.post(
                f"https://api.telegram.org/bot{self.settings.token}/editMessageText",
                json={
                    "chat_id": event["chat"],
                    "message_id": event["telegram_id"],
                    "text": format_message(event),
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            ) as r:
                data = await r.json(content_type=None)
                if r.status == 200 and data.get("ok") is True:
                    state = "zh"
                elif r.status == 429:
                    self.global_pause = time.monotonic() + max(
                        1, float(data.get("parameters", {}).get("retry_after", 30))
                    )
                    return  # Left pending; retried after the pause.
        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError):
            state = "unknown"
        await self.store.mark_edit(event["id"], state)

    async def retry(self, event: dict[str, Any], delay: float, error: str) -> None:
        await self.store.finish(
            event, "pending" if event["attempts"] < 5 else "failed", delay=delay, error=error
        )
