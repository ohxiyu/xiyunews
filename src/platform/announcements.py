"""Independent official-source adapters. Web previews are explicitly degraded sources."""

import asyncio
import hashlib
import hmac
import json
import secrets
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlencode, urlsplit

import aiohttp

from .settings import Settings
from .store import Store

Emit = Callable[[dict[str, Any], bool], Awaitable[None]]
Status = Callable[[str, str, str], None]


class PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)


def plain(value: str) -> str:
    parser = PlainText()
    parser.feed(value)
    return " ".join(" ".join(parser.parts).split())


def category(title: str) -> str:
    text = title.lower()
    for name, words in (
        ("delisting", ("delist", "下架", "下线")),
        ("security", ("security incident", "exploit", "暂停", "suspend", "漏洞", "被盗")),
        ("listing", ("to list", "will list", "listing", "上线", "上币", "launch", "lists ")),
        ("maintenance", ("maintenance", "upgrade", "维护", "升级")),
        (
            "promotion",
            (
                "airdrop",
                "campaign",
                "reward",
                "competition",
                "tournament",
                "voucher",
                "carnival",
                "win up to",
                "prize",
                "giveaway",
                "活动",
                "奖励",
                "瓜分",
            ),
        ),
    ):
        if any(word in text for word in words):
            return name
    return "other"


def announcement(
    source: str, sid: str, title: str, body: str, url: str, published: float | None
) -> dict[str, Any]:
    allowed = {
        "binance": {"www.binance.com", "binance.com"},
        "okx": {"www.okx.com", "okx.com"},
        "hyperliquid": {"t.me"},
        "bybit": {"announcements.bybit.com"},
        "bitget": {"www.bitget.com"},
        "kucoin": {"www.kucoin.com"},
        "htx": {"www.htx.com"},
        "bithumb": {"feed.bithumb.com", "www.bithumb.com"},
        "upbit": {"upbit.com"},
        "gate": {"www.gate.com"},
        "mexc": {"www.mexc.com"},
    }
    if urlsplit(url).scheme != "https" or urlsplit(url).hostname not in allowed[source]:
        raise ValueError("Untrusted announcement link")
    title = plain(title)[:500]
    if not title or not sid:
        raise ValueError("Missing source identity or title")
    return dict(
        kind="announcement",
        source=source,
        source_id=sid,
        title=title,
        body=plain(body)[:20000],
        url=url,
        published=published,
        category=category(title),
    )


