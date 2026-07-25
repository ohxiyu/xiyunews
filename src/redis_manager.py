"""Optional Redis-backed cooldown persistence."""

import logging

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from .config import config

logger = logging.getLogger("coinsignal.redis")


class RedisManager:
    def __init__(self) -> None:
        self.redis: redis.Redis | None = None
        self._pool: ConnectionPool | None = None

    async def init(self) -> None:
        redis_config = config.redis
        if redis_config.password:
            connection_url = (
                f"redis://:{redis_config.password}@"
                f"{redis_config.host}:{redis_config.port}/{redis_config.db}"
            )
        else:
            connection_url = f"redis://{redis_config.host}:{redis_config.port}/{redis_config.db}"

        self._pool = ConnectionPool.from_url(
            connection_url,
            decode_responses=redis_config.decode_responses,
            max_connections=20,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_connect_timeout=5,
            socket_timeout=5,
            health_check_interval=30,
        )

        try:
            self.redis = redis.Redis(connection_pool=self._pool)
            await self.redis.ping()
            logger.info(
                "Redis connection established: %s:%s",
                redis_config.host,
                redis_config.port,
            )
        except Exception as exc:
            logger.warning("Redis unavailable; continuing without persistence: %s", exc)
            if self.redis is not None:
                await self.redis.aclose()
            await self._pool.disconnect()
            self.redis = None
            self._pool = None

    async def close(self) -> None:
        if self.redis is not None:
            await self.redis.aclose()
            self.redis = None
        if self._pool is not None:
            await self._pool.disconnect()
            self._pool = None
        logger.info("Redis resources closed")
