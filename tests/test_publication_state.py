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
    assert state.load_document('queue', pending) == pending  # local reread is not an ACK
    state.acknowledge_document('queue', pending)
    updated = {**pending, 'pending':[], 'sent':['1','3']}
    assert state.load_document('queue', updated) == updated


def test_own_export_read_does_not_acknowledge_or_allow_stale_git_overwrite(tmp_path):
    state = PublicationState(tmp_path / 'state')
    old, new = {'events': ['old']}, {'events': ['old', 'new']}
    state.load_document('events', old)
    state.save_document('events', new)
    assert state.load_document('events', new) == new
    # Reopening simulates a later producer after publication failed.
    restarted = PublicationState(tmp_path / 'state')
    assert restarted.load_document('events', old) == new
    with restarted.connect() as db:
        assert db.execute("SELECT dirty FROM publication_documents WHERE name='events'").fetchone()[0] == 1
    with pytest.raises(StateConflict):
        restarted.load_document('events', {'events': ['other-writer']})


def test_snapshot_ack_rolls_back_all_documents_if_any_changed(tmp_path):
    state = PublicationState(tmp_path / 'state')
    state.save_document('events', {'a': 1})
    state.save_document('daily', {'a': 2})
    with pytest.raises(StateConflict):
        state.acknowledge_documents({'events': {'a': 1}, 'daily': {'a': 1}})
    with state.connect() as db:
        assert list(db.execute('SELECT dirty FROM publication_documents')) == [(1,), (1,)]


def test_publication_ack_reads_real_remote_and_preserves_unpublished_changes(tmp_path, monkeypatch):
    import subprocess
    from src.publication_state import acknowledge_published_snapshot
    work, remote = tmp_path / 'work', tmp_path / 'remote.git'
    work.mkdir()
    def git(*args, cwd=work):
        return subprocess.check_output(['git', *map(str, args)], cwd=cwd, text=True).strip()
    git('init', '--bare', remote)
    git('init', '-b', 'main')
    git('config', 'user.name', 'Offline fixture')
    git('config', 'user.email', 'fixture@example.invalid')
    git('remote', 'add', 'origin', remote)
    path = work / 'docs/_data/events.json'
    path.parent.mkdir(parents=True)
    old, new = {'events': ['old']}, {'events': ['old', 'new']}
    # Publication branch paths omit the source docs/ prefix.
    exported = work / '_data/events.json'
    exported.parent.mkdir(); exported.write_text(json.dumps(old))
    git('add', '_data'); git('commit', '-m', 'old snapshot')
    git('push', 'origin', 'HEAD:gh-pages')
    monkeypatch.chdir(work)
    monkeypatch.setenv('XIYUNEWS_STATE_DIR', str(tmp_path / 'state'))
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    state = PublicationState(tmp_path / 'state')
    state.load_document('events', old)
    state.save_document('events', new)
    path.write_text(json.dumps(new))
    with pytest.raises(StateConflict, match='published bytes differ'):
        acknowledge_published_snapshot()
    assert state.load_document('events', old) == new
    exported.write_text(json.dumps(new))
    git('add', '_data'); git('commit', '-m', 'successful publication')
    git('push', 'origin', 'HEAD:gh-pages')
    result = acknowledge_published_snapshot()
    assert result == {'acknowledged': ['events'], 'artifact_commit': git('rev-parse', 'HEAD')}
    with state.connect() as db:
        assert db.execute("SELECT dirty FROM publication_documents WHERE name='events'").fetchone()[0] == 0
    newer = {'events': ['old', 'new', 'concurrent']}
    state.save_document('events', newer)
    with pytest.raises(StateConflict, match='changed before checkpoint'):
        acknowledge_published_snapshot()
    assert state.load_document('events', None) == newer


def test_every_catalog_publisher_confirms_only_after_the_publication_action():
    root = Path(__file__).resolve().parents[1]
    for name in ('daily-summary', 'feed-collection', 'deploy-docs', 'event-archive-migration'):
        text = (root / '.github/workflows' / (name + '.yml')).read_text()
        action = text.index('uses: peaceiris/actions-gh-pages@v4')
        ack = text.index('      - name: Confirm exact published state checkpoint')
        assert ack > action
        step = text[ack:].split('\n      - name:', 1)[0]
        assert 'if:' not in step
        assert '--acknowledge-published' in step


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
