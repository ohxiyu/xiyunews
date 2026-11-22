"""Read-only account diagnostics and trusted publication evidence for X."""
from __future__ import annotations
import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime,timezone
from bs4 import BeautifulSoup
import httpx
from .deployment_proof import valid_proof
from .models import Config
from .archive import build_records
from .api_output import build_edition_payload
from .core_site import render_core_feed
from .services.x_delivery import XEditionPublisher

PROOF_ROOT=Path('verified-publication')
STATE_PATH=Path('docs/_data/bmtnews_state.json')


def _gh(*args):
    result=subprocess.run(['gh',*args],capture_output=True,check=False)
    if result.returncode:raise RuntimeError('GitHub publication evidence unavailable')
    return result.stdout


def find_proof(*,now=None,root=PROOF_ROOT,state_path=STATE_PATH):
    """Read artifacts only from successful main/origin deployment runs."""
    now=now or datetime.now(timezone.utc)
    repo=os.environ.get('GITHUB_REPOSITORY','')
    if repo!='ohxiyu/xiyunews':raise ValueError('unexpected publication repository')
    raw=state_path.read_bytes();state=json.loads(raw)
    runs=json.loads(_gh('api',f'repos/{repo}/actions/workflows/cloudflare-unified.yml/runs?status=success&branch=main&per_page=20'))
    for run in runs.get('workflow_runs',[]):
        if run.get('head_branch')!='main' or run.get('head_repository',{}).get('full_name')!=repo or run.get('conclusion')!='success':continue
        run_id=run.get('id')
        if type(run_id) is not int or run_id<=0:continue
        artifacts=json.loads(_gh('api',f'repos/{repo}/actions/runs/{run_id}/artifacts'))
        if not any(a.get('name')=='production-edition' and not a.get('expired') for a in artifacts.get('artifacts',[])):continue
        target=root/str(run_id);target.mkdir(parents=True,exist_ok=True)
        _gh('run','download',str(run_id),'--repo',repo,'--name','production-edition','--dir',str(target))
        path=target/'production-edition.json';proof=json.loads(path.read_text())
        source=str(proof.get('source_run_id') or '')
        if not source.isdecimal() or proof.get('edition_date')!=state.get('date') or proof.get('selection_sha256')!=hashlib.sha256(raw).hexdigest():continue
        producer=json.loads(_gh('api',f'repos/{repo}/actions/runs/{source}'))
        if producer.get('path')!='.github/workflows/daily-summary.yml' or producer.get('head_branch')!='main' or producer.get('head_repository',{}).get('full_name')!=repo or producer.get('conclusion')!='success':continue
        reports=target/'source-report'
        _gh('run','download',source,'--repo',repo,'--pattern','run-report-*','--dir',str(reports))
        files=list(reports.glob('**/run-report.json'))
        if len(files)!=1:raise ValueError('ambiguous original daily report')
        if valid_proof(proof,files[0].read_bytes(),raw,now=now):
            (root/'production-edition.json').write_bytes(path.read_bytes())
            (root/'run-report.json').write_bytes(files[0].read_bytes())
            return True
    return False


def _words(value):return ' '.join(value.split())


def _article_fields(article):
    heading=article.find('h2')
    bg=article.select_one('.story-background')
    background=''
    if bg:
        for label in bg.find_all('span',recursive=False):label.decompose()
        background=_words(bg.get_text(' ',strip=True))
        bg.decompose()
    body=article.select_one('.story-body')
    if body is None:raise ValueError('published story body missing')
    for extra in body.select('.source-line,.references,.story-actions,.thread-pill'):extra.decompose()
    return (_words(heading.get_text(' ',strip=True)) if heading else '',background,_words(body.get_text(' ',strip=True)))


async def verify_published_edition(state,*,now=None,root=PROOF_ROOT,state_path=STATE_PATH,client=None):
    """Prove actual page words, including background, before returning publication time."""
    now=now or datetime.now(timezone.utc)
    raw=state_path.read_bytes()
    # Bind the in-memory selection to the exact checked-out private snapshot.
    from .daily_feed import DailyFeedState
    if DailyFeedState.model_validate_json(raw)!=state:raise ValueError('selection changed before X verification')
    proof=json.loads((root/'production-edition.json').read_text())
    if not valid_proof(proof,(root/'run-report.json').read_bytes(),raw,now=now):raise ValueError('current verified publication proof required')
    if client is None:
        async with httpx.AsyncClient(timeout=15,follow_redirects=False) as owned:
            return await verify_published_edition(state,now=now,root=root,state_path=state_path,client=owned)
    pages={}
    for path in ('/api/latest.json','/','/'+state.date.replace('-','/')+'/summary-zh'):
        response=await client.get('https://xiyu.news'+path,headers={'Cache-Control':'no-cache'})
        if response.status_code!=200 or len(response.content)>1_048_576:raise RuntimeError('published edition read unavailable')
        pages[path]=response.text
    public=json.loads(pages['/api/latest.json'])
    records=build_records(state.items,date=state.date,top_category_of=lambda _: '')
    expected=build_edition_payload(records,date=state.date,stats={})
    if public.get('date')!=state.date or public.get('content_revision_version')!=1 or len(public.get('items',[]))!=len(state.items):raise ValueError('published edition mismatch')
    for actual,wanted in zip(public['items'],expected['items']):
        for field in ('url','score','content_revision'):
            if actual.get(field)!=wanted[field]:raise ValueError('published story mismatch')
        for field in ('title','summary'):
            if actual.get(field,{}).get('zh')!=wanted[field]['zh']:raise ValueError('published story words mismatch')
    rendered=BeautifulSoup(render_core_feed(state.items,date=state.date),'html.parser')
    expected_fields=[_article_fields(a) for a in rendered.select('article.digest-item')]
    revisions=[row['content_revision']['zh'] for row in expected['items']]
    for path,html in pages.items():
        if path=='/api/latest.json':continue
        soup=BeautifulSoup(html,'html.parser')
        section=soup.select_one('section.daily-day')
        if section is None or section.get('data-date')!=state.date:raise ValueError('published page date mismatch')
        if path=='/' and not soup.select_one(f'[data-latest-edition-date="{state.date}"]'):raise ValueError('homepage edition mismatch')
        articles=section.select('article.digest-item')
        if [a.get('data-content-revision') for a in articles]!=revisions or [_article_fields(a) for a in articles]!=expected_fields:raise ValueError('published page words or background mismatch')
    return datetime.fromisoformat(proof['verified_at'].replace('Z','+00:00'))


async def account_diagnostics(output):
    config=Config.model_validate_json(Path('data/config.github.json').read_text())
    result={'checked_at':datetime.now(timezone.utc).isoformat(),'x':await XEditionPublisher(config.x_delivery).verify_account()}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
    return result['x'].get('status')=='verified'


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--account-only',action='store_true')
    parser.add_argument('--output',type=Path,default=Path('data/x-verification.json'))
    args=parser.parse_args()
    if args.account_only:return 0 if asyncio.run(account_diagnostics(args.output)) else 1
    ready=find_proof()
    value='ready='+str(ready).lower()
    output=os.environ.get('GITHUB_OUTPUT')
    if output:
        with open(output,'a') as file:file.write(value+'\n')
    print(value)
    return 0


if __name__=='__main__':raise SystemExit(main())
