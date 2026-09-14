"""Bounded official article enrichment, separate from immutable delivery events."""

import asyncio
import html as html_module
import json
import re
import time
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urlsplit

import aiohttp

from .announcements import plain
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
        r"not financial advice|exercise control|unfamiliar|disclaimer|user agreement|terms of|"
        r"一般性公告|地区而异|免责声明|风险提示",
        re.I,
    )
    candidates = [s.strip() for s in sentences if len(s.strip()) > 25 and not excluded.search(s)]
    selected = [s for s in candidates if keywords.search(s)][:3] or candidates[:2]
    result = " ".join(dict.fromkeys(selected))
    return result if len(result) <= 700 else result[:697] + "…"


def cms_text(value: str) -> str:
    tree = json.loads(value)
    parts: list[str] = []

    def walk(node: Any, depth: int = 0) -> None:
        if depth > 40:
            raise ValueError("CMS nesting limit")
        if not isinstance(node, dict):
            return
        if node.get("tag") in {"script", "style"}:
            return
        if node.get("node") == "text":
            parts.append(str(node.get("text", "")))
        for child in node.get("child", []):
            walk(child, depth + 1)
        if node.get("tag") in {"p", "li", "tr", "br"}:
            parts.append("\n")

    walk(tree)
    text = html_module.unescape("".join(parts)).strip()
    if not text:
        raise ValueError("Empty CMS body")
    return text[:20000]


class ContentCollector:
    def __init__(self, store: Store) -> None:
        self.store = store
        self.wake = asyncio.Event()

    async def enrich(self, session: aiohttp.ClientSession, event: dict[str, Any]) -> None:
        body, title, source_url = event["body"], event["title"], event["url"]
        state, language = "ready", ""
        try:
            if event["source"] == "okx":
                url = urlsplit(source_url)
                if (
                    url.scheme != "https"
                    or url.hostname not in {"www.okx.com", "okx.com"}
                    or not url.path.startswith("/help/")
                ):
                    raise ValueError("Unsupported official article")
                source_url = f"https://www.okx.com/zh-hans{url.path}"
                async with session.get(source_url, allow_redirects=False) as response:
                    if response.status != 200:
                        raise ValueError("Chinese detail unavailable")
                    data = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        data.extend(chunk)
                        if len(data) > 2_000_000:
                            raise ValueError("Article exceeds limit")
                    html = data.decode("utf-8")
                    body = article_text(html)
                    match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
                    if match:
                        title = plain(match[1])
            elif event["source"] == "binance" and event["source_id"].startswith("cms:"):
                code = event["source_id"][4:]
                if not re.fullmatch(r"[a-f0-9]{32}", code):
                    raise ValueError("Invalid article code")
                async with session.get(
                    "https://www.binance.com/bapi/composite/v1/public/cms/article/detail/query",
                    params={"articleCode": code},
                    headers={"lang": "zh-CN"},
                    allow_redirects=False,
                ) as response:
                    if response.status != 200:
                        raise ValueError("CMS detail unavailable")
                    raw = bytearray()
                    async for chunk in response.content.iter_chunked(65536):
                        raw.extend(chunk)
                        if len(raw) > 2_000_000:
                            raise ValueError("CMS detail exceeds limit")
                    payload = json.loads(raw)
                    if payload.get("code") != "000000":
                        raise ValueError("CMS detail schema")
                    title = plain(payload["data"]["title"])
                    body = cms_text(payload["data"]["body"])
            if len(re.findall(r"[\u4e00-\u9fff]", body)) < 20:
                state = "translation_pending"
            else:
                language = "zh"
        except (aiohttp.ClientError, TimeoutError, ValueError, UnicodeError, KeyError, TypeError):
            state = "translation_pending"
        await self.store.save_content(
            event["id"],
            body,
            brief(body) if language == "zh" else "",
            state,
            title=title,
            language=language,
            url=source_url if language == "zh" else event["url"],
        )

    async def run(self) -> None:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            while True:
                self.wake.clear()
                # Re-query after each article so retries never queue ahead of new arrivals.
                pending = await self.store.content_pending(time.time())
                if pending:
                    await self.enrich(session, pending[0])
                    continue
                try:
                    await asyncio.wait_for(self.wake.wait(), timeout=2)
                except TimeoutError:
                    pass
