"""CoinSignal process entry point."""

import asyncio
import logging
import sys

from colorama import Fore, init

from .alert_engine import AlertEngine
from .alert_manager import AlertManager
from .config import config
from .redis_manager import RedisManager

APP_NAME = "CoinSignal"
APP_VERSION = "1.0.0"

init(autoreset=True)
logging.basicConfig(
    level=config.logging.log_level_int,
    format=config.logging.format,
    handlers=[logging.StreamHandler(sys.stdout)],
)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)
logger = logging.getLogger("coinsignal")


class CoinSignal:
    def __init__(self) -> None:
        self.alert_manager = AlertManager()
        self.redis_manager = RedisManager()
        self.alert_engine = AlertEngine(self.alert_manager, self.redis_manager)

    async def start(self) -> None:
        print(f"{Fore.MAGENTA}==========================================")
        print(f"{Fore.MAGENTA}   {APP_NAME} {APP_VERSION} - 3-Minute Alerts")
        print(f"{Fore.MAGENTA}==========================================")

        if config.telegram.enabled:
            await self.alert_manager.init_session()
        else:
            logger.warning("Telegram is disabled; running in explicit log-only mode")

        await self.redis_manager.init()
        self.alert_manager.set_redis(self.redis_manager)
        await self.alert_manager.load_cooldowns_from_redis()

        try:
            await self.alert_engine.start()
        except KeyboardInterrupt:
            logger.info("Stopping")
        except Exception:
            logger.exception("Critical system failure")
            raise
        finally:
            await self.close()
            logger.info("Shutdown complete")

    async def close(self) -> None:
        await self.alert_engine.stop()
        await self.alert_manager.close()
        await self.redis_manager.close()


def main() -> None:
    service = CoinSignal()
    try:
        asyncio.run(service.start())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
