"""Telegram public channel scraper implementation."""

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from bs4 import BeautifulSoup

from .base import BaseScraper
from ..models import ContentItem, TelegramConfig, TelegramChannelConfig, SourceType

logger = logging.getLogger(__name__)

TELEGRAM_WEB_BASES = (
    "https://telegram.me/s",
    "https://telegram.dog/s",
    "https://t.me/s",
)
TELEGRAM_LINK_BASE = "https://telegram.me"
USER_AGENT = "Mozilla/5.0 (compatible; xiyu.news/1.0; +https://github.com/thysrael/bmtnews)"


class TelegramScraper(BaseScraper):
    """Scraper for Telegram public channels via web preview."""

    def __init__(self, config: TelegramConfig, http_client: httpx.AsyncClient):
        super().__init__(config.model_dump(), http_client)
        self.telegram_config = config
        # One row per channel per fetch: why a channel yields what it yields.
        self.channel_reports: List[dict] = []

    async def fetch(self, since: datetime) -> List[ContentItem]:
        if not self.config.get("enabled", True):
            return []

        self.channel_reports = []
        channels = [cfg for cfg in self.telegram_config.channels if cfg.enabled]
        if not channels:
            return []

        results = await asyncio.gather(
            *(self._fetch_channel(cfg, since) for cfg in channels),
            return_exceptions=True,
        )
        items = []
        failures = []
        live = 0
        for cfg, result in zip(channels, results):
            if not cfg.probe:
                live += 1
            if isinstance(result, Exception):
                self.channel_reports.append({
                    "channel": cfg.channel,
                    "probe": cfg.probe,
                    "status": "failed",
                    "error": type(result).__name__,
                })
                if not cfg.probe:
                    failures.append(result)
                logger.warning("Error fetching Telegram channel: %s", result)
            elif isinstance(result, list) and not cfg.probe:
                items.extend(result)

        if live and len(failures) == live:
            raise RuntimeError(f"All Telegram channels failed: {failures[0]}") from failures[0]
        return items

    async def _fetch_channel(self, cfg: TelegramChannelConfig, since: datetime) -> List[ContentItem]:
        headers = {"User-Agent": USER_AGENT}
        failures = []

        for web_base in TELEGRAM_WEB_BASES:
            url = f"{web_base}/{cfg.channel}"
            try:
                response = await self.client.get(url, headers=headers, follow_redirects=True, timeout=120.0)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", 5))
                    logger.warning("Telegram rate limited for %s, retrying after %ds", cfg.channel, retry_after)
                    await asyncio.sleep(retry_after)
                    response = await self.client.get(url, headers=headers, follow_redirects=True, timeout=120.0)
                response.raise_for_status()
                html = response.text
                pages = 1
                if cfg.pages > 1:
                    html, pages = await self._with_older_pages(
                        web_base, cfg, since, html, headers
                    )
                items = self._parse_channel_html(html, cfg, since)
                report = self._channel_report(html, cfg, since, items)
                report["pages"] = pages
                self.channel_reports.append(report)
                return items
            except httpx.HTTPError as exc:
                failures.append(exc)
                logger.warning(
                    "Telegram request failed for %s via %s: [%s] %r",
                    cfg.channel,
                    web_base,
                    type(exc).__name__,
                    exc,
                )

        last_failure = failures[-1]
        raise RuntimeError(
            f"All Telegram endpoints failed for {cfg.channel}: "
            f"{type(last_failure).__name__}: {last_failure}"
        ) from last_failure

    async def _with_older_pages(
        self,
        web_base: str,
        cfg: TelegramChannelConfig,
        since: datetime,
        html: str,
        headers: dict,
    ) -> tuple[str, int]:
        """Prepend older preview pages until the window or page budget ends.

        Each page is the channel preview ``?before=<oldest post id>``. Older
        pages go first so the combined messages stay oldest-to-newest. A
        failed older page keeps what was already fetched.
        """
        older: List[str] = []
        current = html
        for _ in range(cfg.pages - 1):
            ids, oldest = self._page_bounds(current)
            if not ids or oldest is None or oldest < since:
                break
            url = f"{web_base}/{cfg.channel}?before={min(ids)}"
            try:
                response = await self.client.get(
                    url, headers=headers, follow_redirects=True, timeout=120.0
                )
                response.raise_for_status()
            except httpx.HTTPError as exc:
                logger.warning("Telegram older page failed for %s: %r", cfg.channel, exc)
                break
            page_ids, _ = self._page_bounds(response.text)
            if not page_ids or min(page_ids) >= min(ids):
                break
            older.append(response.text)
            current = response.text
        return "".join(reversed(older)) + html, 1 + len(older)

    @staticmethod
    def _page_bounds(html: str) -> tuple[List[int], Optional[datetime]]:
        """Message numbers on a preview page and its oldest timestamp."""
        soup = BeautifulSoup(html, "html.parser")
        ids: List[int] = []
        times: List[datetime] = []
        for message in soup.select("div.tgme_widget_message[data-post]"):
            try:
                ids.append(int(message["data-post"].rsplit("/", 1)[1]))
            except (KeyError, IndexError, ValueError):
                continue
            stamp = message.select_one("time[datetime]")
            try:
                times.append(
                    datetime.fromisoformat(stamp["datetime"].replace("Z", "+00:00"))
                )
            except (TypeError, KeyError, ValueError):
                continue
        return ids, (min(times) if times else None)

    @staticmethod
    def _channel_report(
        html: str, cfg: TelegramChannelConfig, since: datetime, items: List[ContentItem]
    ) -> dict:
        """Counts that explain a channel's yield, plus identity for probes.

        ``messages_seen`` 0 usually means the channel disabled its public
        preview; ``in_window`` 0 with messages seen means nothing new since
        the last window; ``kept`` below ``in_window`` means messages without
        text (media only) were skipped.
        """
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.select("div.tgme_widget_message[data-post]")
        times = []
        for message in messages[-cfg.fetch_limit:]:
            stamp = message.select_one("time[datetime]")
            try:
                times.append(
                    datetime.fromisoformat(stamp["datetime"].replace("Z", "+00:00"))
                )
            except (TypeError, KeyError, ValueError):
                continue
        title = soup.select_one(".tgme_channel_info_header_title")
        subscribers = None
        for counter in soup.select(".tgme_channel_info_counter"):
            kind = counter.select_one(".counter_type")
            value = counter.select_one(".counter_value")
            if kind and value and "subscriber" in kind.get_text().lower():
                subscribers = value.get_text(strip=True)
        return {
            "channel": cfg.channel,
            "probe": cfg.probe,
            "status": "ok",
            "title": title.get_text(" ", strip=True)[:80] if title else None,
            "subscribers": subscribers,
            "messages_seen": len(messages),
            "in_window": sum(1 for moment in times if moment >= since),
            "kept": len(items),
            "newest": max(times).isoformat() if times else None,
        }

    def _parse_channel_html(
        self, html: str, cfg: TelegramChannelConfig, since: datetime
    ) -> List[ContentItem]:
        soup = BeautifulSoup(html, "html.parser")
        messages = soup.select("div.tgme_widget_message[data-post]")

        items = []
        seen: set[str] = set()
        for msg in messages[-cfg.fetch_limit:]:
            post = msg.get("data-post")
            if post in seen:  # Adjacent preview pages can overlap.
                continue
            seen.add(post)
            item = self._parse_message(msg, cfg, since)
            if item:
                items.append(item)
        return items

    def _parse_message(
        self, msg_el, cfg: TelegramChannelConfig, since: datetime
    ) -> Optional[ContentItem]:
        channel = cfg.channel
        # Extract message ID
        data_post = msg_el.get("data-post", "")
        msg_id = data_post.split("/")[-1] if "/" in data_post else data_post
        if not msg_id:
            return None

        # Extract timestamp
        time_el = msg_el.select_one("time[datetime]")
        if not time_el:
            return None
        try:
            published_at = datetime.fromisoformat(time_el["datetime"].replace("Z", "+00:00"))
        except (ValueError, KeyError):
            return None

        if published_at < since:
            return None

        # Extract message text
        text_el = msg_el.select_one("div.tgme_widget_message_text.js-message_text")
        if not text_el:
            return None

        # Convert <br> to newlines, then strip tags
        for br in text_el.find_all("br"):
            br.replace_with("\n")
        raw_text = text_el.get_text(separator="")
        text = raw_text.strip()

        if not text:
            return None

        # Generate title from first paragraph
        title = self._make_title(text)

        # Find first external link as canonical URL; fallback to message URL
        msg_url = f"{TELEGRAM_LINK_BASE}/{channel}/{msg_id}"
        canonical_url = msg_url
        for a in text_el.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and "t.me" not in href:
                canonical_url = href
                break

        return ContentItem(
            id=self._generate_id("telegram", channel, msg_id),
            source_type=SourceType.TELEGRAM,
            title=title,
            url=canonical_url,
            content=text,
            author=channel,
            published_at=published_at,
            metadata={"msg_url": msg_url, "channel": channel, "category": cfg.category},
        )

    @staticmethod
    def _make_title(text: str) -> str:
        # Take first paragraph (split on double newline)
        first_para = text.split("\n\n")[0].replace("\n", " ").strip()

        if len(first_para) <= 80:
            return first_para

        # Try to break at a Chinese sentence-ending punctuation within first 80 chars
        match = re.search(r"[。！？]", first_para[:80])
        if match:
            return first_para[: match.end()]

        # Fallback: hard truncate
        return first_para[:80]
