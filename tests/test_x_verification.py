"""Publication/identity failures must stop before a durable public-send attempt."""
import asyncio
import hashlib
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from unittest.mock import AsyncMock
import httpx
import pytest
from src.daily_feed import DailyFeedState
from src.core_site import render_core_feed
from src.archive import build_records
from src.api_output import build_edition_payload
from src.x_verification import verify_published_edition
from src.services.x_delivery import XEditionPublisher,_oauth_header
from src.models import XDeliveryConfig
from test_x_quality import article

NOW=datetime(2026,11,10,0,tzinfo=timezone.utc)
PUBLISHED=NOW-timedelta(minutes=30)


def publication(tmp_path):
    item=article();item.published_at=NOW-timedelta(hours=12)
    state=DailyFeedState(date='2026-11-10',timezone='Asia/Shanghai',updated_at=PUBLISHED-timedelta(minutes=4),items=[item])
    path=tmp_path/'state.json';path.write_text(state.model_dump_json());raw=path.read_bytes()
    root=tmp_path/'proof';root.mkdir()
    report=json.dumps({'kind':'daily_publish','date':state.date,'started_at':state.updated_at.isoformat()}).encode()
    (root/'run-report.json').write_bytes(report)
    proof={'version':1,'verified':True,'source_run_id':'123','edition_date':state.date,
      'source_commit':'a'*40,'artifact_commit':'b'*40,'verified_at':PUBLISHED.isoformat(),
      'source_report_sha256':hashlib.sha256(report).hexdigest(),'selection_sha256':hashlib.sha256(raw).hexdigest()}
    (root/'production-edition.json').write_text(json.dumps(proof))
    public=build_edition_payload(build_records(state.items,date=state.date,top_category_of=lambda _:''),date=state.date,stats={})
    body=render_core_feed(state.items,date=state.date)
    html=f'<header data-latest-edition-date="{state.date}"></header><section class="daily-day" data-date="{state.date}">{body}</section>'
    return state,path,root,public,html


def verify(state,path,root,public,home,dated=None):
    def handler(request):
        assert request.headers.get('Authorization') is None
        if request.url.path=='/api/latest.json':return httpx.Response(200,json=public)
        return httpx.Response(200,text=home if request.url.path=='/' else dated or home)
    async def call():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await verify_published_edition(state,now=NOW,root=root,state_path=path,client=client)
    return asyncio.run(call())


def test_true_publication_time_is_proven_separately_from_generation(tmp_path):
    state,path,root,public,html=publication(tmp_path)
    from bs4 import BeautifulSoup
    saved = BeautifulSoup(html, 'html.parser')
    background = saved.select_one('.story-background')
    background.name = 'details'
    label = background.select_one('.background-label')
    label.name = 'summary'
    del label['class']
    assert verify(state,path,root,public,html,dated=str(saved))==PUBLISHED!=state.updated_at


@pytest.mark.parametrize('change',['background','summary','title','revision','date'])
def test_stale_or_changed_actual_html_cannot_authorize_x(tmp_path,change):
    state,path,root,public,html=publication(tmp_path)
    if change=='background':bad=html.replace('该钱包由Acme提供','该钱包由新机构提供')
    elif change=='summary':bad=html.replace('并非200万美元','为300万美元')
    elif change=='title':bad=html.replace('钱包软件修复已公布的安全问题','其他消息标题')
    elif change=='revision':bad=html.replace('data-content-revision="','data-content-revision="bad')
    else:bad=html.replace('data-date="2026-11-10"','data-date="2026-11-09"')
    with pytest.raises(ValueError):verify(state,path,root,public,bad)
    with pytest.raises(ValueError):verify(state,path,root,public,html,dated=bad)


def test_changed_api_or_local_selection_fails_closed(tmp_path):
    state,path,root,public,html=publication(tmp_path)
    public['items'][0]['score']=7
    with pytest.raises(ValueError):verify(state,path,root,public,html)
    state.items[0].metadata['background_zh']='改动后的背景。'
    with pytest.raises(ValueError,match='selection changed'):verify(state,path,root,public,html)


def test_code_push_or_unverified_proof_cannot_authorize_public_x(tmp_path):
    state,path,root,public,html=publication(tmp_path)
    proof=json.loads((root/'production-edition.json').read_text());proof['source_run_id']=None
    (root/'production-edition.json').write_text(json.dumps(proof))
    with pytest.raises(ValueError,match='proof required'):verify(state,path,root,public,html)


def publisher(monkeypatch,handler):
    for name in ('X_CONSUMER_KEY','X_CONSUMER_SECRET','X_ACCESS_TOKEN','X_ACCESS_SECRET'):monkeypatch.setenv(name,'fixture-only-value')
    return XEditionPublisher(XDeliveryConfig(),transport=httpx.MockTransport(handler))


