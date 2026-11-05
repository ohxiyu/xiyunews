"""Saved public assignments recover links without any model or delivery API."""
import asyncio
import copy
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.daily_feed import DailyFeedState, save_daily_feed_state
from src.event_pipeline import _new_event, _stable_event_id, _stable_update_id, known_story_assignments, save_event_catalog, story_evidence
from src.event_recovery import recover_published_links
from src.events import EventStatus, EventUpdateType
from src.models import AIConfig, Config, ContentItem, FilteringConfig, SourcesConfig, SourceType
from src.orchestrator import BMTNewsOrchestrator
from src.publication_state import StateConflict
from src.storage.manager import StorageManager


NOW = datetime(2026, 11, 5, 6, 0, tzinfo=timezone.utc)


def article(name):
    item = ContentItem(id='rss:' + name, title='Source ' + name,
        url='https://example.com/' + name, source_type=SourceType.RSS,
        published_at=NOW - timedelta(hours=8), fetched_at=NOW - timedelta(hours=7),
        ai_score=8.0, metadata={'category': 'crypto-security',
            'title_zh': '已保存标题 ' + name, 'title_en': 'Saved ' + name,
            'detailed_summary_zh': '已发表的完整事实，不重写。',
            'detailed_summary_en': 'Full saved facts, unchanged.',
            'background_zh': '已保存背景。',
            'sources': [{'title': 'Original reference', 'url': 'https://reference.example.com/a'}]})
    event_id = _stable_event_id(item.id)
    item.metadata.update(event_id=event_id, event_update_id=_stable_update_id(event_id, item.id))
    return item


def test_recovery_preserves_public_facts_ids_references_and_is_idempotent():
    initial = article('initial')
    parent = _new_event(initial, story_evidence(initial)).model_copy(update={'status': EventStatus.CLOSED})
    material, folded, new = (article(n) for n in ('material', 'folded', 'new'))
    material.metadata.update(event_id=parent.event_id, event_update_id=_stable_update_id(parent.event_id, material.id))
    folded.metadata['event_id'] = parent.event_id  # Folded node keeps its original update ID.
    items = [initial, material, folded, new]
    before = copy.deepcopy((items, parent))
    meta, events, count = recover_published_links({'audit': 'keep'}, [parent], items, edition='2026-11-05')
    assert count == 3
    assert (items, parent) == before
    assert meta['audit'] == 'keep'
    assignments = known_story_assignments(events)
    assert assignments == {i.id: (i.metadata['event_id'], i.metadata['event_update_id']) for i in items}
    existing = next(e for e in events if e.event_id == parent.event_id)
    assert existing.status == parent.status
    assert existing.current_state_zh == parent.current_state_zh
    assert existing.updates[0] == parent.updates[0]
    assert _stable_event_id(folded.id) in existing.merged_event_ids
    assert all(u.update_type == EventUpdateType.CONFIRMATION and u.confidence == 0 for u in existing.updates[1:])
    for event in events:
        for update in event.updates:
            assert update.detailed_summary_zh == '已发表的完整事实，不重写。'
            assert update.background_zh == '已保存背景。'
            assert update.references[0].url == 'https://reference.example.com/a'
    again = recover_published_links(meta, events, items, edition='2026-11-05')
    assert again == (meta, events, 0)


@pytest.mark.parametrize('failure', ['unknown_parent', 'unknown_update', 'different_membership', 'missing_text', 'duplicate_source'])
def test_invalid_or_ambiguous_recovery_is_atomic(failure):
    original = article('old')
    parent = _new_event(original, story_evidence(original))
    incoming = article('new')
    if failure == 'unknown_parent':
        incoming.metadata.update(event_id='evt_unknownparent', event_update_id=_stable_update_id('evt_unknownparent', incoming.id))
    elif failure == 'unknown_update':
        incoming.metadata['event_update_id'] = 'upd_unprovable'
    elif failure == 'different_membership':
        incoming = original.model_copy(deep=True)
        incoming.metadata['event_id'] = 'evt_unknownparent'
    elif failure == 'missing_text':
        incoming.metadata.pop('detailed_summary_zh'); incoming.metadata.pop('detailed_summary_en')
    else:
        incoming.metadata.update(event_id=parent.event_id, event_update_id=parent.updates[0].update_id)
    metadata = {'unrelated': {'proof': True}}
    before = copy.deepcopy((metadata, [parent], incoming))
    with pytest.raises(StateConflict):
        recover_published_links(metadata, [parent], [article('valid'), incoming], edition='2026-11-05')
    assert (metadata, [parent], incoming) == before


def test_normal_daily_retry_repairs_saved_event_links_without_external_calls(tmp_path, monkeypatch):
    import src.orchestrator as module
    monkeypatch.chdir(tmp_path)
    item = article('saved')
    save_daily_feed_state(DailyFeedState(date='2026-11-05', timezone='Asia/Shanghai', updated_at=NOW, items=[item], x_posted_languages=['zh']))
    save_event_catalog({'original_audit': True}, [])
    before = Path('docs/_data/bmtnews_state.json').read_bytes()
    runner = BMTNewsOrchestrator(Config(ai=AIConfig(provider='openai', model='fixture', api_key_env='NO_KEY', languages=['zh', 'en']),
        sources=SourcesConfig(), filtering=FilteringConfig(daily_timezone='Asia/Shanghai')),
        storage=StorageManager(data_dir=str(tmp_path / 'data')))
    def forbidden(*args, **kwargs):
        pytest.fail('saved event recovery must not call AI, sources, market or delivery')
    for name in ('fetch_all_sources', '_analyze_content', '_update_event_timeline', '_deliver_telegram_editions', '_deliver_x_editions'):
        monkeypatch.setattr(runner, name, forbidden)
    monkeypatch.setattr(module, 'create_ai_client', forbidden)
    monkeypatch.setattr(module, 'fetch_market_snapshot', forbidden)
    asyncio.run(runner.run_daily_edition(now=NOW))
    assert Path('docs/_data/bmtnews_state.json').read_bytes() == before
    event_id = item.metadata['event_id']; update_id = item.metadata['event_update_id']
    api = json.loads(Path(f'docs/api/events/{event_id}.json').read_text())
    assert api['updates'][0]['update_id'] == update_id
    for language in ('zh', 'en'):
        prefix = 'en-' if language == 'en' else ''
        assert f'id="{update_id}"' in Path(f'docs/events/{prefix}{event_id}.html').read_text()
    outputs = {str(p): p.read_bytes() for p in Path('docs').rglob('*') if p.is_file()}
    asyncio.run(runner.run_daily_edition(now=NOW))
    assert outputs == {str(p): p.read_bytes() for p in Path('docs').rglob('*') if p.is_file()}


def test_later_reviewed_merge_with_same_node_needs_no_repair():
    item = article('already-folded')
    original = _new_event(item, story_evidence(item))
    target_id = 'evt_survivingparent'
    merged = original.model_copy(update={
        'event_id': target_id, 'merged_event_ids': [original.event_id],
        'updates': [u.model_copy(update={'event_id': target_id}) for u in original.updates],
    })
    assert recover_published_links({}, [merged], [item], edition='2026-11-05') == ({}, [merged], 0)
