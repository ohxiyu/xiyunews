import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import textwrap

import pytest

from src import x_queue
from src.publication_state import PublicationState, StateConflict, canonical, signature


def snapshots():
    pending = x_queue._blank_job('zh', 1, 'stable-story')
    pending.update(status='pending', text='A recorded story',
                   text_sha256=hashlib.sha256(b'A recorded story').hexdigest(),
                   attempted_at='2026-10-27T00:00:00+00:00')
    remote = {'version': 2, 'editions': {'2026-10-27': {
        'status': 'active', 'published_at': None, 'planned_at': None, 'jobs': [pending]}}}
    local = copy.deepcopy(remote)
    local['editions']['2026-10-27']['jobs'][0].update(
        status='sent', tweet_id='123456789', detail='X API returned HTTP 201.')
    return remote, local


@pytest.mark.parametrize('payload,api_exit,success', [
    ('{"date":"2026-11-05","items":[]}', '0', True),
    ('not JSON', '0', False), ('[]', '0', False),
    ('{"message":"Not found"}', '0', False),
    ('{"date":"2026-11-05","items":[]}', '1', False),
])
@pytest.mark.parametrize('workflow_name,step_name,resource,destination,edition_date', [
    ('x-distribution.yml', 'Restore published edition state', '_data/bmtnews_state.json', 'docs/_data/bmtnews_state.json', ''),
    ('square-distribution.yml', 'Read edition only on publication, revision or bootstrap', 'api/latest.json', 'square-edition.json', ''),
    ('square-distribution.yml', 'Read edition only on publication, revision or bootstrap', 'editions/2026-11-05/edition.json', 'square-edition.json', '2026-11-05'),
])
def test_actual_workflow_restores_only_valid_authenticated_edition(tmp_path, payload, api_exit, success, workflow_name, step_name, resource, destination, edition_date):
    workflow = (Path(__file__).resolve().parents[1] / '.github/workflows' / workflow_name).read_text()
    step = workflow.split('      - name: ' + step_name + '\n', 1)[1].split('      - ', 1)[0]
    script = textwrap.dedent(step.split('        run: |\n', 1)[1])
    binary = tmp_path / 'bin'; binary.mkdir()
    gh = binary / 'gh'
    gh.write_text('#!/bin/sh\n[ "$1" = api ] && [ "$GH_TOKEN" = fixture ] || exit 2\ncase "$*" in *"$EXPECTED_RESOURCE"*) ;; *) exit 3;; esac\nprintf "%s" "$FIXTURE_EDITION"\nexit "$API_EXIT"\n')
    gh.chmod(0o700)
    path = tmp_path / destination
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text('original snapshot')
    result = subprocess.run(['bash', '-c', script], cwd=tmp_path, capture_output=True, env={
        **os.environ, 'PATH': str(binary) + os.pathsep + os.environ['PATH'],
        'GH_TOKEN': 'fixture', 'GITHUB_REPOSITORY': 'ohxiyu/xiyunews',
        'RUNNER_TEMP': str(tmp_path), 'FIXTURE_EDITION': payload, 'API_EXIT': api_exit,
        'EDITION_DATE': edition_date,
        'EXPECTED_RESOURCE': 'repos/ohxiyu/xiyunews/contents/' + resource + '?ref=gh-pages',
    })
    assert (result.returncode == 0) is success
    assert path.read_text() == (payload if success else 'original snapshot')


def test_reconcile_keeps_confirmed_receipt_and_establishes_pending_snapshot_base(tmp_path):
    remote, local = snapshots()
    store = PublicationState(tmp_path / 'state')
    original = {'version': 2, 'editions': {}}
    store.load_document('x_queue', original)
    store.save_document('x_queue', local)
    remote_before, local_before = copy.deepcopy(remote), copy.deepcopy(local)
    assert store.load_document('x_queue', remote, reconcile=x_queue.reconcile_confirmed_receipts) == local
    with store.connect() as db:
        digest, source, dirty = db.execute('SELECT digest,source_digest,dirty FROM publication_documents').fetchone()
        assert (digest, source, dirty) == (signature(canonical(local)), signature(canonical(remote)), 1)
    assert remote == remote_before and local == local_before
    assert store.load_document('x_queue', remote) == local
    assert store.verify()['verified']


@pytest.mark.parametrize('field,value', [
    ('tweet_id', ''), ('tweet_id', 'unproven'), ('status', 'unknown'),
    ('status', 'failed'), ('status', 'planned'), ('text', 'changed text'),
    ('story_key', 'another-story'), ('attempted_at', '2026-10-27T00:01:00+00:00'),
    ('slot', 2), ('text_sha256', 'wrong digest'),
])
def test_incompatible_receipts_remain_conflicts_without_mutation(tmp_path, field, value):
    remote, local = snapshots()
    local['editions']['2026-10-27']['jobs'][0][field] = value
    store = PublicationState(tmp_path / 'state')
    store.load_document('x_queue', {'version': 2, 'editions': {}})
    store.save_document('x_queue', local)
    before = store.load_document('x_queue', None)
    with pytest.raises((StateConflict, x_queue.QueueError)):
        store.load_document('x_queue', remote, reconcile=x_queue.reconcile_confirmed_receipts)
    assert store.load_document('x_queue', None) == before


