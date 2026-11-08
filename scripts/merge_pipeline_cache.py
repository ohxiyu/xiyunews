"""Merge concurrent data-only cache snapshots; never change published documents."""
from __future__ import annotations
import json
import subprocess
import sys
from datetime import datetime,timedelta,timezone
from pathlib import Path


def merge(local,remote,kind,now=None):
    if not remote:return local
    # Legacy/unknown formats retain existing behavior. Production version 1
    # records are merged by identity and stored_at, never by a run's age.
    if local.get('version')!=1 or remote.get('version')!=1:return local
    now=now or datetime.now(timezone.utc)
    if kind=='staging-items':
        rows={}
        for row in remote.get('items',[])+local.get('items',[]):
            stamp=datetime.fromisoformat(row['published_at'].replace('Z','+00:00'))
            if stamp<now-timedelta(hours=72):continue
            key=row['url'];previous=rows.get(key)
            if previous is None or (row.get('fetched_at',''),len(row.get('content') or ''))>(previous.get('fetched_at',''),len(previous.get('content') or '')):rows[key]=row
        return {**local,'updated_at':max(local['updated_at'],remote['updated_at']),'items':sorted(rows.values(),key=lambda r:r['published_at'],reverse=True)}
    value={'version':1}
    for key,cap,days in [('entries',4000,30),('prefilter_batches',256,1),('relation_pairs',2000,7)]:
        rows={}
        for source in [remote,local]:
            for identity,row in source.get(key,{}).items():
                stamp=datetime.fromisoformat(row['stored_at'].replace('Z','+00:00'))
                if stamp<now-timedelta(days=days):continue
                if identity not in rows or row['stored_at']>rows[identity]['stored_at']:rows[identity]=row
        value[key]=dict(sorted(rows.items(),key=lambda pair:pair[1]['stored_at'],reverse=True)[:cap])
    return value


def main():
    base=sys.argv[1]
    for name in ['staging-items','analysis-cache']:
        path=Path('data')/(name+'.json')
        if not path.exists():continue
        result=subprocess.run(['git','show',base+':'+path.as_posix()],capture_output=True,text=True)
        if result.returncode:continue
        local=json.loads(path.read_text());remote=json.loads(result.stdout)
        value=merge(local,remote,name)
        # Leave unchanged files byte-for-byte identical for idempotent commits.
        if value!=local:path.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True)+'\n')

if __name__=='__main__':main()
