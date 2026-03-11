"""
QwePolymarket - Unified Entry Point

Runs both:
1. Telegram Bot + Scheduler (async tasks)
2. FastAPI Web API (uvicorn server)

All market data flows through Polyrouter API as the ONLY data source.
"""
import asyncio
import os
import sys
import threading
from pathlib import Path
from dotenv import load_dotenv

# Path Setup
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# SSOT Import - Polyrouter as the ONLY data source
from src.services.api import PolyrouterAPI
from src.services.telegram import TelegramService
from src.storage import SQLiteReportRepository
from src.scheduler import Scheduler


def run_api_server():
    """Run FastAPI server in a separate thread."""
    import uvicorn
    from src.api.main import app

    port = int(os.getenv("API_PORT", "8081"))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True,
    )


async def main():
    # SSOT: Polyrouter is the primary data source
    poly_router_key = os.getenv("POLYROUTER_API_KEY")
    if not poly_router_key:
        print("❌ POLYROUTER_API_KEY not set - cannot start")
        sys.exit(1)

    # Initialize services
    polyrouter = PolyrouterAPI(poly_router_key)
    tg = TelegramService()
    storage = SQLiteReportRepository(db_path="db/reports.db")

    # Start API server in a separate thread
    api_thread = threading.Thread(target=run_api_server, daemon=True)
    api_thread.start()
    print(f"🌐 API server started on port {os.getenv('API_PORT', '8081')}")

    # Initialize Scheduler (SSOT via Polyrouter)
    scheduler = Scheduler(
        tg=tg,
        storage=storage,
        poly_router_api=polyrouter,
    )

    try:
        await scheduler.start()
    finally:
        print("🛑 Shutting down services...")
        await polyrouter.close()
        await tg.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
