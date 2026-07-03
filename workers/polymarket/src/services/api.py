"""Polymarket breaking movers API client."""
import aiohttp


class PolymarketAPI:
    """Client for the feed behind https://polymarket.com/zh/breaking."""

    def __init__(self):
        self.base_url = "https://polymarket.com"
        self.session: aiohttp.ClientSession | None = None

    async def start(self):
        if not self.session:
            self.session = aiohttp.ClientSession()

    async def close(self):
        if self.session:
            await self.session.close()
            self.session = None

    async def get_breaking_markets(
        self,
        category: str = "all",
        limit: int = 50,
        locale: str = "zh",
    ) -> list[dict]:
        """Fetch markets with the largest price moves over the last 24 hours."""
        if not self.session:
            await self.start()

        url = f"{self.base_url}/api/biggest-movers"
        params = {"category": category, "locale": locale}

        try:
            print(f"🌐 [Polymarket] Fetching breaking movers (category={category}, limit={limit})...")
            async with self.session.get(url, params=params, timeout=30) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    markets = data.get("markets", [])[:limit]
                    print(f"✅ [Polymarket] Got {len(markets)} breaking movers")
                    return markets

                text = await resp.text()
                print(f"⚠️ Polymarket Breaking API Error: {resp.status} - {text[:200]}")
        except Exception as e:
            print(f"🔥 Polymarket Breaking request failed: {e}")
            import traceback
            traceback.print_exc()

        return []
