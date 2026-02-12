"""
FastAPI Web API for QweTruthMachine

Provides HTTP endpoints to access report data and platform information.
SSOT: When storage is empty, fetches real-time data from Polyrouter.
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
from src.services.api import PolyrouterAPI, OpinionAPI
from src.services.ai import AIService
from src.services.report_service import ReportService

# Initialize FastAPI app
app = FastAPI(
    title="QweTruthMachine API",
    description="API for accessing prediction market reports",
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

# SSOT: Initialize Polyrouter API for real-time data fetching
_polyrouter_api = None
_opinion_api = None
_ai_service = None
_report_service = None


def get_report_service() -> Optional[ReportService]:
    """Get or create ReportService singleton for real-time data fetching."""
    global _polyrouter_api, _opinion_api, _ai_service, _report_service

    if _report_service is not None:
        return _report_service

    api_key = os.getenv("POLYROUTER_API_KEY")
    if not api_key:
        print("⚠️ POLYROUTER_API_KEY not set, real-time fetching disabled")
        return None

    _polyrouter_api = PolyrouterAPI(api_key)
    _ai_service = AIService()

    # Initialize Opinion API if key is available
    opinion_key = os.getenv("OPINION_API_KEY")
    if opinion_key:
        _opinion_api = OpinionAPI(opinion_key)
        print("✅ Opinion API initialized")
    else:
        print("⚠️ OPINION_API_KEY not set, Opinion will use Polyrouter polyfill")

    _report_service = ReportService(
        polyrouter_api=_polyrouter_api,
        ai_service=_ai_service,
        storage=storage,
        opinion_api=_opinion_api
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
        "service": "QweTruthMachine API",
        "version": "1.1.0",
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
        "service": "QweTruthMachine API"
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
    lang: str = Query("zh", description="Language for AI summary (zh or en)"),
    refresh: bool = Query(False, description="Force refresh from Polyrouter"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of markets to fetch")
):
    """
    Get the latest report for a platform.

    SSOT: When storage is empty or refresh=true, fetches real-time data from Polyrouter.

    Args:
        platform: Platform ID (e.g., polymarket, kalshi, opinion)
        lang: Language for AI summaries (zh or en)
        refresh: Force refresh from Polyrouter API
        limit: Maximum number of markets to fetch (1-50, default 20)

    Returns:
        Latest report data (returns empty items array if no data available)
    """
    validate_platform(platform)

    try:
        report = None

        # Try storage first (unless refresh is requested)
        if not refresh:
            report = await storage.get_latest_report(platform)

        # SSOT: If no data in storage, fetch real-time from Polyrouter
        if not report or refresh:
            report_service = get_report_service()
            if report_service:
                print(f"📡 [API] Fetching real-time data for {platform} (lang={lang}, limit={limit})...")
                payload = await report_service.build_latest_report(
                    platform_id=platform,
                    limit=limit,
                    lang=lang,
                    with_ai=True  # Generate AI summaries
                )
                if payload:
                    # Convert ReportPayload to dict for response
                    report = payload.to_dict()
                    print(f"✅ [API] Real-time data fetched: {payload.items_count} items")

        # Still no data? Return empty response
        if not report:
            return Report(
                platform=platform,
                updated_at=datetime.now(timezone.utc).isoformat(),
                title=f"{platform.title()} Markets",
                items=[],
                report_id=None,
                generated_by="polyrouter",
                lang=lang,
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
        platform: Platform ID (e.g., polymarket, kalshi, metaculus)
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
