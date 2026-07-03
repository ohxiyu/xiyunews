"""
FastAPI Web API for QwePolymarket

Provides HTTP endpoints to access report data and platform information.
SSOT: When storage is empty, fetches real-time Polymarket breaking data.
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import os
from pathlib import Path
from datetime import datetime, timezone

# Load environment variables from .env file
from dotenv import load_dotenv
BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(dotenv_path=BASE_DIR / ".env")

# Import models and storage
from .models import Report, ReportMeta, ErrorResponse, PlatformResponse
from src.storage import SQLiteReportRepository

# Import platform registry
from src.platforms import list_platforms, get_registry

# SSOT imports - for real-time data fetching
from src.services.api import PolyrouterAPI
from src.services.report_service import ReportService

# Initialize FastAPI app
app = FastAPI(
    title="QwePolymarket API",
    description="API for accessing prediction market breaking reports",
    version="1.2.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议配置具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize storage
DB_PATH = os.getenv("REPORTS_DB_PATH", str(BASE_DIR / "db" / "reports.db"))
storage = SQLiteReportRepository(db_path=DB_PATH)

_polyrouter_api = None
_report_service = None


def get_report_service() -> Optional[ReportService]:
    """Get or create ReportService singleton for real-time data fetching."""
    global _polyrouter_api, _report_service

    if _report_service is not None:
        return _report_service

    # Optional for breaking mode; legacy Polyrouter methods still use it.
    api_key = os.getenv("POLYROUTER_API_KEY", "")
    _polyrouter_api = PolyrouterAPI(api_key)

    _report_service = ReportService(
        polyrouter_api=_polyrouter_api,
        storage=storage,
    )
    return _report_service


def get_valid_platforms() -> List[str]:
    """Get list of valid platform IDs from registry."""
    return [p.id for p in list_platforms(include_disabled=False)]


def validate_platform(platform: str) -> None:
    """Validate platform ID and raise HTTPException if invalid."""
    valid = get_valid_platforms()
    if platform not in valid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid platform: {platform}. Valid platforms: {', '.join(valid)}"
        )


@app.get("/")
async def root():
    """Root endpoint"""
    platforms = get_valid_platforms()
    return {
        "service": "QwePolymarket API",
        "version": "1.2.0",
        "endpoints": {
            "platforms": "/v1/platforms",
            "latest": f"/v1/reports/latest?platform={{{','.join(platforms)}}}",
            "history": f"/v1/reports/history?platform={{{','.join(platforms)}}}&days=7"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


@app.get("/healthz")
async def healthz():
    """Health check endpoint with timestamp"""
    from datetime import datetime, timezone
    return {
        "ok": True,
        "ts": datetime.now(timezone.utc).isoformat(),
        "service": "QwePolymarket API"
    }


@app.get("/v1/platforms", response_model=List[PlatformResponse])
async def get_platforms(include_disabled: bool = Query(False, description="Include disabled platforms")):
    """
    Get list of available platforms.

    Args:
        include_disabled: If true, include disabled platforms

    Returns:
        List of platform info objects
    """
    platforms = list_platforms(include_disabled=include_disabled)
    return [
        PlatformResponse(
            id=p.id,
            name=p.name,
            enabled=p.enabled,
            description=p.description or "",
        )
        for p in platforms
    ]


@app.get("/v1/reports/latest", response_model=Report)
async def get_latest_report(
    platform: str = Query(..., description="Platform name"),
    refresh: bool = Query(False, description="Force refresh from Polymarket breaking feed"),
    limit: int = Query(8, ge=1, le=50, description="Maximum number of markets to fetch")
):
    """
    Get the latest report for a platform.

    SSOT: When storage is empty or refresh=true, fetches real-time breaking data.

    Args:
        platform: Platform ID (e.g., polymarket)
        refresh: Force refresh from Polymarket breaking feed
        limit: Maximum number of markets to fetch (1-50, default 8)

    Returns:
        Latest report data (returns empty items array if no data available)
    """
    validate_platform(platform)

    try:
        report = None

        # Try storage first (unless refresh is requested)
        if not refresh:
            report = await storage.get_latest_report(platform)

        # SSOT: If no data in storage, fetch real-time breaking data
        if not report or refresh:
            report_service = get_report_service()
            if report_service:
                print(f"📡 [API] Fetching breaking data for {platform} (limit={limit})...")
                payload = await report_service.build_latest_report(
                    platform_id=platform,
                    limit=limit,
                )
                if payload:
                    # Convert ReportPayload to dict for response
                    report = payload.to_dict()
                    print(f"✅ [API] Breaking data fetched: {payload.items_count} items")

        # Still no data? Return empty response
        if not report:
            return Report(
                platform=platform,
                updated_at=datetime.now(timezone.utc).isoformat(),
                title=f"{platform.title()} Breaking Markets",
                items=[],
                report_id=None,
                generated_by="polymarket-breaking",
                source="empty"
            )

        return report

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/v1/reports/history", response_model=List[ReportMeta], responses={400: {"model": ErrorResponse}})
async def get_report_history(
    platform: str = Query(..., description="Platform name"),
    days: int = Query(7, ge=1, le=30, description="Number of days to look back")
):
    """
    Get report history for a platform.

    Args:
        platform: Platform ID (e.g., polymarket)
        days: Number of days to look back (1-30)

    Returns:
        List of report metadata

    Raises:
        HTTPException: If validation fails
    """
    validate_platform(platform)

    try:
        history = await storage.get_history(platform, days=days)
        return history

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/v1/reports/{report_id}", response_model=Report, responses={404: {"model": ErrorResponse}})
async def get_report_by_id(report_id: str):
    """
    Get a specific report by ID.

    Args:
        report_id: Report ID

    Returns:
        Report data

    Raises:
        HTTPException: If report not found
    """
    try:
        report = await storage.get_report_by_id(report_id)

        if not report:
            raise HTTPException(
                status_code=404,
                detail=f"Report not found: {report_id}"
            )

        return report

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# For standalone running
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