def test_other_queue_changes_and_conflicting_success_ids_are_never_merged():
    remote, local = snapshots()
    changed = copy.deepcopy(remote)
    changed['editions']['2026-10-27']['status'] = 'skipped_late'
    with pytest.raises(StateConflict):
        x_queue.reconcile_confirmed_receipts(local, changed)
    changed = copy.deepcopy(local)
    changed['editions']['2026-10-27']['jobs'][0]['tweet_id'] = '987654321'
    with pytest.raises(StateConflict):
        x_queue.reconcile_confirmed_receipts(local, changed)
    changed = copy.deepcopy(local)
    changed['editions']['2026-10-28'] = copy.deepcopy(local['editions']['2026-10-27'])
    with pytest.raises(StateConflict):
        x_queue.reconcile_confirmed_receipts(changed, remote)


def test_acknowledged_pending_snapshot_allows_new_receipt_without_false_conflict(tmp_path):
    remote, local = snapshots()
    store = PublicationState(tmp_path / 'state')
    store.save_document('x_queue', remote)
    store.acknowledge_document('x_queue', remote)
    store.save_document('x_queue', local)
    assert store.load_document('x_queue', remote) == local
    with pytest.raises(StateConflict):
        store.acknowledge_document('x_queue', remote)  # Newer receipt must survive.
    assert store.load_document('x_queue', None) == local
    store.acknowledge_document('x_queue', local)
    with store.connect() as db:
        assert db.execute('SELECT dirty FROM publication_documents').fetchone()[0] == 0


def test_checkpoint_failed_push_keeps_dirty_and_unchanged_retry_really_pushes(tmp_path, monkeypatch):
    monkeypatch.setenv('XIYUNEWS_STATE_DIR', str(tmp_path / 'state'))
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    remote = tmp_path / 'remote.git'
    work = tmp_path / 'queue'
    def git(*args):
        return subprocess.run(['git', *map(str, args)], check=True, capture_output=True)
    git('init', '--bare', remote)
    git('init', work)
    git('-C', work, 'config', 'user.name', 'fixture')
    git('-C', work, 'config', 'user.email', 'fixture@example.com')
    state, sent = snapshots()
    git('-C', work, 'remote', 'add', 'origin', tmp_path / 'missing.git')
    with pytest.raises(subprocess.CalledProcessError):
        x_queue.git_checkpoint(work, state)
    store = PublicationState(tmp_path / 'state')
    with store.connect() as db:
        assert db.execute('SELECT dirty FROM publication_documents').fetchone()[0] == 1
    git('-C', work, 'remote', 'set-url', 'origin', remote)
    x_queue.git_checkpoint(work, state)  # Already committed, but not yet pushed.
    with store.connect() as db:
        assert db.execute('SELECT dirty FROM publication_documents').fetchone()[0] == 0
    x_queue.git_checkpoint(work, sent)
    recovered = json.loads(git('--git-dir', remote, 'show', 'x-queue:data/x-queue.json').stdout)
    assert recovered == sent
    with store.connect() as db:
        assert db.execute('SELECT source_digest FROM publication_documents').fetchone()[0] == signature(canonical(sent))


def test_square_checkpoint_acknowledges_only_after_successful_push(tmp_path, monkeypatch):
    from src.square_delivery import git_checkpoint
    monkeypatch.setenv('XIYUNEWS_STATE_DIR', str(tmp_path / 'state'))
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
    work, remote = tmp_path / 'queue', tmp_path / 'remote.git'
    def git(*args):
        return subprocess.run(['git', *map(str, args)], check=True, capture_output=True)
    git('init', '--bare', remote)
    git('init', work)
    git('-C', work, 'config', 'user.name', 'fixture')
    git('-C', work, 'config', 'user.email', 'fixture@example.com')
    git('-C', work, 'remote', 'add', 'origin', remote)
    state = {'version': 1, 'editions': {}, 'plans': {}}
    git_checkpoint(work, state)
    store = PublicationState(tmp_path / 'state')
    with store.connect() as db:
        assert db.execute('SELECT source_digest,dirty FROM publication_documents WHERE name=?', ('square_queue',)).fetchone() == (signature(canonical(state)), 0)
    git('-C', work, 'remote', 'set-url', 'origin', tmp_path / 'missing.git')
    state['plans']['date'] = {'jobs': []}
    with pytest.raises(subprocess.CalledProcessError):
        git_checkpoint(work, state)
    with store.connect() as db:
        assert db.execute('SELECT dirty FROM publication_documents WHERE name=?', ('square_queue',)).fetchone()[0] == 1
    git('-C', work, 'remote', 'set-url', 'origin', remote)
    git_checkpoint(work, state)
    with store.connect() as db:
        assert db.execute('SELECT source_digest,dirty FROM publication_documents WHERE name=?', ('square_queue',)).fetchone() == (signature(canonical(state)), 0)
