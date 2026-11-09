"""Rolling qualified news; publish a data snapshot without building or delivering."""
from __future__ import annotations
import asyncio
import hashlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx
from .daily_feed import item_identity
from .edition import load_staging_state, merge_staged_items
from .models import Config
from .orchestrator import BMTNewsOrchestrator
from .storage.manager import StorageManager
from .run_report import RunReport
from .ai.tokens import reset_usage
from .edition_fallback import save_selection,open_window
from .ai.chinese import chinese_ready
from .web_feed import _localized_title, _localized_text


def active_items(items, now):
    start=now-timedelta(hours=24)
    return merge_staged_items([], [i for i in items if start<=i.published_at<now], now=now)


def snapshot(items, *, now, collected_at):
    rows=[]
    for item in sorted(active_items(items,now),key=lambda i:i.published_at,reverse=True):
        rows.append({
            'id':hashlib.sha256(item_identity(item).encode()).hexdigest()[:32],
            'title':_localized_title(item,'zh'),
            'summary':_localized_text(item,'detailed_summary','zh') or item.ai_summary or '',
            'background':_localized_text(item,'background','zh') or '',
            'url':str(item.url),'source':str(item.metadata.get('feed_name') or item.author or item.source_type.value),
            'published_at':item.published_at.isoformat(), 'score':item.ai_score,
            'references':[{'title':str(r.get('title') or r.get('url') or ''),'url':str(r.get('url') or '')} for r in (item.metadata.get('sources') or []) if isinstance(r,dict)][:20],
        })
    return {'version':1,'generated_at':now.isoformat(),'collected_at':collected_at.isoformat(),
            'window_start':(now-timedelta(hours=24)).isoformat(),'items':rows}


async def main():
    config=Config.model_validate_json(Path('data/config.github.json').read_text())
    if not config.rolling_feed:raise ValueError('rolling core profile required')
    runner=BMTNewsOrchestrator(config,StorageManager())
    staged=load_staging_state()
    now=datetime.now(timezone.utc)
    report=RunReport.start(date=now.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat(),timezone_name='Asia/Shanghai',kind='staging_fetch')
    reset_usage();runner.last_run_report=report
    try:
        candidates=active_items(staged.items,now)
        analyzed=await runner._analyze_content(candidates)
        result=await runner.filter_items(analyzed, dedup_context=[])
        save_selection(result.items,config,open_window(now,config.filtering.daily_timezone),now=now)
        await runner._enrich_important_items(result.items)
        result.items[:]=[item for item in result.items if chinese_ready(item) and not item.metadata.get("chinese_invalid")]
        # Recheck the boundary after AI completes. Never retain expired stories.
        value=snapshot(result.items,now=datetime.now(timezone.utc),collected_at=staged.updated_at)
        token_name='XIYUNEWS_RECOVERY_CHECK_TOKEN' if os.environ.get('XIYUNEWS_EDGE_ENABLED')=='true' else 'RECOVERY_CHECK_TOKEN'
        token=os.environ.get(token_name,'')
        if not token:raise ValueError('rolling publisher credential unavailable')
        async with httpx.AsyncClient(timeout=30,follow_redirects=False) as client:
            response=await client.post('https://xiyu.news/api/live.json',json=value,headers={'Authorization':'Bearer '+token})
            if response.status_code!=200:raise RuntimeError(f'rolling publish failed HTTP {response.status_code}')
        report.set_metric('rolling_selected',len(value['items']))
    except Exception as exc:
        report.fail(exc);raise
    finally:runner._finish_run_report(report)

if __name__=='__main__':asyncio.run(main())
