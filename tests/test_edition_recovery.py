"""Cross-day static recovery: no news fetch, model calls or channel writes."""
import asyncio
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from src.api_output import write_edition_api
from src.daily_feed import DailyFeedState, save_daily_feed_state
from src.edition_recovery import import_retained_history, inspect_edition, recover_editions, restore_published_files
from src.models import AIConfig, Config, ContentItem, FilteringConfig, SourcesConfig, SourceType
from src.orchestrator import BMTNewsOrchestrator
from src.publication_state import PublicationState, StateConflict, canonical
from src.storage.manager import StorageManager


NOW = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)


def state(day):
    stamp = datetime.fromisoformat(day + 'T01:00:00+00:00') - timedelta(days=1)
    item = ContentItem(id='rss:' + day, title='Original ' + day,
        url='https://example.com/' + day, source_type=SourceType.RSS,
        published_at=stamp, fetched_at=stamp, ai_score=8.5,
        metadata={'category': 'crypto-markets', 'feed_name': 'Fixture',
            'title_zh': '原始标题 ' + day, 'title_en': 'Original ' + day,
            'detailed_summary_zh': '完整事实正文。', 'detailed_summary_en': 'Full saved facts.',
            'background_zh': '已有背景。', 'background_en': 'Saved background.'})
    return DailyFeedState(date=day, timezone='Asia/Shanghai', updated_at=stamp + timedelta(days=1, hours=1), items=[item])


def runner(root):
    return BMTNewsOrchestrator(Config(ai=AIConfig(provider='openai', model='fixture', api_key_env='NO_KEY', languages=['zh','en']),
        sources=SourcesConfig(), filtering=FilteringConfig(daily_timezone='Asia/Shanghai')),
        storage=StorageManager(data_dir=str(root / 'data')))


def test_daily_rollover_journals_each_selection_atomically_and_survives_restart(tmp_path):
    store = PublicationState(tmp_path / 'state')
    old, new = state('2026-11-03'), state('2026-11-05')
    store.save_document('daily', old.model_dump(mode='json'))
    store.save_document('daily', new.model_dump(mode='json'))
    restarted = PublicationState(tmp_path / 'state')
    assert [d['date'] for d in restarted.saved_editions()] == ['2026-11-03','2026-11-05']
    assert restarted.saved_editions()[0]['items'][0]['metadata']['detailed_summary_zh'] == '完整事实正文。'
    before = restarted.load_document('daily', None)
    assert before['date'] == '2026-11-05'
    # Importing the old selected edition never changes the current document.
    restarted.remember_edition(old.model_dump(mode='json'))
    assert restarted.load_document('daily', None) == before


def test_late_edition_api_does_not_replace_latest(tmp_path):
    api, editions = tmp_path / 'api', tmp_path / 'editions'
    newer = {'date': '2026-11-05','items': [{'title': 'new'}]}
    write_edition_api(newer, date='2026-11-05', api_root=api, editions_root=editions)
    before = (api / 'latest.json').read_bytes()
    write_edition_api({'date': '2026-11-03','items': []}, date='2026-11-03', api_root=api, editions_root=editions)
    assert (api / 'latest.json').read_bytes() == before


