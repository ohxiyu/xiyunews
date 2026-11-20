import base64
import json
import sqlite3
import time

import pytest

from src.edge_state import EdgePublicationState, acquire, commit, migrate
from src.core_delivery import claim
from src.publication_state import PublicationState, StateConflict


class Remote:
    """Transport fake only. Domain SQL, page serialization, claim and restart real."""
    def __init__(self):
        self.meta={"version":0,"size":0,"hashes":[],"ready":False,"until":time.time()*1000+2400000}
        self.pages={}
        self.pending={}
        self.owner=None
        self.fail=None
        self.commits=0

    def call(self, action, body):
        if self.fail == action:
            raise StateConflict("transport unconfirmed")
        owner=body['owner']
        if action=='acquire':
            if self.owner and self.owner!=owner:raise StateConflict('423')
            self.owner=owner
            return self.meta.copy()
        if self.owner!=owner:raise StateConflict('lease_lost')
        if action=='release':self.owner=None;self.pending={};return {}
        if body['version']!=self.meta['version']:raise StateConflict('version_conflict')
        if action=='upload':
            self.pending.update({p['n']:p for p in body['pages']});return {}
        if action=='download':
            return {'pages':[self.pages[n] for n in range(body['start'],min(body['start']+8,len(self.pages)))]}
        assert action=='commit'
        self.pages.update(self.pending);self.pending={}
        self.pages={n:p for n,p in self.pages.items() if n<len(body['hashes'])}
        assert [p['hash'] for _,p in sorted(self.pages.items())]==body['hashes']
        self.meta.update(version=self.meta['version']+1,size=body['size'],hashes=body['hashes'],ready=True)
        self.commits+=1
        if self.fail=='after_commit':raise StateConflict('commit response lost')
        return self.meta.copy()


@pytest.fixture
def migrated(tmp_path,monkeypatch):
    monkeypatch.setenv('GITHUB_RUN_ID','123')
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT','1')
    original=PublicationState(tmp_path/'source')
    original.save_document('daily',{'date':'2026-11-17','items':[{'title':'原稿'}]})
    original.save_document('events',{'old_history':'x'*3_000_000})
    assert claim(original,'2026-11-16','private-destination')
    remote=Remote()
    root=tmp_path/'migration';root.mkdir()
    migrate(root,remote,original.path)
    remote.call('release',{'owner':remote.owner})
    return remote,original


def restore(tmp_path,remote,name='restored'):
    root=tmp_path/name;root.mkdir()
    acquire(root,remote,wait=0)
    return EdgePublicationState(root,remote)


def test_full_state_survives_hosted_restart_and_claim_precedes_delivery(tmp_path,migrated):
    remote,original=migrated
    state=restore(tmp_path,remote)
    assert state.load_document('events',None)==original.load_document('events',None)
    assert state.saved_editions()==original.saved_editions()
    assert not claim(state,'2026-11-16','private-destination')
    assert claim(state,'2026-11-17','private-destination')
    remote.call('release',{'owner':remote.owner})
    restarted=restore(tmp_path,remote,'next-job')
    assert not claim(restarted,'2026-11-17','private-destination')
    assert restarted.verify()['verified']
    with restarted.connect() as db:
        assert db.execute('SELECT status FROM core_telegram_receipts ORDER BY edition').fetchall()==[('attempted_unknown',),('attempted_unknown',)]


@pytest.mark.parametrize('failure',['upload','commit'])
def test_remote_failure_rolls_back_and_never_authorizes_send(tmp_path,migrated,failure):
    remote,_=migrated
    state=restore(tmp_path,remote)
    remote.fail=failure
    with pytest.raises(StateConflict):
        claim(state,'2026-11-17','another-destination')
    with sqlite3.connect(state.path) as db:
        assert db.execute('SELECT COUNT(*) FROM core_telegram_receipts').fetchone()[0]==1


