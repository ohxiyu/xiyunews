import asyncio
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import httpx
import pytest

from src.ai.analyzer import ContentAnalyzer
from src.ai.chinese import chinese_ready, repair_chinese
from src.ai.enricher import ContentEnricher
from src.ai.errors import ProviderAccountError
from src.ai.prefilter import ContentPrefilter
from src.edition import edition_window_for
from src.edition_fallback import cached_selection, save_selection
from src.models import Config, ContentItem, SourceType
from src.operations import budget, estimate_cost, private_alert, record_cost
from src.publication_state import PublicationState

NOW=datetime(2026,11,9,0,tzinfo=timezone.utc)


def item(n=0, *, chinese=True):
    return ContentItem(id=f'item{n}',title='项目安全更新' if chinese else 'Security update',
        url=f'https://example.com/{n}',source_type=SourceType.RSS,
        published_at=NOW-timedelta(hours=1),ai_score=8.5,
        ai_summary='项目发布了安全修复。' if chinese else 'A security fix.')


def test_english_scoring_repairs_once_without_changing_score():
    calls=[]
    async def complete(**kwargs):
        calls.append(kwargs)
        return json.dumps({'score':8.5,'summary':'Security fix','reason':'relevant','tags':['security']}) if len(calls)==1 else '{"title_zh":"项目安全更新","summary_zh":"项目发布安全修复。"}'
    value=item(chinese=False)
    asyncio.run(ContentAnalyzer(SimpleNamespace(complete=complete,config=SimpleNamespace(languages=['zh'])))._analyze_item(value))
    assert len(calls)==2 and chinese_ready(value) and value.ai_score==8.5
    assert 'title_zh' in calls[0]['system']


def test_invalid_translation_is_not_accepted():
    calls=[]
    async def complete(**kwargs):
        calls.append(kwargs)
        return '{"title_zh":"English","summary_zh":"Still English"}'
    value=item(chinese=False)
    assert not asyncio.run(repair_chinese(value,SimpleNamespace(complete=complete)))
    assert len(calls)==1 and value.metadata['chinese_invalid']


def test_enrichment_402_stops_queued_calls_without_translation(monkeypatch):
    calls=[]
    async def complete(**kwargs):
        calls.append(kwargs)
        raise ProviderAccountError(402)
    client=SimpleNamespace(complete=complete,config=SimpleNamespace(enrichment_concurrency=1))
    values=[item(n) for n in range(5)]
    asyncio.run(ContentEnricher(client,languages=['zh']).enrich_batch(values))
    assert len(calls)==1
    assert all(v.metadata['edition_mode']=='brief' and chinese_ready(v) for v in values)
    assert all(not v.metadata.get('background_zh') for v in values)


def test_prefilter_account_block_does_not_fail_open_or_leave_peers():
    calls=[]
    async def complete(**kwargs):
        calls.append(kwargs)
        raise ProviderAccountError(402)
    client=SimpleNamespace(complete=complete,config=SimpleNamespace(analysis_concurrency=1))
    with pytest.raises(ProviderAccountError):
        asyncio.run(ContentPrefilter(client,batch_size=5).select([item(n) for n in range(30)],maximum=5))
    assert len(calls)==1


def test_checkpoint_never_uses_wrong_window_model_english_or_low_score(tmp_path):
    config=Config.model_validate_json(open('data/config.github.json').read())
    window=edition_window_for(NOW,'Asia/Shanghai')
    good=item();good.published_at=window.end-timedelta(seconds=1)
    expired=item(1);expired.published_at=window.start-timedelta(seconds=1)
    future=item(2);future.published_at=window.end
    english=item(3,chinese=False);english.published_at=good.published_at
    low=item(4);low.published_at=good.published_at;low.ai_score=1
    path=tmp_path/'qualified.json'
    save_selection([good,expired,future,english,low],config,window,now=NOW,path=path)
    result=cached_selection(config,window,path=path)
    assert [v.id for v in result]==[good.id]
    assert result[0].metadata['edition_mode']=='brief'
    config.ai.model='other'
    assert cached_selection(config,window,path=path)==[]


def usage(**kwargs):
    return dict(provider='siliconflow',model='deepseek-ai/DeepSeek-V3.2',calls=1,input_tokens=1000000,cached_input_tokens=500000,output_tokens=100000,reasoning_tokens=100000,**kwargs)


def test_cost_counts_cache_discount_without_double_counting_reasoning():
    cost=estimate_cost([usage()])
    assert cost['amount']==pytest.approx(2.8) and cost['complete']
    cost=estimate_cost([{'provider':'unknown','calls':1}])
    assert not cost['complete'] and cost['unpriced_rows']==1