def test_readonly_verification_identifies_expected_account_and_real_observed_followers(monkeypatch):
    requests=[]
    def handler(request):
        requests.append(request)
        return httpx.Response(200,json={'data':{'id':'123','username':'ohxiyu','public_metrics':{'followers_count':42}}})
    result=asyncio.run(publisher(monkeypatch,handler).verify_account())
    assert result=={'status':'verified','username':'ohxiyu','write_access':'not_yet_observed','followers_count':42}
    assert len(requests)==1 and requests[0].method=='GET' and requests[0].url.path=='/2/users/me'
    assert requests[0].url.params['user.fields']=='public_metrics'


@pytest.mark.parametrize('response,expected',[(httpx.Response(401,json={'secret':'must not log'}),'unavailable'),(httpx.Response(403),'unavailable'),(httpx.Response(200,json={'data':{'id':'123','username':'other'}}),'wrong_account'),(httpx.Response(200,text='bad'),'unavailable')])
def test_failed_or_wrong_identity_is_not_post_permission(monkeypatch,response,expected):
    result=asyncio.run(publisher(monkeypatch,lambda _:response).verify_account())
    assert result['status']==expected and 'must not log' not in str(result)


def test_oauth_query_parameters_are_signed_in_canonical_order():
    args=dict(consumer_key='fixture',consumer_secret='fixture',access_token='fixture',access_secret='fixture',nonce='n',timestamp='1')
    base='https://api.x.com/2/users/me'
    a=_oauth_header('GET',base+'?user.fields=public_metrics&x=a',**args)
    assert a==_oauth_header('GET',base+'?x=a&user.fields=public_metrics',**args)
    assert a!=_oauth_header('GET',base,**args)
    assert a!=_oauth_header('GET',base+'?user.fields=id&x=a',**args)


def test_publication_failure_stops_before_any_ai_or_send_checkpoint(tmp_path,monkeypatch):
    import src.x_distribution as module
    from test_x_queue import orchestrator_for,FakePublisher,ON_TIME,DAY,item
    state=DailyFeedState(date=DAY,timezone='Asia/Shanghai',updated_at=ON_TIME,items=[item(1)])
    fake=FakePublisher();fake.verify_account=AsyncMock(return_value={'status':'verified'})
    runner=orchestrator_for(fake)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module,'load_daily_feed_state',lambda *a:state)
    monkeypatch.setattr(module,'verify_published_edition',AsyncMock(side_effect=ValueError('not deployed')))
    monkeypatch.setattr(module,'create_ai_client',lambda _:pytest.fail('no AI before publication'))
    monkeypatch.setattr('src.orchestrator.save_run_report',lambda _:None)
    path=tmp_path/'queue.json'
    with pytest.raises(ValueError,match='not deployed'):asyncio.run(runner.run_x_slot(now=ON_TIME,state_path=path))
    assert not path.exists() and fake.posts==[]
    fake.verify_account.assert_not_awaited()


def test_wrong_account_stops_before_ai_or_a_send_receipt(tmp_path,monkeypatch):
    import src.x_distribution as module
    from test_x_queue import orchestrator_for,FakePublisher,ON_TIME,DAY,item
    state=DailyFeedState(date=DAY,timezone='Asia/Shanghai',updated_at=ON_TIME,items=[item(1)])
    fake=FakePublisher();fake.verify_account=AsyncMock(return_value={'status':'wrong_account'})
    runner=orchestrator_for(fake);monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module,'load_daily_feed_state',lambda *a:state)
    monkeypatch.setattr(module,'verify_published_edition',AsyncMock(return_value=ON_TIME))
    monkeypatch.setattr(module,'create_ai_client',lambda _:pytest.fail('no AI for wrong account'))
    monkeypatch.setattr('src.orchestrator.save_run_report',lambda _:None)
    path=tmp_path/'queue.json'
    with pytest.raises(RuntimeError,match='could not be verified'):asyncio.run(runner.run_x_slot(now=ON_TIME,state_path=path))
    assert fake.posts==[] and not path.exists()


