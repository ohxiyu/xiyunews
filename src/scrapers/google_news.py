"""Google News RSS search scraper.

Pulls recent news articles from Google News' key-less RSS search endpoint
(https://news.google.com/rss/search) for a configured query and maps each
feed entry into a ContentItem so the rest of the xiyu.news pipeline
(deduplication, AI scoring, enrichment, summarization) treats them the same
way as RSS, Hacker News, or GDELT items.

Design notes:

* No API key is required; Google News exposes an open RSS search endpoint.
* The desired time window is expressed as a Google News query *operator*
  rather than a request parameter. ``since`` is converted to an integer
  number of hours; for windows up to 100 hours we use ``when:<hours>h``
  (Google News supports ``when:Nh`` / ``when:Nd``), and for longer windows
  we fall back to ``after:YYYY-MM-DD`` using the ``since`` date. This keeps
  the mapping deterministic and lets Google bound the result set.
* Localization is expressed through the ``hl`` (language), ``gl`` (country)
  and ``ceid`` params; ``ceid`` defaults to ``"{country}:{language}"`` when
  not configured.
* Google News headlines are usually formatted "Headline - Publisher" and the
  publisher is also exposed via ``entry.source.title``; it is captured into
  the ``source_name`` metadata key defensively.
* A single malformed entry is skipped, not allowed to abort the batch.
"""

from __future__ import annotations

import asyncio
import calendar
import hashlib
import logging
import math
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any, List, Optional

import feedparser
import httpx

from .base import BaseScraper
from .domain_filter import domain_allowed
from .google_news_url import (
    article_token,
    canonicalize_entry_link,
    resolve_google_news_url_online,
)
from ..models import ContentItem, GoogleNewsConfig, GoogleNewsQuery, SourceType

logger = logging.getLogger(__name__)


