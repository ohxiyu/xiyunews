"""
SSOT API Client

Primary: Polyrouter API for Polymarket data.
"""
import aiohttp
import asyncio
import time
import os


class PolyrouterAPI:
    """
    SSOT Data Source - Polyrouter API Client

    This is the ONLY allowed data source for market data.
    Supports Polymarket platform via Polyrouter aggregator.
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
            platform: Platform ID (e.g., polymarket)
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
            platforms = ["polymarket"]

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