def parse_okx(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("code") != "0" or not isinstance(payload.get("data"), list):
        raise ValueError("Invalid OKX response")
    rows = []
    for group in payload["data"]:
        rows.extend(group.get("details", [group]))
    events = []
    for row in rows:
        url = row["url"]
        # URL is the documented stable identifier; display time is not first publication time.
        events.append(
            announcement(
                "okx",
                urlsplit(url).path,
                row["title"],
                "",
                url,
                float(row["pTime"]) / 1000 if row.get("pTime") else None,
            )
        )
    return events


def parse_binance_public(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("code") != "000000":
        raise ValueError("Invalid public announcement response")
    events = {}
    for catalog in payload["data"]["catalogs"]:
        for row in catalog.get("articles", []):
            code = row["code"]
            if len(code) != 32 or any(c not in "0123456789abcdef" for c in code):
                raise ValueError("Invalid article identity")
            events[code] = announcement(
                "binance",
                "cms:" + code,
                row["title"],
                "",
                "https://www.binance.com/zh-CN/support/announcement/detail/" + code,
                float(row["releaseDate"]) / 1000,
            )
            if catalog.get("catalogId") is not None:
                events[code]["alias"] = (int(catalog["catalogId"]), events[code]["published"])
    if not events:
        raise ValueError("Empty public announcement page")
    return list(events.values())


def parse_binance(payload: dict[str, Any]) -> dict[str, Any] | None:
    if payload.get("type") != "DATA" or payload.get("topic") != "com_announcement_en":
        return None
    data = payload["data"]
    if isinstance(data, str):
        data = json.loads(data)
    # The documented stream has no article ID/URL. Do not invent a detail-page identifier.
    sid = f"{data['catalogId']}:{data['publishDate']}:{data['title']}"
    event = announcement(
        "binance",
        sid,
        data["title"],
        data.get("body", ""),
        "https://www.binance.com/en/support/announcement",
        float(data["publishDate"]) / 1000,
    )
    # Same catalog and publish time identifies the website (CMS) copy of this article.
    event["alias"] = (int(data["catalogId"]), float(data["publishDate"]) / 1000)
    return event


class TelegramPreview(HTMLParser):
    """Parse public channel previews without scripts, credentials or browser automation."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict[str, Any]] = []
        self.current: dict[str, Any] | None = None
        self.text_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        post = values.get("data-post")
        if post and post.startswith("hyperliquid_announcements/"):
            self.current = {"id": post, "parts": [], "published": None}
            self.rows.append(self.current)
        if self.current is None:
            return
        if "tgme_widget_message_text" in (values.get("class") or ""):
            self.text_depth = 1
        elif self.text_depth and tag not in {"br", "img", "hr", "input", "meta", "link"}:
            self.text_depth += 1
        if tag == "br" and self.text_depth:
            self.current["parts"].append("\n")
        if tag == "time" and values.get("datetime"):
            self.current["published"] = datetime.fromisoformat(
                str(values["datetime"]).replace("Z", "+00:00")
            ).timestamp()

    def handle_endtag(self, tag: str) -> None:
        if self.text_depth and tag not in {"br", "img", "hr", "input", "meta", "link"}:
            self.text_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.current is not None and self.text_depth:
            self.current["parts"].append(data)

    def events(self) -> list[dict[str, Any]]:
        result = []
        for row in self.rows:
            body = "".join(row["parts"]).strip()
            if body:
                result.append(
                    announcement(
                        "hyperliquid",
                        row["id"],
                        body.splitlines()[0][:200],
                        body,
                        f"https://t.me/{row['id']}",
                        row["published"],
                    )
                )
        if not result:
            raise ValueError("Channel preview contained no parseable messages")
        return result


class Announcements:
    def __init__(self, settings: Settings, store: Store, emit: Emit, status: Status) -> None:
        self.settings, self.store, self.emit, self.status = settings, store, emit, status

    async def accept_page(self, source: str, rows: list[dict[str, Any]]) -> None:
        initialized = await self.store.meta(f"baseline:{source}")
        for event in sorted(rows, key=lambda row: row.get("published") or 0):
            await self.emit(event, initialized is None)
        await self.store.set_meta(f"baseline:{source}", "1")

    async def okx(self) -> None:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            while True:
                delay = self.settings.okx_interval
                try:
                    async with session.get(
                        self.settings.okx_url + "/api/v5/support/announcements",
                        headers={"Accept-Language": "en-US"},
                    ) as response:
                        response.raise_for_status()
                        rows = parse_okx(await response.json())
                    if not rows:
                        raise ValueError("Empty announcement page")
                    await self.accept_page("okx", rows)
                    self.status(
                        "okx", "polling", "REST; first page polled, backlog coverage limited"
                    )
                except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError):
                    self.status("okx", "error", "Announcement request or schema validation failed")
                    delay = max(delay, 30)
                await asyncio.sleep(delay)

    async def hyperliquid(self) -> None:
        if self.settings.hyper_session:
            await self.hyperliquid_client()
            return
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            while True:
                delay = self.settings.hyper_interval
                try:
                    async with session.get("https://t.me/s/hyperliquid_announcements") as response:
                        response.raise_for_status()
                        parser = TelegramPreview()
                        parser.feed(await response.text())
                    await self.accept_page("hyperliquid", parser.events())
                    self.status(
                        "hyperliquid",
                        "degraded",
                        "Public preview polling; not realtime; "
                        "limited history and media-only posts not covered",
                    )
                except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError):
                    self.status("hyperliquid", "error", "Public channel preview unavailable")
                    delay = max(delay, 60)
                await asyncio.sleep(delay)

    async def hyperliquid_client(self) -> None:
        # Optional dependency; never prompts for login in the daemon.
        try:
            from telethon import TelegramClient, events
        except ImportError:
            self.status(
                "hyperliquid", "blocked", "Install requirements-telegram.txt for client mode"
            )
            await asyncio.Event().wait()
            return

        if not self.settings.telegram_api_id or not self.settings.telegram_api_hash:
            self.status("hyperliquid", "blocked", "Telegram client credentials missing")
            await asyncio.Event().wait()
            return
        while True:
            client = None
            try:
                client = TelegramClient(
                    self.settings.hyper_session,
                    self.settings.telegram_api_id,
                    self.settings.telegram_api_hash,
                )
                await client.connect()
                if not await client.is_user_authorized():
                    raise ValueError("Pre-authorized Telegram session required")
                channel = await client.get_entity("hyperliquid_announcements")

                def convert(message: Any) -> dict[str, Any]:
                    body = message.message or "[Media-only announcement]"
                    return announcement(
                        "hyperliquid",
                        f"hyperliquid_announcements/{message.id}",
                        body.splitlines()[0][:200],
                        body,
                        f"https://t.me/hyperliquid_announcements/{message.id}",
                        message.date.timestamp(),
                    )

                async def receive(update: Any) -> None:
                    await self.emit(convert(update.message), False)
                    self.status("hyperliquid", "live", "Telegram client updates")

                client.add_event_handler(receive, events.NewMessage(chats=channel))
                client.add_event_handler(receive, events.MessageEdited(chats=channel))
                history = [convert(m) async for m in client.iter_messages(channel, limit=100)]
                await self.accept_page("hyperliquid", history)
                self.status("hyperliquid", "live", "Telegram client; last 100 messages reconciled")
                await client.run_until_disconnected()
            except asyncio.CancelledError:
                raise
            except Exception:
                self.status("hyperliquid", "error", "Telegram client disconnected or unauthorized")
                await asyncio.sleep(30)
            finally:
                if client is not None:
                    await client.disconnect()

    async def binance_public(self, source: str = "binance_announcements") -> None:
        # With the realtime stream, this poll only supplies Chinese titles and article links.
        state = "degraded" if source == "binance_announcements" else "polling"
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            while True:
                delay = 30
                try:
                    async with session.get(
                        "https://www.binance.com/bapi/composite/v1/public/cms/article/list/query",
                        params={"type": 1, "pageNo": 1, "pageSize": 20},
                        headers={"lang": "zh-CN"},
                        allow_redirects=False,
                    ) as response:
                        if response.status != 200:
                            raise ValueError("Public list unavailable")
                        rows = parse_binance_public(await response.json())
                    await self.accept_page("binance_public", rows)
                    self.status(
                        source,
                        state,
                        "Public website polling every 30s; first page only; no realtime SLA",
                    )
                except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError):
                    self.status(source, "error", "Public website request/schema failed")
                    delay = 60
                await asyncio.sleep(delay)

    async def binance(self) -> None:
        if not self.settings.binance_key or not self.settings.binance_secret:
            await self.binance_public()
            return
        await asyncio.gather(self.binance_stream(), self.binance_public("binance_catalog"))

    async def binance_stream(self) -> None:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
            while True:
                try:
                    parameters = dict(
                        random=secrets.token_hex(16),
                        topic="com_announcement_en",
                        recvWindow="30000",
                        timestamp=str(int(time.time() * 1000)),
                    )
                    query = urlencode(sorted(parameters.items()))
                    signature = hmac.new(
                        self.settings.binance_secret.encode(), query.encode(), hashlib.sha256
                    ).hexdigest()
                    url = "wss://api.binance.com/sapi/wss?" + query + "&signature=" + signature
                    async with session.ws_connect(
                        url,
                        headers={"X-MBX-APIKEY": self.settings.binance_key},
                        heartbeat=20,
                        max_msg_size=2 * 1024 * 1024,
                    ) as ws:
                        self.status(
                            "binance_announcements",
                            "live",
                            "Official English stream; "
                            "no replay endpoint, reconnect gaps cannot be backfilled",
                        )
                        async for message in ws:
                            if message.type == aiohttp.WSMsgType.TEXT:
                                payload = json.loads(message.data)
                                event = parse_binance(payload)
                                if event:
                                    await self.emit(event, False)
                                    self.status(
                                        "binance_announcements", "live", "Official English stream"
                                    )
                                elif payload.get("type") not in {"COMMAND", "DATA"}:
                                    raise ValueError("Unexpected announcement stream response")
                            elif message.type == aiohttp.WSMsgType.ERROR:
                                raise ConnectionError("Disconnected")
                    raise ConnectionError("Closed")
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # Never log signed URLs, API secrets, raw client exception or payload.
                    self.status(
                        "binance_announcements", "error", "Stream disconnected; replay gap possible"
                    )
                    await asyncio.sleep(5)