def test_missing_old_edition_recovers_while_current_is_complete_and_never_sends(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('XIYUNEWS_STATE_DIR',str(tmp_path / 'state'))
    monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
    store = PublicationState(tmp_path / 'state')
    old, new = state('2026-11-03'), state('2026-11-05')
    save_daily_feed_state(old); save_daily_feed_state(new)
    receipt = {'sent': ['already-confirmed']}
    store.save_document('x_queue', receipt)
    app = runner(tmp_path)
    def forbidden(*args, **kwargs):
        pytest.fail('static recovery must never fetch, call a model or send')
    import src.orchestrator as orchestrator
    monkeypatch.setattr(orchestrator,'create_ai_client',forbidden)
    monkeypatch.setattr(orchestrator,'fetch_market_snapshot',forbidden)
    for name in ('fetch_all_sources','_analyze_content','_update_event_timeline','_deliver_telegram_editions','_deliver_x_editions'):
        monkeypatch.setattr(app,name,forbidden)
    # First publish only today's snapshot; old rows still exist in the journal.
    report = app.last_run_report
    from src.run_report import RunReport
    report = RunReport.start(date=new.date, timezone_name=new.timezone, started_at=NOW, kind='static_recovery')
    report.set_metric('displayed_today',1)
    asyncio.run(app._publish_outputs(new.items,date=new.date,total_candidates=0,timezone_name=new.timezone,run_report=report,static_only=True))
    app._publish_archive_artifacts(new.items,date=new.date,run_report=report)
    latest = Path('docs/api/latest.json').read_bytes()
    current = Path('docs/_data/bmtnews_state.json').read_bytes()
    result = asyncio.run(recover_editions(app,store,now=NOW))
    assert [r['date'] for r in result['repaired']] == [old.date]
    assert result['ai_calls'] == result['channel_calls'] == 0
    assert inspect_edition(old) == inspect_edition(new) == []
    assert Path('docs/api/latest.json').read_bytes() == latest
    assert Path('docs/_data/bmtnews_state.json').read_bytes() == current
    assert store.load_document('x_queue',None) == receipt
    assert [e['date'] for e in json.loads(Path('docs/api/editions.json').read_text())['editions']] == [new.date,old.date]
    assert '已有背景。' in Path('docs/editions/2026-11-03/zh.html').read_text()
    old_outputs = {str(p):p.read_bytes() for p in Path('docs/editions').rglob('*') if p.is_file()}
    assert asyncio.run(recover_editions(app,store,now=NOW))['repaired'] == []
    assert old_outputs == {str(p):p.read_bytes() for p in Path('docs/editions').rglob('*') if p.is_file()}
    # Simulate a replacement state backend rehydrating the portable Git log.
    with store.connect() as db:
        db.execute('DELETE FROM publication_editions WHERE date=?',(old.date,))
    assert asyncio.run(recover_editions(app,store,now=NOW))['repaired'] == []
    assert [e['date'] for e in store.saved_editions()] == [old.date,new.date]
    # JSON exists but an English fragment disappeared: still recover it.
    Path('docs/editions/2026-11-03/en.html').unlink()
    assert [r['date'] for r in asyncio.run(recover_editions(app,store,now=NOW))['repaired']] == [old.date]


def test_legacy_retained_import_requires_count_sources_groups_and_complete_text(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    store=PublicationState(tmp_path / 'state')
    old,new=state('2026-11-03'),state('2026-11-05')
    new.dedup_history=old.items
    store.save_document('daily',new.model_dump(mode='json'))
    app=runner(tmp_path)
    report={'kind':'daily_publish','date':old.date,'started_at':old.updated_at.isoformat(),'timezone':old.timezone,
        'metrics':{'edition_candidates':20,'displayed_today':1},
        'breakdowns':{'final_selected_sources':app._source_breakdown(old.items),'final_selected_groups':app._group_breakdown(old.items)}}
    store.save_report(report)
    assert import_retained_history(store,app,today=date(2026,11,5))[0]['original_tied_rank_available'] is False
    assert store.load_document('daily',None)['date'] == new.date
    with store.connect() as db:
        db.execute('DELETE FROM publication_editions WHERE date=?',(old.date,))
    report['metrics']['displayed_today']=2
    store.save_report(report)
    with pytest.raises(StateConflict,match='no unique complete'):
        import_retained_history(store,app,today=date(2026,11,5))
    assert [e['date'] for e in store.saved_editions()] == [new.date]


def test_restored_git_history_never_overwrites_new_local_files(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    def git(*args):
        return subprocess.check_output(['git',*args],text=True).strip()
    git('init','-b','main');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
    source=Path('editions/2026-11-03/zh.html');source.parent.mkdir(parents=True);source.write_text('published original')
    git('add','.');git('commit','-m','published fixture')
    ref=git('rev-parse','HEAD')
    target=Path('docs')/source
    restore_published_files(ref=ref)
    assert target.read_text() == 'published original'
    target.write_text('newer local output')
    restore_published_files(ref=ref)
    assert target.read_text() == 'newer local output'


def test_actual_cli_runs_with_isolated_backend_without_credentials(tmp_path):
    root=Path(__file__).resolve().parents[1]
    def git(*args):
        return subprocess.check_output(['git',*args],cwd=tmp_path,text=True).strip()
    git('init','-b','main');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
    (tmp_path/'published.txt').write_text('fixture')
    git('add','.');git('commit','-m','fixture')
    git('update-ref','refs/remotes/origin/gh-pages',git('rev-parse','HEAD'))
    config=Config(ai=AIConfig(provider='openai',model='fixture',api_key_env='NO_KEY',languages=['zh','en']),
        sources=SourcesConfig(),filtering=FilteringConfig(daily_timezone='Asia/Shanghai'))
    (tmp_path/'config.json').write_text(config.model_dump_json())
    result=subprocess.run([sys.executable,'-m','src.edition_recovery','--config','config.json'],cwd=tmp_path,
        env={**os.environ,'PYTHONPATH':str(root),'XIYUNEWS_STATE_DIR':str(tmp_path/'state'),'GITHUB_ACTIONS':'false'},
        capture_output=True,text=True,check=True)
    assert json.loads(result.stdout)['repaired'] == []
    assert json.loads((tmp_path/'docs/_data/edition-journal.json').read_text()) == {'version':1,'editions':[]}


def test_deploy_docs_uses_its_pinned_second_checkout_without_root_remote_ref(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source=tmp_path/'current-site';source.mkdir()
    def git(*args):
        return subprocess.check_output(['git',*args],cwd=source,text=True).strip()
    git('init','-b','publication');git('config','user.name','Fixture');git('config','user.email','fixture@example.invalid')
    p=source/'editions/2026-11-03/zh.html';p.parent.mkdir(parents=True);p.write_text('pinned original')
    older=source/'editions/2026-10-01/zh.html';older.parent.mkdir(parents=True);older.write_text('irrelevant old snapshot')
    git('add','.');git('commit','-m','pinned published fixture')
    restore_published_files(days={'2026-11-03'})
    assert Path('docs/editions/2026-11-03/zh.html').read_text() == 'pinned original'
    assert not Path('docs/editions/2026-10-01/zh.html').exists()
