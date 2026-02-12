"""
ReportService - Single Source of Truth (SSOT) for all report generation.

All data flows through Polyrouter API as the ONLY data source.
Both Web API and Telegram bot MUST use this service.

Architecture:
    PolyrouterAPI -> ReportService -> ReportPayload -> Storage/Telegram/API
"""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field

from .api import PolyrouterAPI, OpinionAPI


@dataclass
class MarketItem:
    """Unified market item structure."""
    rank: int
    market_id: str
    title: str
    yes: Optional[float] = None
    no: Optional[float] = None
    volume_24h: Optional[float] = None
    liquidity: Optional[float] = None
    url: str = ""
    summary: Optional[str] = None
    summary_zh: Optional[str] = None
    summary_en: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "market_id": self.market_id,
            "title": self.title,
            "yes": self.yes,
            "no": self.no,
            "volume_24h": self.volume_24h,
            "liquidity": self.liquidity,
            "url": self.url,
            "summary": self.summary,
            "summary_zh": self.summary_zh,
            "summary_en": self.summary_en,
        }


@dataclass
class ReportPayload:
    """
    Report payload with SSOT fingerprint.

    The report_id is a hash that allows verification that
    Web and Telegram are using the same data.
    """
    platform: str
    updated_at: str
    title: str
    items: List[Dict[str, Any]]
    items_count: int
    generation_time_ms: int
    report_id: str = ""  # SSOT fingerprint
    generated_by: str = "polyrouter"  # Always polyrouter
    source_version: str = "v2"
    degraded: bool = False
    lang: str = "zh"
    source: str = "realtime"  # Data source: 'polyfill-{platform}', 'realtime', 'storage'

    def __post_init__(self):
        """Generate report_id fingerprint after initialization."""
        if not self.report_id:
            self.report_id = self._generate_report_id()

    def _generate_report_id(self) -> str:
        """
        Generate a unique fingerprint for this report.

        Format: hash(platform + updated_at + top1_market_id)
        This allows verification that Web and Telegram use the same data.
        """
        top1_id = self.items[0]["market_id"] if self.items else "empty"
        raw = f"{self.platform}|{self.updated_at}|{top1_id}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "updated_at": self.updated_at,
            "title": self.title,
            "items": self.items,
            "items_count": self.items_count,
            "generation_time_ms": self.generation_time_ms,
            "report_id": self.report_id,
            "generated_by": self.generated_by,
            "source_version": self.source_version,
            "degraded": self.degraded,
            "lang": self.lang,
            "source": self.source,
        }


