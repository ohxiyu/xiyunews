"""Background collection never scores, expands, or publishes."""
import asyncio
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from src.rolling_feed import active_items,collect
from src.models import Config
from src.orchestrator import BMTNewsOrchestrator
from src.storage.manager import StorageManager
from test_core_site import story


def test_background_window_uses_source_time_not_collection_time():
    now=datetime(2026,11,8,12,tzinfo=timezone.utc);items=[]
    for i,hours in enumerate((-24,-24.001,-1,0,1)):
        item=story(i);item.published_at=now+timedelta(hours=hours);items.append(item)
    assert [i.id for i in active_items(items,now)]==['2','0']


def test_morning_collection_keeps_scoring_for_the_final_daily_run(tmp_path,monkeypatch):
    config=Config.model_validate_json(Path('data/config.github.json').read_text())
    monkeypatch.chdir(tmp_path)
    runner=BMTNewsOrchestrator(config,StorageManager(data_dir=str(tmp_path/'data')))
    item=story();now=datetime(2026,11,7,22,30,tzinfo=timezone.utc)
    runner._stage_sources=AsyncMock(return_value=[item])
    runner._analyze_content=AsyncMock(return_value=[item])
    runner._enrich_important_items=AsyncMock(side_effect=AssertionError('background must never expand'))
    runner._publish_outputs=AsyncMock(side_effect=AssertionError('background must never publish'))
    report=asyncio.run(collect(runner,now=now))
    assert report.metrics['ai_total_tokens']==0
    assert not Path('data/qualified-cache.json').exists() and Path('data/run-report.json').exists()
    assert not Path('docs').exists()
    runner._analyze_content.assert_not_awaited()
    runner._enrich_important_items.assert_not_awaited();runner._publish_outputs.assert_not_awaited()


def test_collection_failure_keeps_previous_qualified_cache_without_publication(tmp_path,monkeypatch):
    config=Config.model_validate_json(Path('data/config.github.json').read_text())
    monkeypatch.chdir(tmp_path)
    runner=BMTNewsOrchestrator(config,StorageManager(data_dir=str(tmp_path/'data')))
    checkpoint=Path('data/qualified-cache.json');checkpoint.write_text('last qualified cohort')
    runner._stage_sources=AsyncMock(side_effect=RuntimeError('sources unavailable'))
    with pytest.raises(RuntimeError):asyncio.run(collect(runner))
    assert checkpoint.read_text()=='last qualified cohort' and not Path('docs').exists()

def test_ordinary_collection_makes_no_model_calls(tmp_path, monkeypatch):
    config = Config.model_validate_json(Path('data/config.github.json').read_text())
    monkeypatch.chdir(tmp_path)
    runner = BMTNewsOrchestrator(config, StorageManager(data_dir=str(tmp_path / 'data')))
    runner._stage_sources = AsyncMock(return_value=[story()])
    runner._analyze_content = AsyncMock(side_effect=AssertionError('ordinary collection cannot call AI'))
    report = asyncio.run(collect(runner))
    assert report.metrics['ai_total_tokens'] == 0
    assert not Path('data/qualified-cache.json').exists()
    runner._analyze_content.assert_not_awaited()
