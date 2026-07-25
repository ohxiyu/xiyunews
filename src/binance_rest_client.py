"""
Binance REST API Client Module

Provides HTTP clients for Binance Spot and Futures REST APIs
with retry logic, rate limiting, and connection pooling.
"""

import asyncio
import logging
from typing import Any, cast

import aiohttp

logger = logging.getLogger("coinsignal.binance")


class BinanceAPIError(Exception):
    """Custom exception for Binance API errors"""


class BinanceRESTClient:
    """
    Base class for Binance REST API clients.

    Features:
    - aiohttp session with connection pooling
    - Semaphore for concurrency control
    - Exponential backoff retry logic
    - Request timeout handling
    """

    def __init__(self, base_url: str, max_concurrent: int = 50) -> None:
        """
        Initialize REST client.

        Args:
            base_url: API base URL (e.g., "https://api.binance.com")
            max_concurrent: Maximum concurrent requests (default: 50)
        """
        self.base_url = base_url
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session: aiohttp.ClientSession | None = None
        self.timeout = aiohttp.ClientTimeout(total=10, connect=5)
        self.max_retries = 3
        self.retry_delay = 1  # seconds

        logger.info(
            "Initialized %s (base_url=%s, max_concurrent=%s)",
            self.__class__.__name__,
            base_url,
            max_concurrent,
        )

    async def init_session(self) -> None:
        """Initialize aiohttp session with connection pooling"""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,  # Total connection limit
                limit_per_host=30,  # Per-host limit
                ttl_dns_cache=300,  # DNS cache TTL
            )
            self.session = aiohttp.ClientSession(connector=connector, timeout=self.timeout)
            logger.info(f"{self.__class__.__name__} session initialized")

    async def close(self) -> None:
        """Close aiohttp session"""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
            logger.info(f"{self.__class__.__name__} session closed")

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Any:
        """
        Generic HTTP request with retry logic.

        Retries on:
        - HTTP 429 (Rate Limit)
        - HTTP 5xx (Server Errors)
        - Network timeout

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional arguments for aiohttp request

        Returns:
            JSON response as dict

        Raises:
            BinanceAPIError: If all retries fail
        """
        if self.session is None:
            raise RuntimeError("Binance client session is not initialized")

        async with self.semaphore:  # Rate limiting via semaphore
            for attempt in range(self.max_retries):
                try:
                    async with self.session.request(method, url, **kwargs) as resp:
                        # Check HTTP status
                        if resp.status == 200:
                            return await resp.json()

                        elif resp.status in [429, 500, 502, 503, 504]:
                            # Retryable errors
                            error_msg = await resp.text()
                            logger.warning(
                                "HTTP %s on %s (attempt %s/%s): %s",
                                resp.status,
                                url,
                                attempt + 1,
                                self.max_retries,
                                error_msg[:100],
                            )

                            if attempt < self.max_retries - 1:
                                # Exponential backoff: 1s, 2s, 4s
                                delay = self.retry_delay * (2**attempt)
                                await asyncio.sleep(delay)
                                continue
                            else:
                                raise BinanceAPIError(
                                    f"HTTP {resp.status} after {self.max_retries} retries"
                                )

                        else:
                            # Non-retryable error
                            error_msg = await resp.text()
                            raise BinanceAPIError(f"HTTP {resp.status}: {error_msg[:200]}")

                except TimeoutError as exc:
                    logger.warning(f"Timeout on {url} (attempt {attempt + 1}/{self.max_retries})")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2**attempt))
                        continue
                    else:
                        raise BinanceAPIError(f"Timeout after {self.max_retries} retries") from exc

                except aiohttp.ClientError as e:
                    logger.warning(
                        f"Client error on {url}: {e} (attempt {attempt + 1}/{self.max_retries})"
                    )
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (2**attempt))
                        continue
                    else:
                        raise BinanceAPIError(
                            f"Client error after {self.max_retries} retries: {e}"
                        ) from e

        # Should not reach here
        raise BinanceAPIError("Unexpected error in _request_with_retry")