def test_cost_ledger_idempotent_and_balance_requires_baseline_and_seven_days(tmp_path):
    store=PublicationState(tmp_path)
    for n in range(7):
        date=NOW-timedelta(days=n+1)
        report=dict(run_id=str(n),started_at=date.isoformat(),ai_usage=[usage()])
        record_cost(report,store);record_cost(report,store)
    assert budget(store,now=NOW,env={})['balance_status']=='unknown'
    result=budget(store,now=NOW,env={'AI_BALANCE_BASELINE_CNY':'56','AI_BALANCE_BASELINE_AT':(NOW-timedelta(days=8)).isoformat()})
    assert result['coverage_days']==7 and result['remaining_days']==pytest.approx(13)
    with store.connect() as db:
        assert db.execute('SELECT COUNT(*) FROM operations_costs').fetchone()[0]==7


@pytest.mark.parametrize('kind',['group','supergroup','channel'])
def test_private_alert_refuses_non_private_destinations(tmp_path,kind):
    requests=[]
    def handle(request):
        requests.append(request)
        return httpx.Response(200,json={'ok':True,'result':{'type':kind,'id':123}})
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            return await private_alert('test','test',store=PublicationState(tmp_path),client=client,env={'TELEGRAM_BOT_TOKEN':'redacted','TELEGRAM_ALERT_CHAT_ID':'123'})
    assert asyncio.run(run())=='destination_unverified'
    assert len(requests)==1


def test_private_unknown_is_never_retried_after_restart(tmp_path):
    sends=[]
    def handle(request):
        if request.url.path.endswith('getChat'):
            return httpx.Response(200,json={'ok':True,'result':{'type':'private','id':123}})
        sends.append(request)
        raise httpx.ReadTimeout('secret-url')
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
            args=dict(client=client,env={'TELEGRAM_BOT_TOKEN':'redacted','TELEGRAM_ALERT_CHAT_ID':'123'})
            assert await private_alert('one','test',store=PublicationState(tmp_path),**args)=='unknown'
            assert await private_alert('one','test',store=PublicationState(tmp_path),**args)=='already_attempted'
    asyncio.run(run())
    assert len(sends)==1


def test_cached_brief_publication_has_no_ai_and_preserves_existing(tmp_path,monkeypatch):
    import src.orchestrator as module
    from src.orchestrator import BMTNewsOrchestrator
    from src.daily_feed import DailyFeedState,load_daily_feed_state
    from src.run_report import RunReport
    config=Config.model_validate_json(open('data/config.github.json').read())
    monkeypatch.chdir(tmp_path)
    window=edition_window_for(NOW,'Asia/Shanghai')
    good=item();good.published_at=window.end-timedelta(seconds=1)
    save_selection([good],config,window,now=NOW)
    runner=BMTNewsOrchestrator.__new__(BMTNewsOrchestrator);runner.config=config
    calls=[]
    async def publish(items,**kwargs):
        calls.append('publish')
        assert all(v.metadata['edition_mode']=='brief' for v in items)
    def archive(items,**kwargs):calls.append('archive')
    runner._publish_outputs=publish;runner._publish_archive_artifacts=archive
    report=RunReport.start(date=window.date,timezone_name='Asia/Shanghai',kind='daily_publish',started_at=NOW)
    assert asyncio.run(runner._publish_cached_brief(window,report,NOW))
    assert calls==['publish','archive'] and report.metrics['edition_degraded']==1
    restored=load_daily_feed_state(window.date,'Asia/Shanghai')
    assert restored.items[0].metadata['edition_mode']=='brief'
    calls.clear()
    assert asyncio.run(runner._publish_cached_brief(window,report,NOW))
    assert not calls


def test_brief_rendering_failure_is_never_reported_as_success(tmp_path,monkeypatch):
    from src.orchestrator import BMTNewsOrchestrator
    from src.run_report import RunReport
    config=Config.model_validate_json(open('data/config.github.json').read())
    monkeypatch.chdir(tmp_path)
    window=edition_window_for(NOW,'Asia/Shanghai')
    good=item();good.published_at=window.end-timedelta(seconds=1)
    save_selection([good],config,window,now=NOW)
    runner=BMTNewsOrchestrator.__new__(BMTNewsOrchestrator);runner.config=config
    async def broken(*args,**kwargs):raise OSError('render failed')
    runner._publish_outputs=broken
    report=RunReport.start(date=window.date,timezone_name='Asia/Shanghai',kind='daily_publish',started_at=NOW)
    with pytest.raises(OSError):asyncio.run(runner._publish_cached_brief(window,report,NOW))
    report.finish()
    assert report.status=='failure'
