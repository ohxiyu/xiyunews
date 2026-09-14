"""One-time migration of old Redis cooldowns; run after stopping CoinSignal."""

import argparse
import asyncio
import math
import os
import time

from dotenv import load_dotenv
from redis.asyncio import Redis

from src.platform.store import Store


async def migrate(path: str) -> None:
    load_dotenv()
    client = Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD") or None,
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
    )
    store = Store(path)
    try:
        rows = await client.hgetall("coinsignal:alert_cooldowns")
        now = time.time()
        values = [
            (key, float(value) + 7200)
            for key, value in rows.items()
            if math.isfinite(float(value)) and float(value) + 7200 > now
        ]

        def write() -> None:
            with store.db:
                store.db.executemany("INSERT OR REPLACE INTO cooldown VALUES (?,?)", values)

        await store.run(write)
        print(f"Imported {len(values)} active cooldowns; old Redis data retained")
    finally:
        await client.aclose()
        await store.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True)
    arguments = parser.parse_args()
    asyncio.run(migrate(arguments.database))
