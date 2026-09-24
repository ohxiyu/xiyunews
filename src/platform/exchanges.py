"""Additional exchanges: official announcement APIs and new trading-pair detection.

Announcement lists come from each exchange's own public endpoint. Where that endpoint
is blocked from the host (Upbit KR, Gate, MEXC), a new market in the exchange's public
market list is reported instead: it marks the moment trading opens, not the notice.
"""

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .announcements import Emit, Status, announcement

KST = timezone(timedelta(hours=9))
QUOTES = ("USDT", "USDC", "USDE", "FDUSD", "BTC", "ETH", "KRW", "EUR", "TRY", "BRL")
NAMES = {
    "bybit": "Bybit",
    "bitget": "Bitget",
    "bithumb": "Bithumb",
    "upbit": "Upbit",
    "gate": "Gate",
    "mexc": "MEXC",
}


def hinted(event: dict[str, Any], hint: str) -> dict[str, Any]:
    """Refine a keyword category with the exchange's own announcement type."""
    text = hint.lower()
    if event["category"] == "other":
        if any(w in text for w in ("activit", "event", "promotion", "campaign", "reward")):
            event["category"] = "promotion"
        elif "delist" in text:
            event["category"] = "delisting"
        elif any(w in text for w in ("listing", "new_crypto", "new-listings", "coin_listings")):
            event["category"] = "listing"
        elif "maintenance" in text or "입출금" in text:
            event["category"] = "maintenance"
    return event


