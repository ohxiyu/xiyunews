import logging

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from config import config

logger = logging.getLogger("cexMonitor.redis")


class RedisManager:
    _instance = None
    _pool: ConnectionPool | None = None

    def __init__(self) -> None:
        self.redis: redis.Redis | None = None
        self._connection_url: str | None = None
        if RedisManager._instance is None:
            RedisManager._instance = self

    async def init(self) -> None:
        redis_cfg = config.redis

        if RedisManager._pool is None:
            if redis_cfg.password:
                self._connection_url = f"redis://:{redis_cfg.password}@{redis_cfg.host}:{redis_cfg.port}/{redis_cfg.db}"
            else:
                self._connection_url = f"redis://{redis_cfg.host}:{redis_cfg.port}/{redis_cfg.db}"

            RedisManager._pool = ConnectionPool.from_url(
                self._connection_url,
                decode_responses=redis_cfg.decode_responses,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                socket_connect_timeout=5,
                socket_timeout=5,
                health_check_interval=30,
            )
            logger.info(f"Redis Connection Pool Created: {redis_cfg.host}:{redis_cfg.port}")

        try:
            self.redis = redis.Redis(connection_pool=RedisManager._pool)
            await self.redis.ping()
            logger.info("Redis Connection Established")
        except Exception as e:
            logger.warning(f"Redis unavailable, running without persistence: {e}")
            self.redis = None
            RedisManager._pool = None

    async def close(self) -> None:
        if self.redis:
            await self.redis.close()
            logger.info("Redis Connection Closed")

        if RedisManager._pool and RedisManager._instance == self:
            await RedisManager._pool.disconnect()
            RedisManager._pool = None
            RedisManager._instance = None
            logger.info("Redis Connection Pool Closed")