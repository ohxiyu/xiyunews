import asyncio
import logging
import sys

from colorama import Fore, init
from dotenv import load_dotenv

load_dotenv()

from .alert_manager import AlertManager
from .alert_engine import AlertEngine
from .config import config
from .redis_manager import RedisManager

init(autoreset=True)

logging.basicConfig(
    level=config.logging.log_level_int,
    format=config.logging.format,
    handlers=[logging.StreamHandler(sys.stdout)]
)
sys.stdout.reconfigure(line_buffering=True)
logger = logging.getLogger("cexMonitor")


class CexMonitor:
    def __init__(self) -> None:
        self.alert_mgr = AlertManager()
        self.redis_mgr = RedisManager()
        self.alert_engine = AlertEngine(self.alert_mgr, self.redis_mgr)

    async def start(self) -> None:
        print(f"{Fore.MAGENTA}==========================================")
        print(f"{Fore.MAGENTA}   cexMonitor V3.0 - 3-Minute Alerts      ")
        print(f"{Fore.MAGENTA}==========================================")

        await self.alert_mgr.init_session()
        await self.redis_mgr.init()

        # Connect Redis to AlertManager, load cooldowns to prevent alert spam on restart
        self.alert_mgr.set_redis(self.redis_mgr)
        await self.alert_mgr.load_cooldowns_from_redis()

        try:
            # Start alert engine (runs indefinitely)
            await self.alert_engine.start()
        except KeyboardInterrupt:
            logger.info("Stopping...")
        except Exception as e:
            logger.critical(f"Critical System Failure: {e}", exc_info=True)
        finally:
            await self.close()
            logger.info("System Shutdown Complete.")

    async def close(self) -> None:
        await self.alert_engine.stop()
        await self.alert_mgr.close()
        await self.redis_mgr.close()


def main() -> None:
    monitor = CexMonitor()
    try:
        asyncio.run(monitor.start())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