class GoogleNewsScraper(BaseScraper):
    """Scraper backed by the Google News RSS search endpoint."""

    SOURCE_TYPE = SourceType.GOOGLE_NEWS
    BASE_URL = "https://news.google.com/rss/search"

    def __init__(self, config: GoogleNewsConfig, http_client: httpx.AsyncClient):
        """Initialize the scraper.

        Args:
            config: Google News source configuration.
            http_client: Shared async HTTP client.
        """
        super().__init__({"google_news": config}, http_client)
        self.gn_config = config

    async def fetch(self, since: datetime) -> List[ContentItem]:
        """Fetch articles from the Google News RSS search endpoint.

        Args:
            since: Only fetch items published after this time (used to derive
                the Google News ``when:``/``after:`` query operator).

        Returns:
            List[ContentItem]: Fetched content items.
        """
        if not self.gn_config.enabled:
            return []

        searches = [
            GoogleNewsQuery(
                query=self.gn_config.query,
                category=self.gn_config.category,
                max_results=self.gn_config.max_results,
                blocked_domains=self.gn_config.blocked_domains,
                allowed_domains=self.gn_config.allowed_domains,
            ),
            *self.gn_config.extra_queries,
        ]
        items: List[ContentItem] = []
        seen: set[str] = set()
        for search in searches:
            for item in await self._fetch_query(search, since):
                if item.id not in seen:
                    seen.add(item.id)
                    items.append(item)
        await self._resolve_links(items)
        return items

    async def _fetch_query(
        self, search: GoogleNewsQuery, since: datetime
    ) -> List[ContentItem]:
        """One search; a failed search leaves the others unaffected."""
        base_query = (search.query or "").strip()
        if not base_query:
            return []

        query = f"{base_query} {self._time_operator(since)}"

        ceid = self.gn_config.ceid or f"{self.gn_config.country}:{self.gn_config.language}"
        params: dict[str, Any] = {
            "q": query,
            "hl": self.gn_config.language,
            "gl": self.gn_config.country,
            "ceid": ceid,
        }

        try:
            response = await self.client.get(
                self.BASE_URL, params=params, follow_redirects=True
            )
            response.raise_for_status()

            feed = feedparser.parse(response.text)

            items: List[ContentItem] = []
            dropped = 0
            for entry in feed.entries:
                if len(items) >= search.max_results:
                    break
                item = self._entry_to_item(entry, search)
                if item is None:
                    continue
                if not domain_allowed(
                    item.metadata.get("publisher_url") or item.url,
                    blocked=search.blocked_domains,
                    allowed=search.allowed_domains,
                ):
                    dropped += 1
                    continue
                items.append(item)
            if dropped:
                logger.info("Google News: dropped %d items by domain filter", dropped)
            return items

        except httpx.HTTPError as exc:
            logger.warning("Error fetching Google News feed: %s", exc)
            return []
        except Exception as exc:
            logger.warning("Error parsing Google News feed: %s", exc)
            return []

    async def _resolve_links(self, items: List[ContentItem]) -> None:
        """Replace opaque redirect links with publisher URLs where possible."""
        pending = [item for item in items if article_token(str(item.url))]
        pending = pending[: self.gn_config.resolve_links]
        if not pending:
            return
        gate = asyncio.Semaphore(4)

        async def resolve(item: ContentItem) -> bool:
            async with gate:
                url = await resolve_google_news_url_online(self.client, str(item.url))
            if not url:
                return False
            try:
                item.url = url
            except Exception:  # noqa: BLE001 - keep the redirect on any validation issue
                return False
            item.metadata["google_news_link_resolved"] = True
            return True

        results = await asyncio.gather(*(resolve(item) for item in pending))
        logger.info(
            "Google News: resolved %d/%d redirect links", sum(results), len(pending)
        )

    def _time_operator(self, since: datetime) -> str:
        """Build the Google News time operator from ``since``.

        Computes the number of whole hours between ``since`` and now (min 1).
        For windows up to 100 hours we use ``when:<hours>h``; for longer
        windows Google News' relative operator is unreliable, so we fall back
        to ``after:YYYY-MM-DD`` using the ``since`` date.
        """
        since_utc = self._ensure_utc(since)
        now_utc = datetime.now(timezone.utc)
        seconds = (now_utc - since_utc).total_seconds()
        hours = max(1, math.ceil(seconds / 3600))
        if hours <= 100:
            return f"when:{hours}h"
        return f"after:{since_utc.strftime('%Y-%m-%d')}"

    def _entry_to_item(
        self, entry: Any, search: Optional[GoogleNewsQuery] = None
    ) -> Optional[ContentItem]:
        """Map one Google News RSS entry into a ContentItem.

        Returns None when the entry has no title/link or an unparseable
        published date (published_at is required), so a single bad entry is
        skipped rather than aborting the batch.
        """
        try:
            title = (entry.get("title") or "").strip()
            if not title:
                return None

            link = (entry.get("link") or "").strip()
            if not link:
                return None
            link = canonicalize_entry_link(link)

            published = self._parse_date(entry)
            if published is None:
                return None

            source_name = self._extract_source_name(entry)
            title = self._strip_publisher_suffix(title, source_name)

            entry_id = entry.get("id") or link
            entry_hash = hashlib.sha256(str(entry_id).encode("utf-8")).hexdigest()[:16]

            meta = {
                "gn_query": search.query if search else self.gn_config.query,
                "source_name": source_name,
                "publisher_url": self._extract_publisher_url(entry),
                "category": search.category if search else self.gn_config.category,
            }

            return ContentItem(
                id=self._generate_id("google_news", "article", entry_hash),
                source_type=self.SOURCE_TYPE,
                title=title,
                url=link,
                content=self._extract_content(entry),
                author=source_name,
                published_at=published,
                metadata={k: v for k, v in meta.items() if v is not None},
            )
        except Exception as exc:
            logger.warning("Skipping invalid Google News entry: %s", exc)
            return None

    @staticmethod
    def _strip_publisher_suffix(title: str, source_name: Optional[str]) -> str:
        """Drop the " - Publisher" tail Google News appends to headlines."""
        if source_name:
            for separator in (" - ", " | ", " – "):
                tail = f"{separator}{source_name}"
                if title.endswith(tail) and len(title) > len(tail):
                    return title[: -len(tail)].rstrip()
        return title

    @staticmethod
    def _extract_publisher_url(entry: Any) -> Optional[str]:
        """Publisher homepage attached to the entry (``<source url=…>``)."""
        source = entry.get("source")
        href = source.get("href") if isinstance(source, dict) else getattr(source, "href", None)
        return str(href).strip() if href else None

    @staticmethod
    def _extract_source_name(entry: Any) -> Optional[str]:
        """Extract the publisher name from a Google News entry, guarding misses."""
        source = entry.get("source")
        if isinstance(source, dict):
            name = source.get("title")
            if name:
                return str(name).strip()
        # feedparser may expose source as an attribute-bearing object.
        title = getattr(source, "title", None)
        if title:
            return str(title).strip()
        return None

    @staticmethod
    def _parse_date(entry: Any) -> Optional[datetime]:
        """Parse the publication date of an entry into aware UTC."""
        for field in ["published", "updated", "created"]:
            if field in entry:
                try:
                    parsed = entry.get(f"{field}_parsed")
                    if parsed:
                        return datetime.fromtimestamp(
                            calendar.timegm(parsed), tz=timezone.utc
                        )
                    return parsedate_to_datetime(entry[field])
                except Exception:
                    continue
        return None

    @staticmethod
    def _extract_content(entry: Any) -> Optional[str]:
        """Extract text content from a Google News entry, if any."""
        if "summary" in entry:
            return entry.summary
        if "description" in entry:
            return entry.description
        content = entry.get("content")
        if content:
            try:
                return content[0].get("value", "")
            except Exception:
                return None
        return None

    @staticmethod
    def _ensure_utc(moment: datetime) -> datetime:
        if moment.tzinfo is None:
            return moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc)
