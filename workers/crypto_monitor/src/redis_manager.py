import logging
import time
from typing import Any

import orjson
import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from config import config

logger = logging.getLogger("cexMonitor.redis")


class RedisConnectionError(Exception):
    pass


class RedisManager:
    _instance = None
    _pool: ConnectionPool | None = None
    
    def __init__(self) -> None:
        self.redis: redis.Redis | None = None
        self._connection_url: str | None = None
        
        # Singleton pattern for connection pool reuse
        if RedisManager._instance is None:
            RedisManager._instance = self

    async def init(self) -> None:
        redis_cfg = config.redis

        # Reuse existing connection pool
        if RedisManager._pool is None:
            if redis_cfg.password:
                self._connection_url = f"redis://:{redis_cfg.password}@{redis_cfg.host}:{redis_cfg.port}/{redis_cfg.db}"
            else:
                self._connection_url = f"redis://{redis_cfg.host}:{redis_cfg.port}/{redis_cfg.db}"

            # Create connection pool with optimized settings
            RedisManager._pool = ConnectionPool.from_url(
                self._connection_url,
                decode_responses=redis_cfg.decode_responses,
                max_connections=20,  # Optimized pool size
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30
            )
            logger.info(f"Redis Connection Pool Created: {redis_cfg.host}:{redis_cfg.port}")

        try:
            self.redis = redis.Redis(connection_pool=RedisManager._pool)
            await self.redis.ping()
            logger.info("Redis Connection Established (reusing pool)")
        except Exception as e:
            logger.warning(f"Redis unavailable, running without persistence: {e}")
            self.redis = None
            RedisManager._pool = None  # Reset pool for potential retry

    async def close(self) -> None:
        if self.redis:
            await self.redis.close()
            logger.info("Redis Connection Closed")
        
        # Only close pool when shutting down completely
        if RedisManager._pool and RedisManager._instance == self:
            await RedisManager._pool.disconnect()
            RedisManager._pool = None
            RedisManager._instance = None
            logger.info("Redis Connection Pool Closed")

    async def update_market_data(self, symbol: str, data: dict[str, Any]) -> None:
        if not self.redis:
            return

        try:
            data["last_update"] = time.time()
            await self.redis.hset("market_data", symbol, orjson.dumps(data).decode("utf-8"))
        except Exception as e:
            logger.error(f"Redis Write Error for {symbol}: {e}")

    async def set_market_data_batch(self, data: list) -> None:
        if not self.redis:
            return

        try:
            # Use pipeline for atomic operations
            async with self.redis.pipeline() as pipe:
                await pipe.set("crypto_market_data", orjson.dumps(data).decode("utf-8"))
                await pipe.set("crypto_market_data_ts", time.time())
                await pipe.set("crypto_market_data_count", len(data))
                await pipe.execute()
        except Exception as e:
            logger.error(f"Redis Batch Write Error: {e}")

    async def get_market_data(self, symbol: str) -> dict[str, Any] | None:
        if not self.redis:
            return None

        try:
            data = await self.redis.hget("market_data", symbol)
            if data:
                return orjson.loads(data)
        except Exception as e:
            logger.error(f"Redis Read Error for {symbol}: {e}")

        return None

    async def get_all_market_data(self) -> list | None:
        if not self.redis:
            return None

        try:
            data = await self.redis.get("crypto_market_data")
            if data:
                return orjson.loads(data)
        except Exception as e:
            logger.error(f"Redis Batch Read Error: {e}")

        return None

    async def ping(self) -> bool:
        if not self.redis:
            return False

        try:
            await self.redis.ping()
            return True
        except Exception:
            return False

    async def health_check(self) -> dict[str, Any]:
        result = {
            "connected": False,
            "latency_ms": 0,
            "error": None
        }

        if not self.redis:
            result["error"] = "Not initialized"
            return result

        try:
            start = time.time()
            await self.redis.ping()
            result["latency_ms"] = (time.time() - start) * 1000
            result["connected"] = True
        except Exception as e:
            result["error"] = str(e)

        return result
