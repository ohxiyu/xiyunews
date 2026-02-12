"""
SSOT API Clients

Primary: Polyrouter API for most platforms
Secondary: Opinion API (direct) for Opinion platform
"""
import aiohttp
import asyncio
import time
import os


class PolyrouterAPI:
    """
    SSOT Data Source - Polyrouter API Client

    This is the ONLY allowed data source for market data.
    Supports multiple platforms: polymarket, kalshi, limitless, etc.
    """

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api-v2.polyrouter.io"
        self.headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }
        self.session = None

    async def start(self):
        """Initialize aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def get_markets(self, platform: str = "polymarket", limit: int = 50):
        """
        Fetch markets from a specific platform via Polyrouter.

        Args:
            platform: Platform ID (polymarket, kalshi, limitless, etc.)
            limit: Maximum number of markets to fetch

        Returns:
            List of market dictionaries
        """
        if not self.session:
            await self.start()

        url = f"{self.base_url}/markets"
        params = {
            "platform": platform,
            "limit": limit,
            "status": "open"
        }

        try:
            print(f"🌐 [Polyrouter] Fetching {platform} markets (limit={limit})...")
            async with self.session.get(url, params=params, headers=self.headers, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    markets = data.get("markets", [])
                    print(f"✅ [Polyrouter] Got {len(markets)} markets for {platform}")
                    return markets
                else:
                    text = await resp.text()
                    print(f"⚠️ Polyrouter API Error ({platform}): {resp.status} - {text[:200]}")
        except Exception as e:
            print(f"🔥 Polyrouter Request Failed ({platform}): {e}")
            import traceback
            traceback.print_exc()

        return []

    async def get_multi_platform_markets(
        self,
        platforms: list = None,
        limit_per_platform: int = 50
    ):
        """
        Fetch markets from multiple platforms in parallel.

        Args:
            platforms: List of platform IDs
            limit_per_platform: Maximum markets per platform

        Returns:
            Combined list of markets from all platforms
        """
        if platforms is None:
            platforms = ["polymarket", "kalshi", "limitless"]

        tasks = [self.get_markets(p, limit_per_platform) for p in platforms]
        results = await asyncio.gather(*tasks)

        all_markets = []
        for r in results:
            all_markets.extend(r)

        return all_markets

    async def get_price_history(
        self,
        market_id: str,
        platform: str = "polymarket",
        interval: str = "1h",
        limit: int = 2
    ):
        """
        Fetch price history for a specific market.

        Args:
            market_id: Market identifier
            platform: Platform ID
            interval: Time interval (1m, 5m, 1h, 4h, 1d)
            limit: Number of data points

        Returns:
            List of OHLC data points
        """
        if not self.session:
            await self.start()

        url = f"{self.base_url}/price-history"

        # Calculate timestamps
        end_ts = int(time.time())
        seconds_map = {"1m": 60, "5m": 300, "1h": 3600, "4h": 14400, "1d": 86400}
        buffer = seconds_map.get(interval, 3600) * (limit + 1)
        start_ts = end_ts - buffer

        params = {
            "market_ids": market_id,
            "platform": platform,
            "interval": interval,
            "start_ts": start_ts,
            "end_ts": end_ts
        }

        try:
            async with self.session.get(url, params=params, headers=self.headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("data", [])
                else:
                    print(f"⚠️ Polyrouter History Error ({market_id}): {resp.status}")
        except Exception as e:
            print(f"🔥 Polyrouter History failed ({market_id}): {e}")

        return []


class OpinionAPI:
    """
    Opinion Trading API Client

    Direct access to Opinion platform via their OpenAPI.
    API Docs: https://docs.opinion.trade/developer-guide/opinion-open-api
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("OPINION_API_KEY")
        self.base_url = "https://openapi.opinion.trade/openapi"
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        self.session = None

    async def start(self):
        """Initialize aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        """Close aiohttp session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def get_token_price(self, token_id: str) -> float | None:
        """
        Fetch latest price for a token.

        Args:
            token_id: The token ID (yesTokenId or noTokenId)

        Returns:
            Price as float (0-1) or None if failed
        """
        if not token_id:
            return None

        url = f"{self.base_url}/token/latest-price"
        params = {"token_id": token_id}

        try:
            async with self.session.get(url, params=params, headers=self.headers, timeout=5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("errno") == 0:
                        result = data.get("result", {})
                        price_str = result.get("price")
                        if price_str:
                            return float(price_str)
        except Exception:
            pass

        return None

    async def get_markets(self, limit: int = 20):
        """
        Fetch markets from Opinion Trading API with prices.

        Uses pagination to get up to `limit` markets (max 20 per page).
        API Parameters:
        - page: Page number (starts from 1)
        - limit: Items per page (max 20)
        - status: "activated" for open markets
        - marketType: 2 for all types (binary + categorical)
        - sortBy: 3 for volume sorting

        Args:
            limit: Maximum number of markets to fetch (target: 20)

        Returns:
            List of market dictionaries in normalized format
        """
        if not self.api_key:
            print("⚠️ [Opinion] API key not set")
            return []

        if not self.session:
            await self.start()

        url = f"{self.base_url}/market"
        all_raw_markets = []
        page = 1
        per_page = min(limit, 20)  # API max is 20 per page

        print(f"🌐 [Opinion] Fetching markets (target={limit})...")

        try:
            # Strategy: Fetch binary markets first (they have yes/no prices),
            # then fill with multi markets if needed

            async def fetch_markets_by_type(market_type: int, target: int) -> list:
                """Fetch markets of specific type with pagination"""
                markets = []
                page = 1
                type_name = "binary" if market_type == 0 else "multi"

                while len(markets) < target:
                    params = {
                        "page": page,
                        "limit": per_page,
                        "status": "activated",
                        "marketType": market_type,
                        "sortBy": 3,  # Sort by volume
                    }

                    async with self.session.get(url, params=params, headers=self.headers, timeout=30) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            if data.get("errno") == 0 or data.get("code") == 0:
                                result = data.get("result", {})
                                page_markets = result.get("list", [])
                                total = result.get("total", 0)

                                if not page_markets:
                                    break

                                markets.extend(page_markets)
                                print(f"📄 [Opinion] {type_name} page {page}: got {len(page_markets)} (total: {total})")

                                if len(markets) >= total or len(markets) >= target:
                                    break
                                page += 1
                            else:
                                break
                        else:
                            break

                return markets[:target]

            # 1. First fetch binary markets (marketType=0) - they have yes/no prices
            print(f"📊 [Opinion] Fetching binary markets first...")
            binary_markets = await fetch_markets_by_type(0, limit)
            print(f"✅ [Opinion] Got {len(binary_markets)} binary markets")

            all_raw_markets = binary_markets

            # 2. If not enough, fetch multi markets to fill the gap
            if len(all_raw_markets) < limit:
                remaining = limit - len(all_raw_markets)
                print(f"📊 [Opinion] Need {remaining} more, fetching multi markets...")
                multi_markets = await fetch_markets_by_type(1, remaining)
                print(f"✅ [Opinion] Got {len(multi_markets)} multi markets")
                all_raw_markets.extend(multi_markets)

            if not all_raw_markets:
                return []

            # Normalize and fetch prices (no additional filtering - API already filtered)
            markets = await self._normalize_markets_with_prices(all_raw_markets, limit)
            print(f"✅ [Opinion] Got {len(markets)} markets with prices")
            return markets

        except Exception as e:
            print(f"🔥 Opinion Request Failed: {e}")
            import traceback
            traceback.print_exc()

        return []

    async def _normalize_markets_with_prices(self, raw_markets: list, limit: int) -> list:
        """
        Normalize Opinion API response and fetch prices in parallel.

        Opinion API format:
        - marketId, marketTitle, status (2=Activated, 4=Resolved)
        - marketType: 0=binary, 1+=multi
        - yesTokenId, noTokenId for binary markets
        - volume, volume24h, yesLabel, noLabel

        Note: No filtering here - API already returns filtered data via status=activated param.
        We keep ALL markets returned by API (no dedup, no status filter).
        """
        # First pass: collect valid markets (no status filtering - API does it)
        filtered_markets = []
        for m in raw_markets:
            market_id = str(m.get("marketId", ""))
            title = m.get("marketTitle", "")

            # Only skip if missing required fields
            if not market_id or not title:
                continue

            filtered_markets.append(m)
            if len(filtered_markets) >= limit:
                break

        if not filtered_markets:
            return []

        # Fetch YES prices in parallel for binary markets only
        print(f"📊 [Opinion] Fetching prices for {len(filtered_markets)} markets...")

        # Build price fetch tasks: real fetch for binary markets, dummy for others
        async def get_price_or_none(m):
            """Fetch price for binary market, return None for others"""
            if m.get("marketType", 0) == 0:  # Binary market
                yes_token = m.get("yesTokenId", "")
                if yes_token:
                    return await self.get_token_price(yes_token)
            return None

        # Use asyncio.gather with return_exceptions to handle failures gracefully
        prices = await asyncio.gather(
            *[get_price_or_none(m) for m in filtered_markets],
            return_exceptions=True
        )

        # Build normalized list with prices
        normalized = []
        for i, m in enumerate(filtered_markets):
            market_id = str(m.get("marketId", ""))
            title = m.get("marketTitle", "")

            # Determine market type
            raw_market_type = m.get("marketType", 0)
            market_type = "binary" if raw_market_type == 0 else "multi"
            url_type = "binary" if raw_market_type == 0 else "multi"

            source_url = f"https://app.opinion.trade/detail?topicId={market_id}&type={url_type}"

            # Get price from parallel fetch results
            yes_price = None
            no_price = None
            if raw_market_type == 0 and i < len(prices):
                price_result = prices[i]
                if isinstance(price_result, float):
                    yes_price = price_result
                    no_price = 1.0 - yes_price

            normalized.append({
                "id": market_id,
                "platform": "opinion",
                "platform_id": market_id,
                "title": title,
                "question": title,
                "status": "open",
                "market_type": market_type,
                "current_prices": {
                    "yes": {"price": yes_price},
                    "no": {"price": no_price}
                },
                "volume_24h": float(m.get("volume24h") or 0),
                "volume_total": float(m.get("volume") or 0),
                "source_url": source_url,
                "yes_label": m.get("yesLabel", "YES"),
                "no_label": m.get("noLabel", "NO"),
                "thumbnail_url": m.get("thumbnailUrl", ""),
                "child_markets": m.get("childMarkets"),
            })

        return normalized
