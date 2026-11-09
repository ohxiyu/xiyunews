"""Background scoring and qualified fallback cache; no publication or delivery."""
from __future__ import annotations
import asyncio
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
from .edition import DEFAULT_STAGING_PATH,merge_staged_items
from .edition_fallback import save_selection,open_window
from .models import Config
from .orchestrator import BMTNewsOrchestrator
from .storage.manager import StorageManager
from .run_report import RunReport
from .ai.tokens import reset_usage


def active_items(items,now):
    start=now-timedelta(hours=24)
    return merge_staged_items([], [i for i in items if start<=i.published_at<now],now=now)


async def collect_and_score(runner,*,now=None,staging_path=DEFAULT_STAGING_PATH,hours=24):
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
        analyzed=await runner._analyze_content(candidates,edition_window=open_window(now,timezone_name))
        report.set_metric('analyzed_this_run',len(analyzed))
        report.set_breakdown('scored_sources',runner._source_breakdown([i for i in analyzed if i.ai_score is not None]))
        filtered=await runner.filter_items(analyzed,apply_balance=False)
        qualified=runner._distinct_daily_events(await runner.merge_topic_duplicates(filtered.items,daily_events=True))
        _,selection=await runner._audit_daily_ranking(qualified,runner.apply_balanced_digest(qualified,log=False))
        save_selection(selection.items,runner.config,open_window(now,timezone_name),now=now)
        report.set_metric('above_threshold',filtered.threshold_count)
        report.set_metric('qualified_cached',len(selection.items))
        report.set_breakdown('qualified_sources',runner._source_breakdown(selection.items))
        return report
    except Exception as exc:
        report.fail(exc)
        raise
    finally:
        runner._finish_run_report(report)


async def main():
    config=Config.model_validate_json(Path('data/config.github.json').read_text())
    await collect_and_score(BMTNewsOrchestrator(config,StorageManager()))


if __name__=='__main__':asyncio.run(main())
