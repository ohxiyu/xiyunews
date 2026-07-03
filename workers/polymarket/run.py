"""Run the Polymarket breaking scheduler and API server."""
import asyncio
import os
import threading
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")
DB_PATH = os.getenv("REPORTS_DB_PATH", str(BASE_DIR / "db" / "reports.db"))

from src.services.api import PolymarketAPI
from src.services.telegram import TelegramService
from src.storage import SQLiteReportRepository
from src.scheduler import Scheduler


def run_api_server():
    import uvicorn
    from src.api.main import app

    port = int(os.getenv("API_PORT", "8081"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info", access_log=True)


async def main():
    polymarket = PolymarketAPI()
    tg = TelegramService()
    storage = SQLiteReportRepository(db_path=DB_PATH)

    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    print(f"🌐 API server started on port {os.getenv('API_PORT', '8081')}")

    scheduler = Scheduler(tg=tg, storage=storage, polymarket_api=polymarket)

    try:
        await scheduler.start()
    finally:
        print("🛑 Shutting down services...")
        await polymarket.close()
        await tg.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass