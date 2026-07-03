"""Pydantic models for Polymarket API responses."""
from pydantic import BaseModel, Field


class MarketItem(BaseModel):
    rank: int = Field(..., description="Market rank")
    market_id: str = Field(..., description="Market ID")
    title: str = Field(..., description="Market title")
    yes: float | None = Field(None, ge=0, le=1, description="Yes probability")
    no: float | None = Field(None, ge=0, le=1, description="No probability")
    volume_24h: float | None = Field(None, description="24h trading volume")
    liquidity: float | None = Field(None, description="Market liquidity")
    price_change_24h: float | None = Field(None, description="24h price change")
    url: str = Field(..., description="Market URL")


class Report(BaseModel):
    platform: str = Field(..., description="Platform name")
    updated_at: str = Field(..., description="ISO8601 UTC timestamp")
    title: str = Field(..., description="Report title")
    items: list[MarketItem] = Field(..., description="List of market items")
    items_count: int | None = Field(None, description="Number of items")
    generation_time_ms: int | None = Field(None, description="Report generation time in ms")
    report_id: str | None = Field(None, description="Report fingerprint")
    generated_by: str | None = Field(None, description="Data source")
    source_version: str | None = Field(None, description="Source version")
    source: str | None = Field(None, description="Data source: realtime, storage, or empty")


class ReportMeta(BaseModel):
    storage_key: str = Field(..., description="Storage key/ID")
    platform: str = Field(..., description="Platform name")
    updated_at: str = Field(..., description="ISO8601 UTC timestamp")
    items_count: int = Field(..., description="Number of items")


class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    detail: str | None = Field(None, description="Error details")
