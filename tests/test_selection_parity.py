"""PR3 extraction must preserve selection on the same scored inputs.

The expected IDs/statistics were captured from PR2 head 5bd52f6 before extraction.
Model comparison responses are fixed; this checks orchestration, not model drift.
"""
import asyncio
import json
from io import StringIO
from pathlib import Path
import pytest
from rich.console import Console
from src.models import Config,ContentItem
from src.orchestrator import BMTNewsOrchestrator
from src.storage.manager import StorageManager

FIXTURE=json.loads((Path(__file__).parent/'fixtures/daily-selection-parity.json').read_text())


@pytest.mark.parametrize('case',FIXTURE['scenarios'],ids=lambda c:c['name'])
def test_fixed_input_selection_matches_before_extraction(case,tmp_path,monkeypatch):
    config=Config.model_validate_json(Path('data/config.github.json').read_text())
    config.filtering=type(config.filtering).model_validate(FIXTURE['filtering'])
    config.ai.result_cache_enabled=False
    runner=BMTNewsOrchestrator(config,StorageManager(data_dir=str(tmp_path)))
    runner.console=Console(file=StringIO())
    async def comparisons(client,items,clusters,**kwargs):
        groups={}
        for i,item in enumerate(items):
            key=item.metadata.get('fixture_event')
            if key:groups.setdefault(key,[]).append(i)
        return [ids for ids in groups.values() if len(ids)>1]
    monkeypatch.setattr('src.ai.topic_dedup.duplicate_groups',comparisons)
    monkeypatch.setattr('src.selection.create_ai_client',lambda _:object())
    async def select():
        rows=[ContentItem.model_validate(i) for i in case['items']]
        history=[ContentItem.model_validate(i) for i in case['history']]
        merged=runner.merge_cross_source_duplicates(rows)
        filtered=await runner.filter_items(merged,apply_balance=False,dedup_context=history,log=False)
        qualified=runner._distinct_daily_events(await runner.merge_topic_duplicates(filtered.items,daily_events=True))
        _,selected=await runner._audit_daily_ranking(qualified,runner.apply_balanced_digest(qualified,log=False,**case['balance_kwargs']))
        return {'url_ids':[i.id for i in merged],'threshold_count':filtered.threshold_count,
            'topic_dedup_removed':filtered.topic_dedup_removed,'selected_ids':[i.id for i in selected.items],
            'groups':selected.group_counts,'borrowed':selected.borrowed_count,
            'category_deferred':selected.category_limit_deferred,'source_deferred':selected.source_limit_deferred}
    assert asyncio.run(select())==case['expected']
