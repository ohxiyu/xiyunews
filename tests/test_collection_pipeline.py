"""The extracted raw collection stage must be useful without publication or AI."""
import asyncio
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from test_core_site import story
from src.models import Config
from src.orchestrator import BMTNewsOrchestrator
from src.collection import FetchReport,SourceFetchOutcome
from src.edition import load_staging_state
from src.storage.manager import StorageManager
from src.run_report import load_run_report


def test_collection_saves_raw_candidates_and_reports_without_ai_or_site_writes(tmp_path,monkeypatch):
    config=Config.model_validate_json(Path('data/config.github.json').read_text())
    monkeypatch.chdir(tmp_path)
    app=BMTNewsOrchestrator(config,StorageManager(data_dir=str(tmp_path/'data')))
    item=story();now=datetime(2026,11,8,2,tzinfo=timezone.utc)
    async def fetch(since):
        app.last_fetch_report=FetchReport([SourceFetchOutcome('RSS','success',items=[item])])
        return [item]
    app.fetch_all_sources=fetch
    app._analyze_content=AsyncMock(side_effect=AssertionError('raw collection must not score'))
    app._enrich_important_items=AsyncMock(side_effect=AssertionError('raw collection must not expand'))
    app._publish_outputs=AsyncMock(side_effect=AssertionError('raw collection must not publish'))
    asyncio.run(app.fetch_to_staging(now=now))
    assert [i.id for i in load_staging_state().items]==[item.id]
    report=load_run_report(Path('data/run-report.json'))
    assert report['kind']=='staging_fetch' and report['metrics']['staged_added']==1
    assert not Path('docs').exists()
    app._analyze_content.assert_not_awaited();app._publish_outputs.assert_not_awaited()


def test_collection_failure_preserves_existing_staging_and_has_failure_report(tmp_path,monkeypatch):
    config=Config.model_validate_json(Path('data/config.github.json').read_text())
    monkeypatch.chdir(tmp_path)
    app=BMTNewsOrchestrator(config,StorageManager(data_dir=str(tmp_path/'data')))
    path=Path('data/staging-items.json');path.write_text('unchanged prior snapshot')
    async def fetch(since):
        app.last_fetch_report=FetchReport([SourceFetchOutcome('RSS','failure',error='HTTP 403')])
        return []
    app.fetch_all_sources=fetch
    with pytest.raises(RuntimeError,match='All 1 attempted sources failed'):
        asyncio.run(app.fetch_to_staging())
    assert path.read_text()=='unchanged prior snapshot'
    assert load_run_report(Path('data/run-report.json'))['status']=='failure'
