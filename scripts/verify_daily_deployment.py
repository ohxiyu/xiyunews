"""Read public production and prove the exact saved edition before distribution."""
from __future__ import annotations
import argparse,hashlib,json,os,re,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.request import Request,urlopen,HTTPRedirectHandler,build_opener
from urllib.parse import urlsplit

class SameOrigin(HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,message,headers,newurl):
        target=urlsplit(newurl)
        if target.scheme!='https' or target.hostname!='xiyu.news':raise ValueError('unexpected production redirect')
        return super().redirect_request(request,fp,code,message,headers,newurl)


def digest(value):return hashlib.sha256(value).hexdigest()


def matches(health,public,expected,*,build_key,artifact,home,edition_html):
    if health.get('status')!='ok' or health.get('service')!='xiyunews':return False
    if health.get('site_build_key')!=build_key or health.get('site_artifact_commit')!=artifact:return False
    if public!=expected:return False
    day=expected.get('date');items=expected.get('items')
    if not isinstance(day,str) or not isinstance(items,list) or not items:return False
    first=home.split('<section class="daily-day"',1)
    if len(first)!=2:return False
    first=first[1].split('<section class="daily-day"',1)[0]
    if f'data-latest-edition-date="{day}"' not in home or f'data-date="{day}"' not in first:return False
    revisions=[r.get('content_revision',{}).get('zh') for r in items]
    for html in (first,edition_html):
        if len(re.findall(r'<article class="digest-item(?:\s|\")',html))!=len(items):return False
        if expected.get('content_revision_version')==1 and re.findall(r'data-content-revision="([a-f0-9]{64})"',html)!=revisions:return False
    return bool(re.fullmatch('[a-f0-9]{40}',health.get('site_source_commit','')) and health.get('version_id'))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--artifact',required=True);parser.add_argument('--build-key',required=True)
    parser.add_argument('--snapshot',type=Path,default=Path('.edge-source'))
    parser.add_argument('--source-report',type=Path)
    parser.add_argument('--daily-run-id',default='')
    parser.add_argument('--output',type=Path,default=Path('production-edition.json'))
    args=parser.parse_args()
    expected=json.loads((args.snapshot/'api/latest.json').read_text())
    state_bytes=(args.snapshot/'_data/bmtnews_state.json').read_bytes()
    state=json.loads(state_bytes)
    report_bytes=args.source_report.read_bytes() if args.source_report else None
    if args.daily_run_id:
        if not args.daily_run_id.isdecimal() or not report_bytes:raise ValueError('one exact daily producer report required')
        report=json.loads(report_bytes)
        normalize=lambda s:datetime.fromisoformat(s.replace('Z','+00:00'))
        if report.get('kind')!='daily_publish' or report.get('date')!=state.get('date') or state.get('date')!=expected.get('date') or normalize(report['started_at'])!=normalize(state['updated_at']):
            raise ValueError('daily report and saved selection do not match')
    day=expected['date'];path='/'+day.replace('-','/')+'/summary-zh.html'
    reader=build_opener(SameOrigin())
    def read(path):
        request=Request('https://xiyu.news'+path,headers={'Cache-Control':'no-cache','User-Agent':'xiyunews-production-verification/1.0'})
        with reader.open(request,timeout=12) as response:return response.read(4_000_001).decode('utf8')
    for attempt in range(12):
        try:
            health=json.loads(read('/health'));public=json.loads(read('/api/latest.json'))
            if matches(health,public,expected,build_key=args.build_key,artifact=args.artifact,home=read('/'),edition_html=read(path)):break
        except (OSError,ValueError,KeyError):pass
        if attempt==11:raise RuntimeError('production did not verify; distribution remains blocked')
        time.sleep(10)
    proof={'version':1,'verified':True,'edition_date':day,'source_run_id':args.daily_run_id or None,
        'selection_sha256':digest(state_bytes),'source_report_sha256':digest(report_bytes) if report_bytes else None,
        'source_commit':health['site_source_commit'],'artifact_commit':args.artifact,'worker_version':health['version_id'],
        'build_key':args.build_key,'verified_at':datetime.now(timezone.utc).isoformat()}
    args.output.write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
    print('Production edition verified; source_report='+('matched' if report_bytes else 'not a daily publication'))


if __name__=='__main__':main()
