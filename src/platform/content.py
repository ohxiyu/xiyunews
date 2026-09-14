"""Bounded official article enrichment, separate from immutable delivery events."""

import asyncio
import re
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .store import Store


class ArticleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.skip = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if not self.depth:
            if tag == "div" and "richTextContent" in (dict(attrs).get("class") or ""):
                self.depth = 1
            return
        if tag in {"script", "style"}:
            self.skip += 1
        if tag not in {"br", "img", "hr", "input", "meta", "link", "wbr"}:
            self.depth += 1
        if tag in {"td", "th"}:
            self.parts.append(" | ")
        if tag in {"p", "li", "br", "tr", "h2", "h3"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self.depth and tag not in {"br", "img", "hr", "input", "meta", "link", "wbr"}:
            if tag in {"p", "li", "tr", "h2", "h3"}:
                self.parts.append("\n")
            if tag in {"script", "style"} and self.skip:
                self.skip -= 1
            self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.depth and not self.skip:
            self.parts.append(data)


def article_text(html: str) -> str:
    parser = ArticleParser()
    parser.feed(html)
    body = "\n".join(
        line for raw in "".join(parser.parts).splitlines() if (line := " ".join(raw.split()))
    )
    if len(body) < 80:
        raise ValueError("Article body missing")
    return body[:20000]


def brief(body: str) -> str:
    """Extract verbatim sentences; never infer facts or silently translate numbers."""
    sentences = re.split(r"(?<=[.!?。\uff01\uff1f])\s+|\n+", body.strip())
    keywords = re.compile(
        r"list|launch|trading|delist|suspend|maintenance|upgrade|deposit|withdraw|"
        r"UTC|leverage|上线|下架|暂停|升级|交易|充值|提现",
        re.I,
    )
    excluded = re.compile(
        r"general update|please check|not an endorsement|past performance|"
        r"not financial advice|exercise control|unfamiliar|disclaimer|user agreement|terms of",
        re.I,
    )
    candidates = [s.strip() for s in sentences if len(s.strip()) > 25 and not excluded.search(s)]
    selected = [s for s in candidates if keywords.search(s)][:3] or candidates[:2]
    result = " ".join(dict.fromkeys(selected))
    return result if len(result) <= 700 else result[:697] + "…"


class ContentCollector:
    def __init__(self, store: Store) -> None:
        self.store = store

    async def enrich(self, session: aiohttp.ClientSession, event: dict[str, Any]) -> None:
        body = event["body"]
        state = "ready"
        try:
            if not body:
                url = urlsplit(event["url"])
                if (
                    event["source"] != "okx"
                    or url.scheme != "https"
                    or url.hostname not in {"www.okx.com", "okx.com"}
                    or not url.path.startswith("/help/")
                ):
                    raise ValueError("No supported detail source")
                async with session.get(event["url"], allow_redirects=False) as response:
                    if response.status != 200:
                        raise ValueError("Detail unavailable")
                    data = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        data.extend(chunk)
                        if len(data) > 2_000_000:
                            raise ValueError("Article exceeds limit")
                    body = article_text(data.decode("utf-8"))
        except (aiohttp.ClientError, TimeoutError, ValueError, UnicodeError):
            state = "unavailable"
        await self.store.save_content(event["id"], body, brief(body), state)

    async def run(self) -> None:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            while True:
                for event in await self.store.content_pending(time.time()):
                    await self.enrich(session, event)
                    await asyncio.sleep(1)
                await asyncio.sleep(15)
