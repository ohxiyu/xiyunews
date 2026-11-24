"""Rolling source collection and deterministic deduplication."""
from __future__ import annotations
import asyncio
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .edition import DEFAULT_STAGING_PATH,merge_staged_items
from .models import Config
from .orchestrator import BMTNewsOrchestrator
from .storage.manager import StorageManager
from .run_report import RunReport
from .ai.tokens import reset_usage


def active_items(items,now):
    start=now-timedelta(hours=24)
    return merge_staged_items([], [i for i in items if start<=i.published_at<now],now=now)


async def collect(runner,*,now=None,staging_path=DEFAULT_STAGING_PATH,hours=24):
    now=now or datetime.now(timezone.utc)
    if now.tzinfo is None:raise ValueError('background collection requires aware time')
    timezone_name=runner.config.filtering.daily_timezone
    report=RunReport.start(date=now.astimezone(ZoneInfo(timezone_name)).date().isoformat(),
        timezone_name=timezone_name,kind='staging_fetch',started_at=now)
    reset_usage();runner.last_run_report=report
    try:
        staged=await runner._stage_sources(report,now,force_hours=hours,staging_path=staging_path)
        candidates=active_items(staged,now)
        report.set_metric('edition_candidates',len(candidates))
        report.set_breakdown('candidate_sources',runner._source_breakdown(candidates))
        return report
    except Exception as exc:
        report.fail(exc)
        raise
    finally:
        runner._finish_run_report(report)


async def main():
    config=Config.model_validate_json(Path('data/config.github.json').read_text())
    await collect(BMTNewsOrchestrator(config,StorageManager()))


if __name__=='__main__':asyncio.run(main())
