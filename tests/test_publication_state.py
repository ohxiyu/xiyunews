from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import pytest
from src.publication_state import PublicationState, StateConflict, active_store
from src.ai.result_cache import AnalysisResultCache
from src.edition import load_staging_state, save_staging_state
from src.models import ContentItem, SourceType


def test_unpublished_state_survives_stale_audit_and_conflict_preserves_both(tmp_path):
    state = PublicationState(tmp_path / 'state')
    old = {'sent':['1'], 'unknown':['2']}
    assert state.load_document('queue', old) == old
    pending = {**old, 'pending':['3']}
    state.save_document('queue', pending)
    assert state.load_document('queue', old) == pending
    with pytest.raises(StateConflict):
        state.load_document('queue', {**old, 'sent':['1','4']})
    assert state.load_document('queue', None) == pending
    assert state.load_document('queue', pending) == pending  # audit caught up
    updated = {**pending, 'pending':[], 'sent':['1','3']}
    assert state.load_document('queue', updated) == updated


def test_cache_import_once_delta_rows_and_transaction_rollback(tmp_path):
    state = PublicationState(tmp_path / 'state')
    original = {'version':1,'entries':{'a':{'stored_at':'2026-10-13T00:00:00+00:00','value':{'score_model':'fixture:stable','ai_score':8}}},'relation_pairs':{},'prefilter_batches':{}}
    assert state.load_cache(original) == original
    assert state.load_cache({'version':1,'entries':{}}) == original
    changed = json.loads(json.dumps(original))
    changed['relation_pairs']['b']={'stored_at':'2026-10-13T00:00:00+00:00','value':{'relation':'duplicate_coverage'}}
    state.save_cache(changed)
    with state.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM ai_cache').fetchone()[0] == 2
    # Namespace error occurs after earlier rows; the WHOLE update rolls back.
    broken = {**changed, 'entries':{}, 'relation_pairs':[]}
    with pytest.raises(ValueError):
        state.save_cache(broken)
    assert state.load_cache({}) == changed


def test_ci_never_activates_business_storage(monkeypatch,tmp_path):
    monkeypatch.setenv('XIYUNEWS_STATE_DIR',str(tmp_path / 'state'))
    monkeypatch.setenv('GITHUB_ACTIONS','true')
    monkeypatch.setenv('GITHUB_REPOSITORY','ohxiyu/xiyunews')
    monkeypatch.setenv('GITHUB_REF','refs/heads/main')
    monkeypatch.setenv('GITHUB_WORKFLOW','CI')
    assert active_store() is None
    assert not (tmp_path / 'state').exists()
    monkeypatch.setenv('GITHUB_WORKFLOW','xiyu.news Feed Collection')
    assert active_store() is not None
    monkeypatch.setenv('GITHUB_REF','refs/pull/1/merge')
    assert active_store() is None


def test_bootstrap_atomic_exact_and_never_overwrites_live_state(tmp_path):
    state=PublicationState(tmp_path / 'state')
    cache={'version':1,'entries':{'score':{'stored_at':'2026-10-13T00:00:00Z','value':{'score_model':'fixture','ai_score':8}}}}
    documents={'x_queue':{'jobs':[{'status':'unknown','id':'stable'}]},'staging':{'items':[]}}
    result=state.bootstrap(cache,documents)
    assert result['cache_imported']
    assert len(result['inserted_documents']) == 2
    state.save_document('x_queue', {'jobs':[{'status':'sent','id':'stable'}]})
    assert not state.bootstrap({'version':1,'entries':{}}, documents)['cache_imported']
    assert state.load_document('x_queue', None)['jobs'][0]['status'] == 'sent'
    assert state.verify()['verified']


def test_staging_and_paid_cache_survive_clean_job_workspace(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('XIYUNEWS_STATE_DIR',str(tmp_path / 'state'))
    monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
    moment=datetime.now(timezone.utc)
    article=ContentItem(id='rss:one',title='Actual fixture',url='https://example.com/one',source_type=SourceType.RSS,published_at=moment,fetched_at=moment,ai_score=8,ai_reason='fixture',metadata={'score_model':'fixture:stable'})
    save_staging_state([article])
    Path('data/staging-items.json').unlink()
    assert load_staging_state().items[0].id == article.id
    cache=AnalysisResultCache(Path('data/analysis-cache.json'),model='fixture:stable')
    cache.store_analysis(article)
    cache.save(export_json=False)
    assert not cache.path.exists()  # durable SQLite, no per-result blob rewrite
    restored=AnalysisResultCache(cache.path,model='fixture:stable')
    raw=article.model_copy(update={'ai_score':None,'ai_reason':None,'metadata':{}})
    assert restored.restore_analysis(raw) and raw.ai_score == 8
    assert raw.metadata['score_model'] == 'fixture:stable'
    restored.save()
    assert json.loads(restored.path.read_text())['entries']
