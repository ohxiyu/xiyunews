"""
ReportService - Single Source of Truth (SSOT) for all report generation.

Polymarket reports use the breaking movers feed from polymarket.com/zh/breaking.

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
    price_change_24h: Optional[float] = None
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
            "price_change_24h": self.price_change_24h,
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
    generated_by: str = "polymarket-breaking"
    source_version: str = "breaking-v1"
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

    Polymarket data is restricted to the breaking movers feed.
    """

    PLATFORM_NAMES = {
        "polymarket": "Polymarket Breaking",
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
        Build a breaking report for the specified platform.

        Args:
            platform_id: Platform identifier (e.g., polymarket)
            limit: Maximum number of markets in report

        Returns:
            ReportPayload or None if fetch failed
        """
        start_time = datetime.now(timezone.utc)
        platform_name = self.PLATFORM_NAMES.get(platform_id, platform_id.title())

        print(f"📊 Building {platform_name} report...")

        try:
            # 1. Fetch breaking mover data from Polymarket.
            await self.polyrouter.start()
            fetch_limit = min(limit + 5, 25)
            raw_markets = await self.polyrouter.get_breaking_markets(
                category="all",
                limit=fetch_limit,
                locale="zh",
            )

            if not raw_markets:
                print(f"⚠️ No breaking markets returned for {platform_name}")
                return None

            print(f"📥 Fetched {len(raw_markets)} breaking markets")

            # 2. Normalize and deduplicate
            items = self._normalize_markets(raw_markets, limit)

            if not items:
                print(f"⚠️ No valid breaking markets after normalization")
                return None

            # 3. Build payload
            end_time = datetime.now(timezone.utc)
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            payload = ReportPayload(
                platform=platform_id,
                updated_at=end_time.isoformat(),
                title=f"{platform_name} - 24h Biggest Movers Top{len(items)}",
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
        """Normalize raw Polymarket breaking markets to unified format."""
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
            url = self._build_market_url(m)
            volume_24h = m.get("volume_24h") or self._event_value(m, "volume")

            items.append(MarketItem(
                rank=len(items) + 1,
                market_id=market_id,
                title=title,
                yes=yes_price,
                no=no_price,
                volume_24h=volume_24h,
                liquidity=m.get("liquidity"),
                price_change_24h=m.get("oneDayPriceChange"),
                url=url,
            ))

            if len(items) >= limit:
                break

        return items

    def _event_value(self, market: Dict, key: str):
        """Read a value from the first attached event when available."""
        events = market.get("events") or []
        if events and isinstance(events[0], dict):
            return events[0].get(key)
        return None

    def _build_market_url(self, market: Dict) -> str:
        """Build the user-facing Polymarket URL."""
        events = market.get("events") or []
        if events and isinstance(events[0], dict) and events[0].get("slug"):
            return f"https://polymarket.com/event/{events[0]['slug']}"

        slug = market.get("slug")
        if slug:
            return f"https://polymarket.com/market/{slug}"

        return market.get("source_url") or market.get("url", "")

    def _parse_prices(self, market: Dict) -> tuple:
        """Parse yes/no prices from Polymarket market data."""
        try:
            outcome_prices = market.get("outcomePrices")
            if isinstance(outcome_prices, list) and len(outcome_prices) >= 2:
                yes_price = round(float(outcome_prices[0]), 4)
                no_price = round(float(outcome_prices[1]), 4)
                return yes_price, no_price

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
        """Format report payload for Telegram push."""
        lines = []

        platform_name = self.PLATFORM_NAMES.get(payload.platform, payload.platform.title())
        lines.append(f"🔥 {platform_name} Top{payload.items_count}")
        lines.append("过去 24 小时波动最大")
        lines.append(f"⏰ {payload.updated_at[:16].replace('T', ' ')} UTC\n")

        for item in payload.items:
            rank = item.get("rank", "?")
            title = item.get("title", "Unknown")
            url = item.get("url", "")
            change = item.get("price_change_24h")

            msg = f"#{rank} {title}"
            if change is not None:
                msg += f"\n24h: {change:+.1%}"
            if url:
                msg += f"\n🔗 {url}"

            lines.append(msg)

        return "\n\n".join(lines)