def parse_bybit(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("retCode") != 0:
        raise ValueError("Invalid Bybit response")
    events = []
    for row in payload["result"]["list"]:
        url = row["url"]
        event = announcement(
            "bybit",
            urlsplit(url).path,
            row["title"],
            row.get("description", ""),
            url,
            float(row.get("publishTime") or row["dateTimestamp"]) / 1000,
        )
        events.append(hinted(event, str(row.get("type", {}).get("key", ""))))
    return events


def parse_bitget(payload: dict[str, Any]) -> list[dict[str, Any]]:
    if payload.get("code") != "00000":
        raise ValueError("Invalid Bitget response")
    events = []
    for row in payload["data"]:
        event = announcement(
            "bitget",
            str(row["annId"]),
            row["annTitle"],
            "",
            row["annUrl"],
            float(row["cTime"]) / 1000,
        )
        events.append(hinted(event, f"{row.get('annType', '')} {row.get('annSubType', '')}"))
    return events




def parse_bithumb(payload: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not isinstance(payload, list):
        raise ValueError("Invalid Bithumb response")
    events = []
    for row in payload:
        url = row["pc_url"]
        published = datetime.strptime(row["published_at"], "%Y-%m-%d %H:%M:%S")
        event = announcement(
            "bithumb",
            urlsplit(url).path,
            row["title"],
            "",
            url,
            published.replace(tzinfo=KST).timestamp(),
        )
        events.append(hinted(event, " ".join(row.get("categories") or [])))
    return events


def bybit_key(url: str) -> str:
    # The article id suffix is shared by every locale of one Bybit announcement.
    match = re.search(r"-(art[0-9a-f]+)/?$", url)
    return match[1] if match else url


def versions_bybit(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    if payload.get("retCode") != 0:
        raise ValueError("Invalid Bybit response")
    return {
        bybit_key(row["url"]): dict(
            title=row["title"], body=row.get("description", ""), url=row["url"]
        )
        for row in payload["result"]["list"]
    }


def versions_bitget(payload: dict[str, Any]) -> dict[str, dict[str, str]]:
    if payload.get("code") != "00000":
        raise ValueError("Invalid Bitget response")
    return {
        str(row["annId"]): dict(title=row["annTitle"], body="", url=row["annUrl"])
        for row in payload["data"]
    }


def split_symbol(symbol: str) -> tuple[str, str]:
    for quote in QUOTES:
        if symbol.endswith(quote) and len(symbol) > len(quote):
            return symbol[: -len(quote)], quote
    return symbol, ""


def markets_upbit(payload: list[dict[str, Any]]) -> dict[str, tuple[str, str, str]]:
    # Upbit markets are QUOTE-BASE.
    return {
        m["market"]: (m["market"].split("-")[1], m["market"].split("-")[0], m["market"])
        for m in payload
    }


def markets_bithumb(payload: list[dict[str, Any]]) -> dict[str, tuple[str, str, str]]:
    return {
        m["market"]: (
            m["market"].split("-")[1],
            m["market"].split("-")[0],
            f"{m['market'].split('-')[1]}-{m['market'].split('-')[0]}",
        )
        for m in payload
    }


def markets_gate(payload: list[dict[str, Any]]) -> dict[str, tuple[str, str, str]]:
    return {p["id"]: (p["base"], p["quote"], p["id"]) for p in payload}


def markets_mexc(payload: dict[str, Any]) -> dict[str, tuple[str, str, str]]:
    result = {}
    for symbol in payload["data"]:
        base, quote = split_symbol(symbol)
        result[symbol] = (base, quote, f"{base}_{quote}" if quote else symbol)
    return result


PAIR_URLS = {
    "upbit": "https://upbit.com/exchange?code=CRIX.UPBIT.{}",
    "bithumb": "https://www.bithumb.com/react/trade/order/{}",
    "gate": "https://www.gate.com/trade/{}",
    "mexc": "https://www.mexc.com/exchange/{}",
}


def pair_event(
    source: str, key: str, base: str, quote: str, path: str, quiet: bool = False
) -> dict[str, Any]:
    event = announcement(
        source,
        "market:" + key,
        f"{NAMES[source]} 新增交易对 {base}/{quote}"
        if quote
        else f"{NAMES[source]} 新增交易对 {key}",
        f"{NAMES[source]} 公开行情接口出现新交易对 {base}/{quote or '?'}。"
        "通常意味着已开放或即将开放交易。",
        PAIR_URLS[source].format(path),
        None,
    )
    event["category"] = "listing"
    event["symbol"] = base
    event["quiet"] = quiet
    event["i18n"] = {
        "en": dict(
            title=f"{NAMES[source]} lists new pair {base}/{quote or '?'}",
            body=f"A new trading pair {base}/{quote or '?'} appeared in the public {NAMES[source]} "
            "market list, which usually means trading is open or about to open.",
            url=event["url"],
        )
    }
    return event


@dataclass(frozen=True)
class Feed:
    source: str
    url: str
    parse: Callable[[Any], list[dict[str, Any]]]
    interval: float
    # Official second language: (language, list URL, parser keyed like `key`).
    translation: tuple[str, str, Callable[[Any], dict[str, dict[str, str]]]] | None = None
    key: Callable[[dict[str, Any]], str] = lambda event: str(event["source_id"])


@dataclass(frozen=True)
class Markets:
    source: str
    url: str
    parse: Callable[[Any], dict[str, tuple[str, str, str]]]
    interval: float
    quiet: bool  # Recorded on the web; not pushed (high-volume long-tail listings).


FEEDS = (
    Feed(
        "bybit",
        "https://api.bybit.com/v5/announcements/index?locale=en-US&limit=20",
        parse_bybit,
        5,
        # Bybit publishes Chinese as zh-TW (traditional); shown as-is, not converted.
        (
            "zh",
            "https://api.bybit.com/v5/announcements/index?locale=zh-TW&limit=20",
            versions_bybit,
        ),
        lambda event: bybit_key(event["url"]),
    ),
    Feed(
        "bitget",
        "https://api.bitget.com/api/v2/public/annoucements?language=en_US",
        parse_bitget,
        5,
        ("zh", "https://api.bitget.com/api/v2/public/annoucements?language=zh_CN", versions_bitget),
    ),
    # Korean only; served through a CDN cache, so new notices can appear minutes late.
    Feed("bithumb", "https://feed-api.bithumb.com/v1/notices?count=20", parse_bithumb, 10),
)
MARKETS = (
    Markets("upbit", "https://api.upbit.com/v1/market/all", markets_upbit, 10, False),
    Markets("bithumb", "https://api.bithumb.com/v1/market/all", markets_bithumb, 15, False),
    Markets("gate", "https://api.gateio.ws/api/v4/spot/currency_pairs", markets_gate, 60, True),
    Markets("mexc", "https://api.mexc.com/api/v3/defaultSymbols", markets_mexc, 30, True),
)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; FomoBTC/2.2; +https://fomobtc.com)",
    "Accept": "application/json",
}
MAX_NEW_PAIRS = 50


class Exchanges:
    def __init__(
        self, accept: Callable[[str, list[dict[str, Any]]], Any], emit: Emit, status: Status
    ) -> None:
        self.accept, self.emit, self.status = accept, emit, status

    def tasks(self) -> list[tuple[str, Any]]:
        return [(f"{f.source}-notices", self.feed(f)) for f in FEEDS] + [
            (f"{m.source}-markets", self.markets(m)) for m in MARKETS
        ]

    async def get(self, session: aiohttp.ClientSession, url: str) -> Any:
        async with session.get(url, headers=HEADERS, allow_redirects=False) as response:
            if response.status != 200:
                raise ValueError(f"HTTP {response.status}")
            return await response.json(content_type=None)

    async def feed(self, feed: Feed) -> None:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            while True:
                delay = feed.interval
                try:
                    rows = feed.parse(await self.get(session, feed.url))
                    if not rows:
                        raise ValueError("Empty announcement page")
                    if feed.translation:
                        lang, url, parse = feed.translation
                        try:
                            other = parse(await self.get(session, url))
                        except (aiohttp.ClientError, TimeoutError, ValueError, KeyError):
                            other = {}  # The original language still flows; retried next poll.
                        for row in rows:
                            if feed.key(row) in other:
                                row["i18n"] = {lang: other[feed.key(row)]}
                    await self.accept(feed.source, rows)
                    self.status(
                        feed.source,
                        "polling",
                        f"Official announcement API every {feed.interval:g}s",
                    )
                except (aiohttp.ClientError, TimeoutError, ValueError, KeyError, TypeError):
                    self.status(feed.source, "error", "Announcement request or schema failed")
                    delay = max(delay, 30)
                await asyncio.sleep(delay)

    async def markets(self, spec: Markets) -> None:
        name = spec.source + "_markets"
        known: set[str] | None = None
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
            while True:
                delay = spec.interval
                try:
                    current = spec.parse(await self.get(session, spec.url))
                    if len(current) < 20:
                        raise ValueError("Implausibly small market list")
                    if known is None:
                        # First list after start: stored as a baseline, never notified.
                        rows = [
                            pair_event(spec.source, k, *v, quiet=spec.quiet)
                            for k, v in current.items()
                        ]
                        await self.accept(name, rows)
                    else:
                        added = sorted(set(current) - known)
                        if len(added) > MAX_NEW_PAIRS:
                            raise ValueError("Too many new pairs at once")
                        for key in added:
                            await self.emit(
                                pair_event(spec.source, key, *current[key], quiet=spec.quiet),
                                False,
                            )
                    known = set(current) | (known or set())
                    self.status(
                        name,
                        "polling",
                        f"{len(current)} markets; new pairs every {spec.interval:g}s",
                    )
                except (
                    aiohttp.ClientError,
                    TimeoutError,
                    ValueError,
                    KeyError,
                    TypeError,
                    IndexError,
                ):
                    self.status(name, "error", "Market list request or schema failed")
                    delay = max(delay, 60)
                await asyncio.sleep(delay)
