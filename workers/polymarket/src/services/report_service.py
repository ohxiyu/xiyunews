"""
ReportService - Single Source of Truth (SSOT) for all report generation.

All data flows through Polyrouter API as the ONLY data source.

Architecture:
    PolyrouterAPI -> ReportService -> ReportPayload -> Storage/Telegram/API
"""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .api import PolyrouterAPI


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
        }


@dataclass
class ReportPayload:
    """Report payload with SSOT fingerprint."""
    platform: str
    updated_at: str
    title: str
    items: List[Dict[str, Any]]
    items_count: int
    generation_time_ms: int
    report_id: str = ""
    generated_by: str = "polyrouter"
    source_version: str = "v2"
    lang: str = "zh"
    source: str = "realtime"

    def __post_init__(self):
        if not self.report_id:
            self.report_id = self._generate_report_id()

    def _generate_report_id(self) -> str:
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
            "lang": self.lang,
            "source": self.source,
        }


class ReportService:
    """
    Single Source of Truth (SSOT) Report Service.

    ALL data MUST come from Polyrouter API.
    """

    PLATFORM_NAMES = {
        "polymarket": "Polymarket",
    }

    def __init__(
        self,
        polyrouter_api: PolyrouterAPI,
        storage: Any = None,
    ):
        self.polyrouter = polyrouter_api
        self.storage = storage

    async def build_latest_report(
        self,
        platform_id: str,
        limit: int = 8,
    ) -> Optional[ReportPayload]:
        """
        Build a report for the specified platform using Polyrouter.

        Args:
            platform_id: Platform identifier (e.g., polymarket)
            limit: Maximum number of markets in report

        Returns:
            ReportPayload or None if fetch failed
        """
        start_time = datetime.now(timezone.utc)
        platform_name = self.PLATFORM_NAMES.get(platform_id, platform_id.title())

        print(f"📊 Building {platform_name} report via Polyrouter...")

        try:
            # 1. Fetch market data from Polyrouter
            await self.polyrouter.start()
            fetch_limit = min(limit + 5, 25)
            raw_markets = await self.polyrouter.get_markets(
                platform=platform_id,
                limit=fetch_limit
            )

            if not raw_markets:
                print(f"⚠️ No markets returned from Polyrouter for {platform_name}")
                return None

            print(f"📥 Fetched {len(raw_markets)} markets from Polyrouter")

            # 2. Normalize and deduplicate
            items = self._normalize_markets(raw_markets, limit)

            if not items:
                print(f"⚠️ No valid markets after normalization")
                return None

            # 3. Build payload
            end_time = datetime.now(timezone.utc)
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            payload = ReportPayload(
                platform=platform_id,
                updated_at=end_time.isoformat(),
                title=f"{platform_name} - Trending Top{len(items)}",
                items=[item.to_dict() for item in items],
                items_count=len(items),
                generation_time_ms=generation_time_ms,
            )

            # 4. Persist to storage (optional)
            if self.storage:
                try:
                    await self.storage.save_report(platform_id, payload.to_dict())
                    print(f"💾 Saved report for {platform_name}")
                except Exception as e:
                    print(f"⚠️ Failed to save report: {e}")

            print(f"✅ Built {platform_name} report: {len(items)} items, "
                  f"report_id={payload.report_id}, {generation_time_ms}ms")

            return payload

        except Exception as e:
            print(f"🔥 Failed to build {platform_name} report: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _normalize_markets(
        self,
        raw_markets: List[Dict],
        limit: int,
    ) -> List[MarketItem]:
        """Normalize raw Polyrouter markets to unified format."""
        seen_ids = set()
        items = []

        for m in raw_markets:
            market_id = str(m.get("id") or m.get("platform_id") or m.get("slug", ""))
            if not market_id:
                continue

            if market_id in seen_ids:
                continue
            seen_ids.add(market_id)

            title = m.get("title") or m.get("question") or m.get("event_name", "")
            if not title:
                continue

            yes_price, no_price = self._parse_prices(m)
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
        """Parse yes/no prices from Polyrouter market data."""
        try:
            prices = market.get("current_prices", {})
            if not prices:
                return None, None

            yes_price = None
            no_price = None

            for key, val in prices.items():
                if isinstance(val, dict):
                    price = val.get("price")
                    if key.lower() in ("yes", "up"):
                        yes_price = price
                    elif key.lower() in ("no", "down"):
                        no_price = price

            if yes_price is not None and no_price is not None:
                yes_price = round(yes_price, 4)
                no_price = round(no_price, 4)

                total = yes_price + no_price
                if 0.95 <= total <= 1.05:
                    if total != 1.0:
                        no_price = round(1.0 - yes_price, 4)
                elif total < 0.1:
                    return None, None

            if yes_price is not None and no_price is None:
                no_price = round(1.0 - yes_price, 4)
            elif no_price is not None and yes_price is None:
                yes_price = round(1.0 - no_price, 4)

            if yes_price is not None and not (0 <= yes_price <= 1):
                yes_price = None
            if no_price is not None and not (0 <= no_price <= 1):
                no_price = None

            return yes_price, no_price
        except Exception:
            return None, None

    def format_for_telegram(self, payload: ReportPayload) -> str:
        """Format report payload for Telegram push. Title + link only."""
        lines = []

        platform_name = self.PLATFORM_NAMES.get(payload.platform, payload.platform.title())
        lines.append(f"🔥 {platform_name} Top{payload.items_count}")
        lines.append(f"⏰ {payload.updated_at[:16].replace('T', ' ')} UTC\n")

        for item in payload.items:
            rank = item.get("rank", "?")
            title = item.get("title", "Unknown")
            url = item.get("url", "")

            msg = f"#{rank} {title}"
            if url:
                msg += f"\n🔗 {url}"

            lines.append(msg)

        return "\n\n".join(lines)
