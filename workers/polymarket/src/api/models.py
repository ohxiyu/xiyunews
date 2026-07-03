"""
Pydantic models for API responses
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class MarketItem(BaseModel):
    """Single market item"""
    rank: int = Field(..., description="Market rank")
    market_id: str = Field(..., description="Market ID")
    title: str = Field(..., description="Market title")
    yes: Optional[float] = Field(None, ge=0, le=1, description="Yes probability (None if not binary)")
    no: Optional[float] = Field(None, ge=0, le=1, description="No probability (None if not binary)")
    volume_24h: Optional[float] = Field(None, description="24h trading volume")
    liquidity: Optional[float] = Field(None, description="Market liquidity")
    price_change_24h: Optional[float] = Field(None, description="24h price change")
    url: str = Field(..., description="Market URL")
    platform: Optional[str] = Field(None, description="Platform ID")
    category: Optional[str] = Field(None, description="Market category")
    slug: Optional[str] = Field(None, description="Market slug/identifier")
    updated_at: Optional[str] = Field(None, description="Last update timestamp")


class Report(BaseModel):
    """
    Complete report with SSOT fingerprint.

    The report_id allows verification that Web and Telegram
    are using the same data source.
    """
    platform: str = Field(..., description="Platform name")
    updated_at: str = Field(..., description="ISO8601 UTC timestamp")
    title: str = Field(..., description="Report title")
    items: List[MarketItem] = Field(..., description="List of market items")
    items_count: Optional[int] = Field(None, description="Number of items")
    generation_time_ms: Optional[int] = Field(None, description="Report generation time in ms")
    # SSOT fields
    report_id: Optional[str] = Field(None, description="SSOT fingerprint for consistency verification")
    generated_by: Optional[str] = Field(None, description="Data source")
    source_version: Optional[str] = Field(None, description="API version")
    source: Optional[str] = Field(None, description="Data source: 'realtime', 'storage', 'empty'")


class ReportMeta(BaseModel):
    """Report metadata for history"""
    storage_key: str = Field(..., description="Storage key/ID")
    platform: str = Field(..., description="Platform name")
    updated_at: str = Field(..., description="ISO8601 UTC timestamp")
    items_count: int = Field(..., description="Number of items")


class PlatformResponse(BaseModel):
    """Platform information"""
    id: str = Field(..., description="Platform identifier")
    name: str = Field(..., description="Display name")
    enabled: bool = Field(..., description="Whether platform is enabled")
    description: str = Field("", description="Platform description")


class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Error details")
