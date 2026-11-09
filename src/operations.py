"""Operational topic receipts and estimated AI costs; never reader delivery."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx

from ._file_utils import _atomic_write_text
from .publication_state import active_store

PRICE_SOURCE = 'https://docs.siliconflow.cn/docs/release-notes/overview'


def estimate_cost(rows):
    """CNY estimate at 2026-06-25 prices; reasoning is included in output."""
    total = Decimal(0)
    unpriced = 0
    for row in rows:
        if row.get('provider') != 'siliconflow' or row.get('model') != 'deepseek-ai/DeepSeek-V3.2':
            if row.get('calls') or row.get('input_tokens') or row.get('output_tokens'):
                unpriced += 1
            continue
        values = [row.get(k, 0) for k in ('input_tokens', 'output_tokens', 'cached_input_tokens')]
        if any(type(v) is not int or v < 0 for v in values):
            unpriced += 1
            continue
        incoming, outgoing, cached = values
        if cached > incoming:
            unpriced += 1
            continue
        total += (Decimal(incoming-cached)*4 + Decimal(cached)*Decimal('.4') + Decimal(outgoing)*6) / 1000000
    return {'currency': 'CNY', 'estimated': True, 'amount': float(total),
            'complete': unpriced == 0, 'unpriced_rows': unpriced, 'price_source': PRICE_SOURCE}


def prepare(store):
    with store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS operations_costs (run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, day TEXT NOT NULL, amount REAL NOT NULL, complete INTEGER NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS private_alerts (id TEXT PRIMARY KEY, status TEXT NOT NULL)')


def record_cost(report, store=None):
    cost = estimate_cost(report.get('ai_usage') or [])
    store = store or active_store()
    if store is not None:
        prepare(store)
        moment = datetime.fromisoformat(report['started_at'])
        if moment.tzinfo is None:
            raise ValueError('cost timestamp requires timezone')
        started = moment.astimezone(timezone.utc).isoformat()
        day = moment.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
        with store.connect() as db:
            db.execute('INSERT INTO operations_costs VALUES(?,?,?,?,?) ON CONFLICT(run_id) DO UPDATE SET amount=excluded.amount,complete=excluded.complete',
                       (report['run_id'], started, day, cost['amount'], int(cost['complete'])))
    return cost


def cost_totals(store, *, now=None):
    """Recorded project usage only; no provider balance checks or forecasts."""
    if store is None:
        return {'status': 'state_unavailable'}
    now = now or datetime.now(timezone.utc)
    prepare(store)
    day = now.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
    with store.connect() as db:
        rows = db.execute('SELECT started_at,day,amount,complete FROM operations_costs').fetchall()
    return {'status': 'recorded_usage',
            'today_cny': round(sum(r[2] for r in rows if r[1] == day), 6),
            'month_cny': round(sum(r[2] for r in rows if r[1][:7] == day[:7]), 6),
            'recorded_since': min((r[0] for r in rows), default=None),
            'complete_pricing': all(r[3] for r in rows),
            'note': '仅为本项目已记录用量的费用估算，不是供应商账单或余额。'}


async def send_alert(key, text, *, store=None, client=None, env=None):
    """Persist unknown BEFORE send. Require the configured forum topic; no fallback."""
    env = os.environ if env is None else env
    token, chat = env.get('TELEGRAM_BOT_TOKEN',''), env.get('TELEGRAM_ALERT_CHAT_ID','')
    thread = env.get('TELEGRAM_ALERT_THREAD_ID','')
    if not token or not re.fullmatch(r'-[1-9][0-9]*', chat) or not re.fullmatch(r'[1-9][0-9]*', thread):
        return 'not_configured'
    store = store or active_store()
    if store is None:
        return 'state_unavailable'
    prepare(store)
    if client is None:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as owned:
            return await send_alert(key,text,store=store,client=owned,env=env)
    # Verify destination before claiming/sending; errors must not reveal bot URLs.
    try:
        response = await client.post(f'https://api.telegram.org/bot{token}/getChat', json={'chat_id':chat})
        payload = response.json()
        if response.status_code != 200 or payload.get('ok') is not True or payload.get('result',{}).get('type') != 'supergroup' or payload.get('result',{}).get('is_forum') is not True or str(payload['result'].get('id')) != chat:
            return 'destination_unverified'
    except Exception:
        return 'destination_unverified'
    with store.connect() as db:
        changed = db.execute('INSERT OR IGNORE INTO private_alerts VALUES(?,?)',(key,'unknown')).rowcount
        if not changed:
            return 'already_attempted'
    status = 'unknown'
    try:
        response = await client.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'message_thread_id':int(thread),'text':text[:4000], 'link_preview_options':{'is_disabled':True}})
        payload = response.json()
        if response.status_code==200 and payload.get('ok') is True and payload.get('result',{}).get('message_id'):
            status = 'sent'
        elif 400 <= response.status_code < 500 and payload.get('ok') is False:
            status = 'failed'
    except Exception:
        pass
    with store.connect() as db:
        db.execute('UPDATE private_alerts SET status=? WHERE id=?',(status,key))
    return status


async def setup_alert_topic(chat, *, store=None, client=None, env=None):
    """Create one explicitly requested forum topic, with a durable attempt receipt."""
    env = os.environ if env is None else env
    token = env.get('TELEGRAM_BOT_TOKEN', '')
    if not token or not re.fullmatch(r'(?:-[1-9][0-9]*|@[a-zA-Z][a-zA-Z0-9_]{4,31})', chat):
        return {'status': 'invalid_or_missing_configuration'}
    store = store or active_store()
    if store is None:
        return {'status': 'state_unavailable'}
    prepare(store)
    if client is None:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as owned:
            return await setup_alert_topic(chat,store=store,client=owned,env=env)
    try:
        response = await client.post(f'https://api.telegram.org/bot{token}/getChat',json={'chat_id':chat})
        data=response.json();group=data.get('result',{})
        if response.status_code!=200 or data.get('ok') is not True or group.get('type')!='supergroup' or group.get('is_forum') is not True:
            return {'status':'forum_unverified'}
        chat_id=str(group['id'])
        if chat.startswith('-') and chat_id!=chat:
            return {'status':'forum_unverified'}
        if chat.startswith('@') and str(group.get('username','')).lower()!=chat[1:].lower():
            return {'status':'forum_unverified'}
        if not re.fullmatch(r'-[1-9][0-9]*',chat_id):
            return {'status':'forum_unverified'}
    except Exception:
        return {'status':'forum_unverified'}
    key='topic-setup:'+chat_id
    with store.connect() as db:
        previous=db.execute('SELECT status FROM private_alerts WHERE id=?',(key,)).fetchone()
        if previous:
            try:
                outcome=json.loads(previous[0])
            except ValueError:
                return {'status':'already_attempted'}
            if outcome.get('status') != 'rejected_check_bot_topic_permissions':
                return outcome
            # Only a new explicit setup dispatch can retry a proven rejection;
            # ambiguous creations remain unknown and are never repeated.
        db.execute('INSERT OR REPLACE INTO private_alerts VALUES(?,?)',(key,json.dumps({'status':'unknown'})))
    result={'status':'unknown'}
    try:
        response=await client.post(f'https://api.telegram.org/bot{token}/createForumTopic',json={'chat_id':chat_id,'name':'日报运维'})
        data=response.json();thread=data.get('result',{}).get('message_thread_id')
        if response.status_code==200 and data.get('ok') is True and type(thread) is int and thread>0:
            result={'status':'created','chat_id':chat_id,'message_thread_id':thread,'name':'日报运维'}
        elif 400<=response.status_code<500 and data.get('ok') is False:
            result={'status':'rejected_check_bot_topic_permissions'}
    except Exception:
        pass
    with store.connect() as db:
        db.execute('UPDATE private_alerts SET status=? WHERE id=?',(json.dumps(result),key))
    return result


async def finalize(path, workflow_status, *, test=False):
    store = active_store()
    if test:
        key = 'test:'+os.environ.get('GITHUB_RUN_ID','local')+':'+os.environ.get('GITHUB_RUN_ATTEMPT','1')
        status = await send_alert(key,'xiyu.news 日报运维测试：仅发送到指定群组话题，不影响其他实时消息。',store=store)
        print('alert_topic_test='+status)
        return 0 if status=='sent' else 1
    if not path.exists():
        if workflow_status=='failure':
            await send_alert('initialization:'+os.environ.get('GITHUB_RUN_ID','local'),'xiyu.news 任务初始化失败，未生成运行报告。',store=store)
        return 0
    report = json.loads(path.read_text())
    report['ai_cost'] = record_cost(report,store)
    report['operations'] = {'workflow_status':workflow_status, 'cost_totals':cost_totals(store), 'alerts':[]}
    run_id=report['run_id'];metrics=report.get('metrics',{})
    if workflow_status=='failure' or report.get('status')=='failure':
        status=await send_alert('failure:'+run_id,f"xiyu.news {report.get('date')} 任务失败，请检查 Actions 运行日志。",store=store)
        report['operations']['alerts'].append({'event':'failure','status':status})
    elif metrics.get('edition_degraded') or metrics.get('enrichment_degraded'):
        status=await send_alert('degraded:'+run_id,f"xiyu.news {report.get('date')} 已生成简版，部分背景不可用。" + (f" AI账户HTTP {metrics['provider_account_http_status']}，已停止调用。" if metrics.get('provider_account_http_status') else ''),store=store)
        report['operations']['alerts'].append({'event':'degraded','status':status})
    totals=report['operations']['cost_totals']
    if report.get('kind')=='daily_publish' and workflow_status=='success' and metrics.get('displayed_today'):
        status=await send_alert('daily:'+report['date'],f"xiyu.news {report['date']}：{metrics['displayed_today']}条；今日AI估算¥{totals.get('today_cny',report['ai_cost']['amount']):.4f}，本月已记录¥{totals.get('month_cny',0):.4f}；X正式发布关闭。",store=store)
        report['operations']['alerts'].append({'event':'daily','status':status})
    _atomic_write_text(path,json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    if store:
        store.save_report(report)
    return 0


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--report',type=Path,default=Path('data/run-report.json'))
    parser.add_argument('--workflow-status',choices=['success','failure','cancelled'],default='success')
    parser.add_argument('--test-alert',action='store_true')
    parser.add_argument('--setup-alert-topic')
    args=parser.parse_args()
    if args.setup_alert_topic:
        result=asyncio.run(setup_alert_topic(args.setup_alert_topic))
        Path('data').mkdir(exist_ok=True)
        _atomic_write_text(Path('data/alert-setup.json'),json.dumps(result,ensure_ascii=False)+'\n')
        print('alert_topic_setup='+result['status'])
        return 0 if result['status']=='created' else 1
    return asyncio.run(finalize(args.report,args.workflow_status,test=args.test_alert))


if __name__=='__main__':
    raise SystemExit(main())
