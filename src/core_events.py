"""Independent event processing. Publishes only event-owned assets, never daily files."""
from __future__ import annotations
import asyncio
import json
import shutil
from pathlib import Path
from .models import Config
from .daily_feed import DailyFeedState
from .orchestrator import BMTNewsOrchestrator
from .storage.manager import StorageManager
from .run_report import RunReport, save_run_report
from .core_site import republish_events
from .event_brief_backfill import backfill_catalog
from .edition import load_staging_state, DEFAULT_STAGING_PATH

async def main():
    config=Config.model_validate_json(Path('data/config.github.json').read_text())
    if not config.core_only:raise ValueError('core profile required')
    runner=BMTNewsOrchestrator(config,StorageManager())
    from .publication_state import restore_published_documents
    restore_published_documents()
    backfill_catalog()
    daily=DailyFeedState.model_validate_json(Path('docs/_data/bmtnews_state.json').read_text())
    # Analysis is cached. Use the same bounded prefilter as collection formerly
    # used; enrichments from the saved edition take precedence over raw staging.
    from .event_pipeline import known_story_assignments, load_event_catalog
    from .ai.tokens import reset_usage
    report=RunReport.start(date=daily.date,timezone_name='Asia/Shanghai',kind='staging_fetch')
    reset_usage();runner.last_run_report=report
    try:
        _,catalog=load_event_catalog()
        known=known_story_assignments(catalog)
        staged=[item for item in load_staging_state(DEFAULT_STAGING_PATH).items if item.id not in known]
        analyzed=await runner._analyze_content(staged)
        qualified={i.id:i for i in analyzed if (i.ai_score or 0)>=config.filtering.ai_score_threshold}
        qualified.update({i.id:i for i in daily.items})
        await runner._update_event_timeline(list(qualified.values()),run_report=report)
        republish_events(Path('docs'))
    except Exception as exc:
        report.fail(exc)
        raise
    finally:
        runner._finish_run_report(report)
    # Build an event-only publication directory. It cannot overwrite a newer
    # daily selection, API/latest, journal, or delivery state in gh-pages.
    out=Path('event-output');out.mkdir()
    for relative in ['events','threads','api/events','api/events.json','_data/events.json','_data/event-legacy-urls.json','_data/threads.json','_data/core_stream.json']:
        source=Path('docs')/relative;target=out/relative
        if source.is_dir():shutil.copytree(source,target)
        elif source.is_file():target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)

if __name__=='__main__':asyncio.run(main())