class BinanceSpotClient(BinanceRESTClient):
    """
    Binance Spot REST API client.

    Endpoints:
    - GET /api/v3/ticker/24hr
    - GET /api/v3/klines
    """

    def __init__(self, max_concurrent: int = 50):
        super().__init__("https://api.binance.com", max_concurrent)

    async def get_24hr_tickers(self) -> list[dict[str, Any]]:
        """
        Get 24-hour ticker data for all symbols.

        Returns only USDT pairs with quoteVolume > 0.

        Returns:
            List of ticker dicts with keys: symbol, quoteVolume, priceChange, etc.

        Example:
            [
                {'symbol': 'BTCUSDT', 'quoteVolume': '1234567890', 'priceChange': '123.45', ...},
                {'symbol': 'ETHUSDT', 'quoteVolume': '9876543210', ...},
                ...
            ]

        Raises:
            BinanceAPIError: If API request fails
        """
        url = f"{self.base_url}/api/v3/ticker/24hr"

        try:
            data = await self._request_with_retry("GET", url)

            # Filter USDT pairs with quoteVolume > 0
            usdt_pairs = [
                ticker
                for ticker in data
                if ticker.get("symbol", "").endswith("USDT")
                and float(ticker.get("quoteVolume", 0)) > 0
            ]

            logger.info(f"Fetched {len(usdt_pairs)} USDT spot tickers (total: {len(data)})")
            return usdt_pairs

        except Exception as e:
            logger.error(f"Failed to fetch spot 24hr tickers: {e}")
            raise BinanceAPIError(f"Failed to fetch spot tickers: {e}") from e

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 4,
    ) -> list[list[Any]]:
        """
        Get klines (candlestick) data for a symbol.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            interval: Kline interval (default: "1m")
            limit: Number of klines to fetch (default: 4)

        Returns:
            List of klines, each kline is a list:
            [open_time, open, high, low, close, volume, close_time, quote_volume, ...]

            Close price is at index [4]

        Example:
            [
                [1609459200000, "29000", "29500", "28900", "29300", "123.45", ...],
                [1609459260000, "29300", "29400", "29200", "29350", "98.76", ...],
                [1609459320000, "29350", "29600", "29300", "29500", "145.23", ...],
                [1609459380000, "29500", "29700", "29450", "29650", "167.89", ...]
            ]

        Raises:
            BinanceAPIError: If API request fails
        """
        url = f"{self.base_url}/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}

        try:
            data = await self._request_with_retry("GET", url, params=params)

            if not data or len(data) < limit:
                logger.debug(
                    "%s: insufficient klines data (got %s, need %s)",
                    symbol,
                    len(data) if data else 0,
                    limit,
                )
                return []

            return cast(list[list[Any]], data)

        except Exception as e:
            logger.debug(f"Failed to fetch klines for {symbol}: {e}")
            return []


class BinanceFuturesClient(BinanceRESTClient):
    """
    Binance USDⓈ-M Futures REST API client.

    Endpoints:
    - GET /fapi/v1/ticker/24hr
    - GET /fapi/v1/klines
    """

    def __init__(self, max_concurrent: int = 50):
        super().__init__("https://fapi.binance.com", max_concurrent)

    async def get_24hr_tickers(self) -> list[dict[str, Any]]:
        """
        Get 24-hour ticker data for all futures symbols.

        Returns only USDT pairs with quoteVolume > 0.

        Returns:
            List of ticker dicts with keys: symbol, quoteVolume, priceChange, etc.

        Example:
            [
                {'symbol': 'BTCUSDT', 'quoteVolume': '1234567890', 'priceChange': '123.45', ...},
                {'symbol': 'ETHUSDT', 'quoteVolume': '9876543210', ...},
                ...
            ]

        Raises:
            BinanceAPIError: If API request fails
        """
        url = f"{self.base_url}/fapi/v1/ticker/24hr"

        try:
            data = await self._request_with_retry("GET", url)

            # Filter USDT pairs with quoteVolume > 0
            usdt_pairs = [
                ticker
                for ticker in data
                if ticker.get("symbol", "").endswith("USDT")
                and float(ticker.get("quoteVolume", 0)) > 0
            ]

            logger.info(f"Fetched {len(usdt_pairs)} USDT futures tickers (total: {len(data)})")
            return usdt_pairs

        except Exception as e:
            logger.error(f"Failed to fetch futures 24hr tickers: {e}")
            raise BinanceAPIError(f"Failed to fetch futures tickers: {e}") from e

    async def get_klines(
        self,
        symbol: str,
        interval: str = "1m",
        limit: int = 4,
    ) -> list[list[Any]]:
        """
        Get klines (candlestick) data for a futures symbol.

        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            interval: Kline interval (default: "1m")
            limit: Number of klines to fetch (default: 4)

        Returns:
            List of klines, each kline is a list:
            [open_time, open, high, low, close, volume, close_time, quote_volume, ...]

            Close price is at index [4]

        Example:
            [
                [1609459200000, "29000", "29500", "28900", "29300", "123.45", ...],
                [1609459260000, "29300", "29400", "29200", "29350", "98.76", ...],
                [1609459320000, "29350", "29600", "29300", "29500", "145.23", ...],
                [1609459380000, "29500", "29700", "29450", "29650", "167.89", ...]
            ]

        Raises:
            BinanceAPIError: If API request fails
        """
        url = f"{self.base_url}/fapi/v1/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}

        try:
            data = await self._request_with_retry("GET", url, params=params)

            if not data or len(data) < limit:
                logger.debug(
                    "%s: insufficient klines data (got %s, need %s)",
                    symbol,
                    len(data) if data else 0,
                    limit,
                )
                return []

            return cast(list[list[Any]], data)

        except Exception as e:
            logger.debug(f"Failed to fetch klines for {symbol}: {e}")
            return []