class ReportService:
    """
    Single Source of Truth (SSOT) Report Service.

    ALL data MUST come from Polyrouter API.
    No direct access to third-party platforms (polymarket.com, kalshi, etc.)
    """

    # Platform display names
    PLATFORM_NAMES = {
        "polymarket": "Polymarket",
        "kalshi": "Kalshi",
        "limitless": "Limitless",
        "manifold": "Manifold",
        "metaculus": "Metaculus",
        "opinion": "Opinion",
    }

    # Platform polyfill mapping (for platforms not yet in Polyrouter)
    # Maps to the platform that should be used as data source
    PLATFORM_POLYFILL = {
        # Opinion now uses its own API directly
    }

    def __init__(
        self,
        polyrouter_api: PolyrouterAPI,
        ai_service: Any = None,
        storage: Any = None,
        opinion_api: OpinionAPI = None
    ):
        """
        Initialize ReportService.

        Args:
            polyrouter_api: PolyrouterAPI instance (REQUIRED - the ONLY data source)
            ai_service: Optional AI service for summary generation
            storage: Optional storage repository for persistence
            opinion_api: Optional OpinionAPI instance for Opinion platform
        """
        self.polyrouter = polyrouter_api
        self.ai = ai_service
        self.storage = storage
        self.opinion_api = opinion_api

    async def build_latest_report(
        self,
        platform_id: str,
        limit: int = 20,
        lang: str = "zh",
        with_ai: bool = True,
    ) -> Optional[ReportPayload]:
        """
        Build a report for the specified platform using Polyrouter ONLY.

        This is the SINGLE ENTRY POINT for all report generation.
        Both Web API and Telegram MUST call this method.

        Args:
            platform_id: Platform identifier (polymarket, kalshi, etc.)
            limit: Maximum number of markets in report
            lang: Language for AI summaries (zh or en)
            with_ai: Whether to generate AI summaries

        Returns:
            ReportPayload or None if fetch failed
        """
        start_time = datetime.now(timezone.utc)
        platform_name = self.PLATFORM_NAMES.get(platform_id, platform_id.title())

        # Check if platform needs polyfill
        actual_platform = self.PLATFORM_POLYFILL.get(platform_id, platform_id)
        is_polyfill = actual_platform != platform_id

        # Special handling for Opinion platform - use direct API
        use_opinion_api = platform_id == "opinion" and self.opinion_api is not None

        if use_opinion_api:
            print(f"📊 [SSOT] Building {platform_name} report via Opinion API...")
        elif is_polyfill:
            print(f"📊 [SSOT] Building {platform_name} report via polyfill ({actual_platform})...")
        else:
            print(f"📊 [SSOT] Building {platform_name} report via Polyrouter...")

        try:
            # 1. Fetch market data
            if use_opinion_api:
                # Use Opinion's direct API with pagination
                # API supports: page, limit (max 20), status=activated, marketType=2
                # User requirement: show all Opinion API data without filtering/dedup
                await self.opinion_api.start()
                raw_markets = await self.opinion_api.get_markets(limit=limit)
            else:
                # Use Polyrouter for other platforms
                await self.polyrouter.start()
                # Note: Some platforms (limitless, kalshi) have API limits
                # Use min(limit+5, 25) to avoid hitting rate limits while allowing dedup
                fetch_limit = min(limit + 5, 25)
                raw_markets = await self.polyrouter.get_markets(
                    platform=actual_platform,  # Use actual platform for polyfill
                    limit=fetch_limit
                )

            if not raw_markets:
                source_name = "Opinion API" if use_opinion_api else "Polyrouter"
                print(f"⚠️ [SSOT] No markets returned from {source_name} for {platform_name}")
                return None

            source_name = "Opinion API" if use_opinion_api else "Polyrouter"
            print(f"📥 [SSOT] Fetched {len(raw_markets)} markets from {source_name}")

            # 2. Normalize and deduplicate
            items = self._normalize_markets(raw_markets, limit, platform_id)

            if not items:
                print(f"⚠️ [SSOT] No valid markets after normalization")
                return None

            # 3. Generate AI summaries (optional)
            degraded = False
            if with_ai and self.ai:
                items, degraded = await self._generate_summaries(items, platform_name, lang)

            # 4. Build payload with SSOT fingerprint
            end_time = datetime.now(timezone.utc)
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            # Determine source type
            if use_opinion_api:
                source = "opinion-api"
            elif is_polyfill:
                source = f"polyfill-{actual_platform}"
            else:
                source = "realtime"

            payload = ReportPayload(
                platform=platform_id,
                updated_at=end_time.isoformat(),
                title=f"{platform_name} - Trending Top{len(items)}",
                items=[item.to_dict() for item in items],
                items_count=len(items),
                generation_time_ms=generation_time_ms,
                degraded=degraded,
                lang=lang,
                generated_by="polyrouter",  # SSOT marker
                source=source,  # Track data source for polyfill
            )

            # 5. Persist to storage (optional)
            if self.storage:
                try:
                    await self.storage.save_report(platform_id, payload.to_dict())
                    print(f"💾 [SSOT] Saved report for {platform_name}")
                except Exception as e:
                    print(f"⚠️ [SSOT] Failed to save report: {e}")

            print(f"✅ [SSOT] Built {platform_name} report: {len(items)} items, "
                  f"report_id={payload.report_id}, {generation_time_ms}ms")

            return payload

        except Exception as e:
            print(f"🔥 [SSOT] Failed to build {platform_name} report: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _normalize_markets(
        self,
        raw_markets: List[Dict],
        limit: int,
        platform_id: str,
    ) -> List[MarketItem]:
        """
        Normalize raw Polyrouter markets to unified format.

        Note: Deduplication is skipped for Opinion platform to show all API data.
        """
        seen_ids = set()
        items = []

        # Skip deduplication for Opinion - show all API data as-is
        skip_dedup = (platform_id == "opinion")

        for m in raw_markets:
            # Get market ID
            market_id = str(m.get("id") or m.get("platform_id") or m.get("slug", ""))
            if not market_id:
                continue

            # Deduplication (skipped for Opinion)
            if not skip_dedup:
                if market_id in seen_ids:
                    continue
                seen_ids.add(market_id)

            # Get title
            title = m.get("title") or m.get("question") or m.get("event_name", "")
            if not title:
                continue

            # Parse prices
            yes_price, no_price = self._parse_prices(m)

            # Get URL
            url = m.get("source_url") or m.get("url", "")

            items.append(MarketItem(
                rank=len(items) + 1,
                market_id=market_id,
                title=title,
                yes=yes_price,
                no=no_price,
                volume_24h=m.get("volume_24h"),
                liquidity=m.get("liquidity"),
                url=url,
            ))

            if len(items) >= limit:
                break

        return items

    def _parse_prices(self, market: Dict) -> tuple:
        """
        Parse yes/no prices from Polyrouter market data.

        Includes validation to ensure prices are sensible:
        - yes + no should approximately equal 1.0
        - Prices should be between 0 and 1
        - Handles floating point precision issues
        """
        try:
            prices = market.get("current_prices", {})
            if not prices:
                return None, None

            # Polyrouter format: {"yes": {"price": 0.65}, "no": {"price": 0.35}}
            # or {"up": {"price": 0.5}, "down": {"price": 0.5}}
            yes_price = None
            no_price = None

            for key, val in prices.items():
                if isinstance(val, dict):
                    price = val.get("price")
                    if key.lower() in ("yes", "up"):
                        yes_price = price
                    elif key.lower() in ("no", "down"):
                        no_price = price

            # Validate and fix prices
            if yes_price is not None and no_price is not None:
                # Round to avoid floating point precision issues
                yes_price = round(yes_price, 4)
                no_price = round(no_price, 4)

                # Check if prices sum to approximately 1.0
                total = yes_price + no_price
                if 0.95 <= total <= 1.05:
                    # Valid prices, normalize to exactly 1.0
                    if total != 1.0:
                        no_price = round(1.0 - yes_price, 4)
                elif total < 0.1:
                    # Prices too low (e.g., Limitless low-liquidity markets)
                    # These are likely invalid, return None
                    return None, None
                # else: keep as-is for edge cases

            # Compute complement if one is missing
            if yes_price is not None and no_price is None:
                no_price = round(1.0 - yes_price, 4)
            elif no_price is not None and yes_price is None:
                yes_price = round(1.0 - no_price, 4)

            # Final validation: prices should be between 0 and 1
            if yes_price is not None and not (0 <= yes_price <= 1):
                yes_price = None
            if no_price is not None and not (0 <= no_price <= 1):
                no_price = None

            return yes_price, no_price
        except Exception:
            return None, None

    async def _generate_summaries(
        self,
        items: List[MarketItem],
        platform_name: str,
        lang: str,
    ) -> tuple:
        """Generate AI summaries for market items."""
        if not self.ai:
            return items, True

        try:
            # Format items for AI
            formatted = []
            for item in items:
                text = f"#{item.rank} {item.title}"
                if item.yes is not None:
                    text += f" | Yes: {item.yes*100:.1f}%"
                if item.volume_24h:
                    vol = item.volume_24h
                    if vol >= 1_000_000:
                        text += f" | Vol: ${vol/1_000_000:.1f}M"
                    elif vol >= 1_000:
                        text += f" | Vol: ${vol/1_000:.0f}K"
                formatted.append(text)

            # Call AI service
            result = await self.ai.rewrite_trending_report(
                formatted,
                platform=platform_name,
                lang=lang,
            )

            if not result:
                return items, True

            # Parse summaries
            summaries = []
            for line in result.split("\n"):
                line = line.strip()
                if line.startswith("💡"):
                    summaries.append(line[1:].strip())
                elif line.startswith("#") and "💡" in line:
                    parts = line.split("💡")
                    if len(parts) > 1:
                        summaries.append(parts[1].strip())

            # Assign summaries
            for i, item in enumerate(items):
                if i < len(summaries):
                    item.summary = summaries[i]
                    # Store language-specific summary
                    if lang == "zh":
                        item.summary_zh = summaries[i]
                    else:
                        item.summary_en = summaries[i]

            return items, False

        except Exception as e:
            print(f"⚠️ [SSOT] AI summary generation failed: {e}")
            return items, True

    def format_for_telegram(self, payload: ReportPayload) -> str:
        """
        Format report payload for Telegram push.

        Uses the SAME payload as Web API to ensure consistency.
        Includes report_id for verification.
        """
        lines = []

        # Header (plain text to avoid Telegram Markdown parsing issues)
        platform_name = self.PLATFORM_NAMES.get(payload.platform, payload.platform.title())
        lines.append(f"🔥 {platform_name} 热榜 Top{payload.items_count} 🔥")
        lines.append(f"📍 平台：{platform_name}")
        lines.append(f"⏰ {payload.updated_at[:16].replace('T', ' ')} UTC")
        lines.append(f"🔑 ID: {payload.report_id}")
        lines.append("实时赔率 · 专业解读\n")

        # Items
        for item in payload.items:
            rank = item.get("rank", "?")
            title = item.get("title", "Unknown")
            yes = item.get("yes")
            no = item.get("no")
            vol = item.get("volume_24h")
            url = item.get("url", "")
            summary = item.get("summary")

            # Format odds
            if yes is not None and no is not None:
                odds_str = f"Yes {yes*100:.1f}% / No {no*100:.1f}%"
            elif yes is not None:
                odds_str = f"Yes {yes*100:.1f}%"
            else:
                odds_str = "N/A"

            # Format volume
            if vol is not None and vol > 0:
                if vol >= 1_000_000:
                    vol_str = f"${vol/1_000_000:.1f}M"
                elif vol >= 1_000:
                    vol_str = f"${vol/1_000:.0f}K"
                else:
                    vol_str = f"${vol:.0f}"
            else:
                vol_str = "N/A"

            # Build message (plain text format)
            msg = f"#{rank} ❓ {title}\n"
            msg += f"📊 赔率：{odds_str}\n"
            msg += f"💰 24h交易量：{vol_str}\n"
            if summary:
                msg += f"💡 {summary}\n"
            msg += f"🔗 {url}"

            lines.append(msg)

        return "\n\n".join(lines)