def test_production_change_after_planning_never_reaches_http_attempt(tmp_path,monkeypatch):
    import src.x_distribution as module
    from test_x_queue import orchestrator_for,FakePublisher,ON_TIME,DAY,item
    state=DailyFeedState(date=DAY,timezone='Asia/Shanghai',updated_at=ON_TIME,items=[item(1)])
    fake=FakePublisher();runner=orchestrator_for(fake);monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(module,'load_daily_feed_state',lambda *a:state)
    monkeypatch.setattr(module,'verify_published_edition',AsyncMock(side_effect=[ON_TIME,ValueError('changed production')]))
    client=type('Client',(),{'complete':AsyncMock(return_value='{"sentences":[0,1]}')})()
    monkeypatch.setattr(module,'create_ai_client',lambda _:client)
    monkeypatch.setattr('src.orchestrator.save_run_report',lambda _:None)
    path=tmp_path/'queue.json'
    with pytest.raises(ValueError,match='changed production'):asyncio.run(runner.run_x_slot(now=ON_TIME,state_path=path))
    job=json.loads(path.read_text())['editions'][DAY]['jobs'][0]
    assert job['status']=='planned' and job['attempted_at'] is None and fake.posts==[]


def proof_api(monkeypatch,tmp_path,*,deployment=None,producer=None,bad_hash=False,api_error=False):
    import src.x_verification as module
    state,path,root,public,html=publication(tmp_path)
    rawproof=(root/'production-edition.json').read_bytes();report=(root/'run-report.json').read_bytes()
    if bad_hash:
        data=json.loads(rawproof);data['selection_sha256']='0'*64;rawproof=json.dumps(data).encode()
    calls=[]
    run={'id':456,'head_branch':'main','head_repository':{'full_name':'ohxiyu/xiyunews'},'conclusion':'success'}
    run.update(deployment or {})
    original={'id':123,'head_branch':'main','head_repository':{'full_name':'ohxiyu/xiyunews'},'conclusion':'success','path':'.github/workflows/daily-summary.yml'}
    original.update(producer or {})
    def gh(*args):
        calls.append(args)
        if api_error:raise RuntimeError('GitHub publication evidence unavailable')
        if args[0]=='run':
            target=Path(args[-1]);target.mkdir(parents=True,exist_ok=True)
            if args[2]=='456':(target/'production-edition.json').write_bytes(rawproof)
            else:(target/'run-report.json').write_bytes(report)
            return b''
        route=args[1]
        if 'workflows/' in route:return json.dumps({'workflow_runs':[run]}).encode()
        if route.endswith('/artifacts'):return b'{"artifacts":[{"name":"production-edition","expired":false}]}'
        return json.dumps(original).encode()
    monkeypatch.setenv('GITHUB_REPOSITORY','ohxiyu/xiyunews');monkeypatch.setattr(module,'_gh',gh)
    return module,path,tmp_path/'found',calls


def test_find_proof_binds_exact_original_report_and_selection_without_queue_mutation(tmp_path,monkeypatch):
    module,path,root,calls=proof_api(monkeypatch,tmp_path)
    assert module.find_proof(now=NOW,root=root,state_path=path)
    assert (root/'production-edition.json').exists() and (root/'run-report.json').exists()
    assert not list(tmp_path.rglob('x-queue.json'))
    assert all(args[0] in ('api','run') for args in calls)


@pytest.mark.parametrize('stage,change',[
    ('deployment',{'head_branch':'other'}),('deployment',{'head_repository':{'full_name':'attacker/xiyunews'}}),
    ('producer',{'path':'.github/workflows/feed-collection.yml'}),
    ('producer',{'head_branch':'other'}),('producer',{'head_repository':{'full_name':'attacker/xiyunews'}}),
    ('producer',{'conclusion':'failure'}),
])
def test_find_proof_rejects_wrong_origin_branch_or_producer(tmp_path,monkeypatch,stage,change):
    module,path,root,calls=proof_api(monkeypatch,tmp_path,**{stage:change})
    assert not module.find_proof(now=NOW,root=root,state_path=path)
    assert not (root/'production-edition.json').exists()


def test_find_proof_never_treats_github_error_as_empty_history(tmp_path,monkeypatch):
    module,path,root,_=proof_api(monkeypatch,tmp_path,api_error=True)
    with pytest.raises(RuntimeError):module.find_proof(now=NOW,root=root,state_path=path)


def test_wrong_raw_selection_hash_never_grants_ready(tmp_path,monkeypatch):
    module,path,root,_=proof_api(monkeypatch,tmp_path,bad_hash=True)
    assert not module.find_proof(now=NOW,root=root,state_path=path)


@pytest.mark.parametrize('case',['disabled','missing','empty','over_limit'])
def test_sender_rejects_before_http(monkeypatch,case):
    p=publisher(monkeypatch,lambda _:pytest.fail('must not call HTTP'))
    p.config=p.config.model_copy(update={'enabled':case!='disabled'})
    if case=='missing':monkeypatch.delenv('X_ACCESS_TOKEN')
    text='' if case=='empty' else '汉'*141 if case=='over_limit' else 'valid'
    assert asyncio.run(p.publish_post(text)).kind in ('not_sent','failed')