def test_stale_owner_or_revision_cannot_write_or_claim(tmp_path,migrated):
    remote,_=migrated
    state=restore(tmp_path,remote)
    with pytest.raises(StateConflict,match='423'):
        acquire(tmp_path/'not-created',remote,wait=0)
    remote.owner='new-owner'
    with pytest.raises(StateConflict,match='lease_lost'):
        claim(state,'2026-11-17','private-destination')


def test_read_only_transactions_do_not_upload_and_migration_never_overwrites(tmp_path,migrated):
    remote,original=migrated
    state=restore(tmp_path,remote)
    before=remote.commits
    for _ in range(3):state.verify();state.saved_editions()
    assert remote.commits==before
    remote.call('release',{'owner':remote.owner})
    root=tmp_path/'second-migration';root.mkdir()
    with pytest.raises(StateConflict,match='already initialized'):
        migrate(root,remote,original.path)
    assert remote.commits==before


def test_missing_or_corrupt_state_fails_closed(tmp_path,migrated):
    remote,_=migrated
    first=remote.pages[0]
    first['data']=base64.b64encode(b'corrupt').decode()
    root=tmp_path/'corrupted';root.mkdir()
    with pytest.raises(StateConflict,match='checksum'):
        acquire(root,remote,wait=0)
    assert not (root/'publication.sqlite3').exists()


def test_unknown_commit_is_durable_and_next_job_does_not_resend(tmp_path,migrated):
    remote,_=migrated
    state=restore(tmp_path,remote)
    remote.fail='after_commit'
    with pytest.raises(StateConflict,match='response lost'):
        claim(state,'2026-11-17','private-destination')
    remote.fail=None
    remote.call('release',{'owner':remote.owner})
    next_job=restore(tmp_path,remote,'after-unknown')
    assert not claim(next_job,'2026-11-17','private-destination')


def test_version_conflict_cannot_commit_a_stale_local_transaction(tmp_path,migrated):
    remote,_=migrated
    state=restore(tmp_path,remote)
    remote.meta['version']+=1
    with pytest.raises(StateConflict,match='version_conflict'):
        claim(state,'2026-11-17','private-destination')


def test_transport_identifies_itself_without_weakening_authentication(monkeypatch):
    import io
    from src import edge_state
    seen=[]
    class Response(io.BytesIO):
        headers={}
    def http(request,timeout):
        seen.append(request)
        return Response(b'{"ready":true}')
    transport=edge_state.Transport()
    monkeypatch.setattr(transport,'identity',lambda:'short-lived-test-identity')
    monkeypatch.setattr(edge_state,'urlopen',http)
    assert transport.call('acquire',{'owner':'private-owner'})=={'ready':True}
    assert seen[0].get_header('User-agent')=='xiyunews-publication-state/1.0'
    assert seen[0].get_header('Authorization')=='Bearer short-lived-test-identity'
    assert seen[0].method=='POST'


def test_workflows_fence_remote_state_and_retire_backup():
    from pathlib import Path
    root=Path(__file__).parents[1]
    for name in ['feed-collection','daily-summary','daily-telegram','x-distribution','cloudflare-unified']:
        text=(root/'.github/workflows'/f'{name}.yml').read_text()
        assert "XIYUNEWS_STATE_BACKEND: ${{ vars.XIYUNEWS_RUNTIME_MODE == 'hosted' && 'cloudflare' || '' }}" in text
        assert "vars.XIYUNEWS_RUNTIME_MODE != 'maintenance'" in text
        assert "vars.XIYUNEWS_RUNTIME_MODE == 'hosted' && 'ubuntu-latest'" in text
        assert 'id-token: write' in text
        assert text.count('src.edge_state acquire')==1
        assert text.count('src.edge_state release')==1
        assert "if: always() && steps.state.outcome == 'success'" in text
    assert not (root/'.github/workflows/server-backup.yml').exists()
