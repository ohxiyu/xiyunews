"""Build and format Polymarket breaking reports."""

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .api import PolymarketAPI


@dataclass
class MarketItem:
    rank: int
    market_id: str
    title: str
    yes: float | None = None
    no: float | None = None
    volume_24h: float | None = None
    liquidity: float | None = None
    price_change_24h: float | None = None
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
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
    platform: str
    updated_at: str
    title: str
    items: list[dict[str, Any]]
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

    def to_dict(self) -> dict[str, Any]:
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
    PLATFORM = "polymarket"
    PLATFORM_NAME = "Polymarket Breaking"

    def __init__(self, polymarket_api: PolymarketAPI, storage: Any = None):
        self.polymarket = polymarket_api
        self.storage = storage

    async def build_latest_report(self, limit: int = 8) -> ReportPayload | None:
        start_time = datetime.now(timezone.utc)
        print(f"📊 Building {self.PLATFORM_NAME} report...")

        try:
            await self.polymarket.start()
            raw_markets = await self.polymarket.get_breaking_markets(
                category="all",
                limit=min(limit + 5, 25),
                locale="zh",
            )

            if not raw_markets:
                print(f"⚠️ No breaking markets returned for {self.PLATFORM_NAME}")
                return None

            items = self._normalize_markets(raw_markets, limit)
            if not items:
                print("⚠️ No valid breaking markets after normalization")
                return None

            end_time = datetime.now(timezone.utc)
            generation_time_ms = int((end_time - start_time).total_seconds() * 1000)

            payload = ReportPayload(
                platform=self.PLATFORM,
                updated_at=end_time.isoformat(),
                title=f"{self.PLATFORM_NAME} - 24h Biggest Movers Top{len(items)}",
                items=[item.to_dict() for item in items],
                items_count=len(items),
                generation_time_ms=generation_time_ms,
            )

            if self.storage:
                try:
                    await self.storage.save_report(self.PLATFORM, payload.to_dict())
                    print(f"💾 Saved report for {self.PLATFORM_NAME}")
                except Exception as e:
                    print(f"⚠️ Failed to save report: {e}")

            print(f"✅ Built {self.PLATFORM_NAME} report: {len(items)} items, report_id={payload.report_id}, {generation_time_ms}ms")
            return payload
        except Exception as e:
            print(f"🔥 Failed to build {self.PLATFORM_NAME} report: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _normalize_markets(self, raw_markets: list[dict], limit: int) -> list[MarketItem]:
        seen_ids = set()
        items = []

        for market in raw_markets:
            market_id = str(market.get("id") or market.get("slug") or "")
            title = market.get("question") or market.get("title") or ""
            if not market_id or not title or market_id in seen_ids:
                continue

            seen_ids.add(market_id)
            yes_price, no_price = self._parse_prices(market)

            items.append(MarketItem(
                rank=len(items) + 1,
                market_id=market_id,
                title=title,
                yes=yes_price,
                no=no_price,
                volume_24h=self._event_value(market, "volume"),
                liquidity=market.get("liquidity"),
                price_change_24h=market.get("oneDayPriceChange"),
                url=self._build_market_url(market),
            ))

            if len(items) >= limit:
                break

        return items

    def _event_value(self, market: dict, key: str):
        events = market.get("events") or []
        if events and isinstance(events[0], dict):
            return events[0].get(key)
        return None

    def _build_market_url(self, market: dict) -> str:
        events = market.get("events") or []
        if events and isinstance(events[0], dict) and events[0].get("slug"):
            return f"https://polymarket.com/event/{events[0]['slug']}"

        slug = market.get("slug")
        return f"https://polymarket.com/market/{slug}" if slug else ""

    def _parse_prices(self, market: dict) -> tuple[float | None, float | None]:
        outcome_prices = market.get("outcomePrices")
        if not isinstance(outcome_prices, list) or len(outcome_prices) < 2:
            return None, None

        try:
            return round(float(outcome_prices[0]), 4), round(float(outcome_prices[1]), 4)
        except (TypeError, ValueError):
            return None, None

    def format_for_telegram(self, payload: ReportPayload) -> str:
        lines = [
            f"🔥 {self.PLATFORM_NAME} Top{payload.items_count}",
            "过去 24 小时波动最大",
            f"⏰ {payload.updated_at[:16].replace('T', ' ')} UTC\n",
        ]

        for item in payload.items:
            msg = f"#{item.get('rank', '?')} {item.get('title', 'Unknown')}"
            change = item.get("price_change_24h")
            if change is not None:
                msg += f"\n24h: {change:+.1%}"
            if item.get("url"):
                msg += f"\n🔗 {item['url']}"
            lines.append(msg)

        return "\n\n".join(lines)
