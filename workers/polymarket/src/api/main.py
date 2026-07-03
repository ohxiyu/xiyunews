"""FastAPI API for Polymarket breaking reports."""
import os
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .models import Report, ReportMeta, ErrorResponse
from src.services.api import PolymarketAPI
from src.services.report_service import ReportService
from src.storage import SQLiteReportRepository

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

app = FastAPI(
    title="QwePolymarket API",
    description="API for Polymarket breaking market reports",
    version="1.3.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.getenv("REPORTS_DB_PATH", str(BASE_DIR / "db" / "reports.db"))
storage = SQLiteReportRepository(db_path=DB_PATH)

_polymarket_api: PolymarketAPI | None = None
_report_service: ReportService | None = None


def get_report_service() -> ReportService:
    global _polymarket_api, _report_service

    if _report_service is None:
        _polymarket_api = PolymarketAPI()
        _report_service = ReportService(polymarket_api=_polymarket_api, storage=storage)
    return _report_service


def validate_platform(platform: str) -> None:
    if platform != "polymarket":
        raise HTTPException(status_code=400, detail="Invalid platform: only polymarket is supported")


@app.get("/")
async def root():
    return {
        "service": "QwePolymarket API",
        "version": "1.3.0",
        "endpoints": {
            "latest": "/v1/reports/latest?platform=polymarket",
            "history": "/v1/reports/history?platform=polymarket&days=7",
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    return {
        "ok": True,
        "ts": datetime.now(timezone.utc).isoformat(),
        "service": "QwePolymarket API",
    }


@app.get("/v1/reports/latest", response_model=Report)
async def get_latest_report(
    platform: str = Query(..., description="Only polymarket is supported"),
    refresh: bool = Query(False, description="Force refresh from Polymarket breaking feed"),
    limit: int = Query(8, ge=1, le=50, description="Maximum number of markets to fetch"),
):
    validate_platform(platform)

    try:
        report = None if refresh else await storage.get_latest_report(platform)

        if not report:
            payload = await get_report_service().build_latest_report(limit=limit)
            if payload:
                report = payload.to_dict()
                print(f"✅ [API] Breaking data fetched: {payload.items_count} items")

        if not report:
            return Report(
                platform=platform,
                updated_at=datetime.now(timezone.utc).isoformat(),
                title="Polymarket Breaking Markets",
                items=[],
                report_id=None,
                generated_by="polymarket-breaking",
                source="empty",
            )

        return report
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/v1/reports/history", response_model=list[ReportMeta], responses={400: {"model": ErrorResponse}})
async def get_report_history(
    platform: str = Query(..., description="Only polymarket is supported"),
    days: int = Query(7, ge=1, le=30, description="Number of days to look back"),
):
    validate_platform(platform)
    try:
        return await storage.get_history(platform, days=days)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.get("/v1/reports/{report_id}", response_model=Report, responses={404: {"model": ErrorResponse}})
async def get_report_by_id(report_id: str):
    try:
        report = await storage.get_report_by_id(report_id)
        if not report:
            raise HTTPException(status_code=404, detail=f"Report not found: {report_id}")
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
