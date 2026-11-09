"""Private operational receipts and estimated AI costs; never reader delivery."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
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


def budget(store, *, now=None, env=None):
    now = now or datetime.now(timezone.utc)
    env = os.environ if env is None else env
    result = {'balance_status': 'unknown', 'coverage_days': 0, 'remaining_days': None,
              'note': '估算仅含本项目已记录用量；不含其他应用消费、充值或供应商账单调整。'}
    if store is None:
        return result
    prepare(store)
    day = now.astimezone(ZoneInfo('Asia/Shanghai')).date()
    start = (day-timedelta(days=7)).isoformat()
    with store.connect() as db:
        rows = db.execute('SELECT started_at,day,amount,complete FROM operations_costs').fetchall()
    recent = [r for r in rows if start <= r[1] < day.isoformat()]
    days = {r[1] for r in recent}
    result.update(coverage_days=len(days), today_cny=round(sum(r[2] for r in rows if r[1]==day.isoformat()), 6),
                  month_cny=round(sum(r[2] for r in rows if r[1][:7]==day.isoformat()[:7]), 6))
    try:
        baseline = Decimal(env.get('AI_BALANCE_BASELINE_CNY', ''))
        observed = datetime.fromisoformat(env.get('AI_BALANCE_BASELINE_AT', '').replace('Z','+00:00'))
        if not baseline.is_finite() or baseline < 0 or observed.tzinfo is None or observed > now:
            return result
    except (ValueError, InvalidOperation):
        return result
    # No interpolation through a run spanning the baseline observation.
    since = [r for r in rows if datetime.fromisoformat(r[0]) >= observed]
    remaining = float(baseline) - sum(r[2] for r in since)
    result.update(balance_status='project_estimate', remaining_cny=round(remaining,6))
    if len(days)==7 and all(r[3] for r in recent+since):
        average = sum(r[2] for r in recent)/7
        if average > 0:
            result['remaining_days'] = max(0, remaining)/average
    return result


async def private_alert(key, text, *, store=None, client=None, env=None):
    """Persist unknown BEFORE send. No retry, no reader/group fallback."""
    env = os.environ if env is None else env
    token, chat = env.get('TELEGRAM_BOT_TOKEN',''), env.get('TELEGRAM_ALERT_CHAT_ID','')
    if not token or not re.fullmatch(r'[1-9][0-9]*', chat):
        return 'not_configured'
    store = store or active_store()
    if store is None:
        return 'state_unavailable'
    prepare(store)
    if client is None:
        async with httpx.AsyncClient(timeout=20, follow_redirects=False) as owned:
            return await private_alert(key,text,store=store,client=owned,env=env)
    # Verify destination before claiming/sending; errors must not reveal bot URLs.
    try:
        response = await client.post(f'https://api.telegram.org/bot{token}/getChat', json={'chat_id':chat})
        payload = response.json()
        if response.status_code != 200 or payload.get('ok') is not True or payload.get('result',{}).get('type') != 'private' or str(payload['result'].get('id')) != chat:
            return 'destination_unverified'
    except Exception:
        return 'destination_unverified'
    with store.connect() as db:
        changed = db.execute('INSERT OR IGNORE INTO private_alerts VALUES(?,?)',(key,'unknown')).rowcount
        if not changed:
            return 'already_attempted'
    status = 'unknown'
    try:
        response = await client.post(f'https://api.telegram.org/bot{token}/sendMessage',json={'chat_id':chat,'text':text[:4000], 'link_preview_options':{'is_disabled':True}})
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


async def finalize(path, workflow_status, *, test=False):
    store = active_store()
    if test:
        key = 'test:'+os.environ.get('GITHUB_RUN_ID','local')+':'+os.environ.get('GITHUB_RUN_ATTEMPT','1')
        status = await private_alert(key,'xiyu.news 私人告警测试：仅发送到已验证的私人聊天。',store=store)
        print('private_alert_test='+status)
        return 0 if status=='sent' else 1
    if not path.exists():
        if workflow_status=='failure':
            await private_alert('initialization:'+os.environ.get('GITHUB_RUN_ID','local'),'xiyu.news 任务初始化失败，未生成运行报告。',store=store)
        return 0
    report = json.loads(path.read_text())
    report['ai_cost'] = record_cost(report,store)
    report['operations'] = {'workflow_status':workflow_status, 'budget':budget(store), 'alerts':[]}
    run_id=report['run_id'];metrics=report.get('metrics',{})
    if workflow_status=='failure' or report.get('status')=='failure':
        status=await private_alert('failure:'+run_id,f"xiyu.news {report.get('date')} 任务失败，请检查 Actions 运行日志。",store=store)
        report['operations']['alerts'].append({'event':'failure','status':status})
    elif metrics.get('edition_degraded') or metrics.get('enrichment_degraded'):
        status=await private_alert('degraded:'+run_id,f"xiyu.news {report.get('date')} 已生成简版，部分背景不可用。",store=store)
        report['operations']['alerts'].append({'event':'degraded','status':status})
    balance=report['operations']['budget']
    if balance.get('remaining_days') is not None and balance['remaining_days']<3:
        day=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
        status=await private_alert('balance:'+day,'xiyu.news AI余额估算低于3天本项目用量，请核对供应商余额。',store=store)
        report['operations']['alerts'].append({'event':'balance_low','status':status})
    if report.get('kind')=='daily_publish' and workflow_status=='success' and metrics.get('displayed_today'):
        status=await private_alert('daily:'+report['date'],f"xiyu.news {report['date']}：{metrics['displayed_today']}条；今日AI估算¥{balance.get('today_cny',report['ai_cost']['amount']):.4f}，本月已记录¥{balance.get('month_cny',0):.4f}；X正式发布关闭。",store=store)
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
    args=parser.parse_args()
    return asyncio.run(finalize(args.report,args.workflow_status,test=args.test_alert))


if __name__=='__main__':
    raise SystemExit(main())
