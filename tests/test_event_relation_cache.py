import asyncio
import json
import pytest
from src.ai.event_relations import (classify_event_relation, compact_context, relation_user,
    relation_cache_input, EventRelationError, _event_context, _story_context)
from src.ai.prompts import EVENT_RELATION_SYSTEM, EVENT_RELATION_USER
from src.ai.result_cache import AnalysisResultCache
from src.event_pipeline import story_evidence
from src.events import EventRelation, EventUpdateType
from test_event_pipeline import existing_event, item, decision


class Client:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0
    async def complete(self, **kwargs):
        self.calls += 1
        return json.dumps(self.payload)


def test_relation_survives_partial_retry_and_full_input_changes_invalidate(tmp_path):
    event = existing_event()
    article = item('recovery', title='Tectonic confirms recovery after exploit')
    article.content = 'Confirmed loss: $5 million. ' * 20
    story = story_evidence(article)
    cache = AnalysisResultCache(tmp_path / 'cache.json', model='fixture:stable')
    expected = decision(EventRelation.SAME_EVENT_UPDATE, update_type=EventUpdateType.RESOLUTION)
    client = Client(expected.model_dump(mode='json'))
    def classify(e=event, s=story, c=cache):
        return asyncio.run(classify_event_relation(client, event=e, story=s, cache=c))
    assert classify() == expected
    fresh = AnalysisResultCache(cache.path, model='fixture:stable')
    assert classify(c=fresh) == expected
    assert client.calls == 1
    assert fresh.relation_hits == 1
    assert classify(e=event.model_copy(update={'current_state_en':'Confirmed loss: $6 million.'}), c=fresh) == expected
    assert client.calls == 2
    assert classify(s=story.model_copy(update={'source_excerpt':'Additional confirmed reimbursement evidence.'}), c=fresh) == expected
    assert client.calls == 3
    changed_rules = AnalysisResultCache(cache.path, model='fixture:stable', prompt_revision='new-rules')
    classify(c=changed_rules)
    assert client.calls == 4
    assert not fresh.entries  # Relation budget never evicts score entries.


def test_invalid_or_headline_material_response_never_cached(tmp_path):
    event = existing_event()
    article = item('headline', title='Tectonic exploit')
    article.content = article.title
    story = story_evidence(article)
    cache = AnalysisResultCache(tmp_path / 'cache.json', model='fixture:stable')
    expected = decision(EventRelation.SAME_EVENT_UPDATE, update_type=EventUpdateType.RESOLUTION)
    client = Client(expected.model_dump(mode='json'))
    with pytest.raises(EventRelationError, match='headline-only'):
        asyncio.run(classify_event_relation(client, event=event, story=story, cache=cache))
    assert not cache.relation_pairs
    user = relation_user(event, story)
    cache.store_relation(EVENT_RELATION_SYSTEM, relation_cache_input(event, story, user), {'candidate_event_id':'wrong'})
    client.payload = decision(EventRelation.DUPLICATE_COVERAGE).model_dump(mode='json')
    result = asyncio.run(classify_event_relation(client, event=event, story=story, cache=cache))
    assert result.relation is EventRelation.DUPLICATE_COVERAGE
    assert client.calls == 2


def test_compact_prompt_retains_distinct_facts_and_all_source_evidence():
    assert compact_context({'summary_zh':'same','summary_en':'same'}) == {'summary_zh':'same'}
    assert compact_context({'summary_zh':'损失500万','summary_en':'Reimbursement $6m'}) == {'summary_zh':'损失500万','summary_en':'Reimbursement $6m'}
    event = existing_event()
    article = item('recovery', title='Tectonic loss $5m, reimbursement $6m')
    article.content = 'Loss $5m; proposal $6m, not confirmed; 2026-10-13. ' * 20
    story = story_evidence(article)
    compact = relation_user(event, story)
    original = EVENT_RELATION_USER.format(event=json.dumps(_event_context(event), ensure_ascii=False, indent=2),
        story=json.dumps(_story_context(story), ensure_ascii=False, indent=2))
    assert len(compact.encode()) < len(original.encode())
    assert story.source_excerpt in compact
    assert event.current_state_zh in compact and event.current_state_en in compact
    assert 'headline_only' not in compact


def test_headline_candidate_waits_without_any_paid_call_then_accepts_new_evidence():
    from src.event_pipeline import update_events
    article = item('deferred', title='Tectonic exploit loss confirmed')
    article.content = article.title
    async def never(*args):
        raise AssertionError('headline evidence must not call a model')
    events, result = asyncio.run(update_events([article], [existing_event()], client=None, classifier=never))
    assert result.evidence_deferred == 1 and result.candidates_classified == 0
    assert len(events[0].updates) == 1 and article.metadata['event_retry_pending']
    article.content = 'Confirmed Tectonic loss estimate and reimbursement evidence. ' * 10
    async def accept(*args):
        return decision(EventRelation.SAME_EVENT_UPDATE, update_type=EventUpdateType.CONFIRMATION)
    events, result = asyncio.run(update_events([article], events, client=object(), classifier=accept))
    assert result.material_updates == 1 and result.evidence_deferred == 0
