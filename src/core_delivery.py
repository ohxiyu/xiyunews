"""Post-publication Telegram delivery with durable, conservative one-shot receipts."""
from __future__ import annotations
import asyncio
import hashlib
import json
import os
from pathlib import Path
from .daily_feed import DailyFeedState
from .models import Config
from .publication_state import active_store
from .services.telegram_delivery import TelegramEditionPublisher, TelegramDeliveryStatus


def delivery_eligible(report: dict, state: DailyFeedState) -> bool:
    codes={row['code'] for row in report.get('alerts',[])}
    return ('telegram_deferred' in codes and 'telegram_rebuild_skipped' not in codes
        and report.get('date')==state.date and report.get('kind')=='daily_publish'
        and not report.get('error') and report.get('metrics',{}).get('displayed_today')==len(state.items)
        and state.updated_at.isoformat()==report.get('started_at'))


def claim(store, edition: str, destination: str) -> bool:
    """Commit before HTTP; unknown outcomes are never automatically retried."""
    key=hashlib.sha256(destination.encode()).hexdigest()
    with store.connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS core_telegram_receipts (edition TEXT NOT NULL, destination TEXT NOT NULL, status TEXT NOT NULL, message_id INTEGER, PRIMARY KEY(edition,destination))')
        result=db.execute("INSERT OR IGNORE INTO core_telegram_receipts VALUES(?,?,'attempted_unknown',NULL)",(edition,key))
        return result.rowcount==1


async def main():
    state=DailyFeedState.model_validate_json(Path('published/_data/bmtnews_state.json').read_text())
    reports=list(Path('source-report').glob('**/run-report.json'))
    if len(reports)!=1:raise ValueError('one exact source run report required')
    report=json.loads(reports[0].read_text())
    if not delivery_eligible(report,state):
        print('No new eligible edition; no delivery.');return
    if os.environ.get('GITHUB_RUN_ATTEMPT')!='1':raise RuntimeError('Delivery reruns require outcome inspection')
    store=active_store()
    if store is None:raise RuntimeError('Durable receipt backend required; no message sent')
    config=Config.model_validate_json(Path('data/config.github.json').read_text())
    delivery=config.telegram_delivery
    if not delivery or not delivery.enabled:raise ValueError('core Telegram disabled')
    token=os.environ.get(delivery.bot_token_env,'');destination=os.environ.get(delivery.channel_id_env,'')
    if not token or not destination:raise RuntimeError('Telegram credentials unavailable')
    if not claim(store,state.date,destination):
        print('Edition already claimed; no retry or duplicate send.');return
    result=await TelegramEditionPublisher(delivery).send_daily_edition(state.items,date=state.date,total_candidates=report['metrics'].get('edition_candidates',len(state.items)),language='zh')
    if result.status!=TelegramDeliveryStatus.SUCCESS or not result.message_id:
        raise RuntimeError('Telegram outcome unconfirmed; receipt retained, inspect before retry')
    with store.connect() as db:
        db.execute("UPDATE core_telegram_receipts SET status='sent',message_id=? WHERE edition=? AND destination=?",(result.message_id,state.date,hashlib.sha256(destination.encode()).hexdigest()))
    print(json.dumps({'edition':state.date,'status':'sent','message_id':result.message_id}))

if __name__=='__main__':asyncio.run(main())
