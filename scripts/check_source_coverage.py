"""Read-only source coverage check: no AI, publication, secrets or state writes."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import httpx

from src.models import RSSSourceConfig
from src.scrapers.rss import RSSScraper


async def check(config: Path, hours: int) -> dict:
    raw = json.loads(config.read_text())
    sources = [RSSSourceConfig.model_validate(row) for row in raw["sources"]["rss"] if row.get("fallback_google_news") and row.get("enabled", True)]
    async with httpx.AsyncClient(timeout=20) as client:
        scraper = RSSScraper(sources, client)
        items = await scraper.fetch(datetime.now(timezone.utc) - timedelta(hours=hours))
    return {"hours": hours, "feeds": scraper.feed_results, "items": len(items),
            "headline_only": sum(bool(row.metadata.get("headline_only")) for row in items),
            "publishers": sorted({str(row.metadata.get("feed_name")) for row in items})}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("data/config.github.json"))
    parser.add_argument("--hours", type=int, default=72)
    args = parser.parse_args()
    if not 1 <= args.hours <= 168:
        parser.error("hours must be 1..168")
    report = asyncio.run(check(args.config, args.hours))
    print(json.dumps(report, ensure_ascii=False))
    return int(any(row.get("status") == "failure" and row.get("fallback_status") != "empty" for row in report["feeds"]))


if __name__ == "__main__":
    raise SystemExit(main())
