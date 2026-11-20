import json
from pathlib import Path
import sqlite3
import tarfile
import pytest
from ops.backup.backup import create_snapshot, verify_restore, write_archive
from src.publication_state import PublicationState


def test_sqlite_primary_backup_omits_only_redundant_cache_mirrors(tmp_path):
    state = PublicationState(tmp_path / 'state')
    state.bootstrap({'version': 1, 'entries': {'a': {'value': {'ai_score': 8}}}}, {'staging': {'items': []}})
    for name in ('analysis-cache.json', 'staging-items.json', 'events.json'):
        (tmp_path / 'state' / name).write_text('{}')
    target = tmp_path / 'snapshot'
    target.mkdir()
    manifest = create_snapshot(target, {'publication': state.path}, state=tmp_path / 'state')
    assert set(manifest['state_files']) == {'state-events.json'}
    assert manifest['databases']['publication']['tables']['ai_cache'] == 1
    assert verify_restore(target)['verified']


def test_backup_preserves_wal_pending_and_sent_receipts(tmp_path):
    original = tmp_path / 'original.sqlite3'
    db = sqlite3.connect(original)
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('CREATE TABLE receipts (id INTEGER PRIMARY KEY, status TEXT)')
    db.executemany('INSERT INTO receipts(status) VALUES (?)', [('pending',), ('sent',), ('unknown',)])
    db.commit()
    target = tmp_path / 'snapshot'
    target.mkdir()
    manifest = create_snapshot(target, {'realtime': original}, state=tmp_path / 'none')
    assert not list(target.glob('*-wal')) and not list(target.glob('*-shm'))
    assert manifest['databases']['realtime']['tables']['receipts'] == 3
    assert verify_restore(target)['verified']
    assert not list(target.glob('*-wal')) and not list(target.glob('*-shm'))
    with sqlite3.connect(target / 'realtime.sqlite3') as restored:
        assert restored.execute('SELECT status FROM receipts ORDER BY id').fetchall() == [('pending',), ('sent',), ('unknown',)]
    assert db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0] == 3
    db.close()


def test_equal_publication_mirror_deduplicated_but_newer_mirror_preserved(tmp_path):
    state = PublicationState(tmp_path / 'state')
    state.bootstrap({'version': 1, 'entries': {}}, {'events': {'events': [{'id': 'one'}]}, 'daily': {'date': '2026-10-13'}})
    (tmp_path / 'state' / 'events.json').write_text(json.dumps({'events': [{'id': 'one'}]}, indent=4))
    (tmp_path / 'state' / 'bmtnews_state.json').write_text(json.dumps({'date': '2026-10-14'}))
    target = tmp_path / 'snapshot'
    target.mkdir()
    manifest = create_snapshot(target, {'publication': state.path}, state=tmp_path / 'state')
    assert set(manifest['state_files']) == {'state-bmtnews_state.json'}
    assert verify_restore(target)['verified']
    with sqlite3.connect(target / 'publication.sqlite3') as db:
        assert json.loads(db.execute("SELECT payload FROM publication_documents WHERE name='events'").fetchone()[0])['events'][0]['id'] == 'one'


def test_corrupt_restore_or_unsafe_paths_rejected(tmp_path):
    target = tmp_path / 'snapshot'
    target.mkdir()
    source = tmp_path / 'database.sqlite3'
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE tasks(id INTEGER)')
    create_snapshot(target, {'realtime': source}, state=tmp_path / 'none')
    (target / 'realtime.sqlite3').write_bytes(b'corrupted')
    with pytest.raises(sqlite3.DatabaseError):
        verify_restore(target)
    bad = tmp_path / 'linked.sqlite3'
    bad.symlink_to(source)
    with pytest.raises(ValueError, match='unsafe'):
        create_snapshot(tmp_path, {'realtime': bad}, state=tmp_path / 'none')


def test_only_backup_copy_compacted_and_live_rows_unchanged(tmp_path):
    source = tmp_path / 'original.sqlite3'
    with sqlite3.connect(source) as db:
        db.execute('CREATE TABLE receipts(id INTEGER PRIMARY KEY,status TEXT,payload BLOB)')
        db.executemany('INSERT INTO receipts VALUES(?,?,?)', [(1,'sent',b'a'*100000), (2,'unknown',b'b'*100000), (3,'obsolete',b'c'*500000)])
        db.execute('DELETE FROM receipts WHERE id=3')
    with sqlite3.connect(source) as db:
        before = db.execute('PRAGMA freelist_count').fetchone()[0]
        assert before > 0
    target = tmp_path / 'snapshot'
    target.mkdir()
    create_snapshot(target, {'realtime': source}, state=tmp_path / 'none')
    with sqlite3.connect(target / 'realtime.sqlite3') as db:
        assert db.execute('PRAGMA freelist_count').fetchone()[0] == 0
        assert db.execute('SELECT id,status,LENGTH(payload) FROM receipts ORDER BY id').fetchall() == [(1,'sent',100000),(2,'unknown',100000)]
    with sqlite3.connect(source) as db:
        assert db.execute('PRAGMA freelist_count').fetchone()[0] == before
    assert verify_restore(target)['verified']


def test_xz_archive_restores_all_rows_without_sqlite_sidecars(tmp_path):
    state = PublicationState(tmp_path / 'state')
    state.bootstrap({'version': 1, 'entries': {'score': {'value': {'ai_score': 8}}}}, {'events': {'events': []}})
    snapshot = tmp_path / 'snapshot'
    snapshot.mkdir()
    create_snapshot(snapshot, {'publication': state.path}, state=tmp_path / 'state')
    archive = tmp_path / 'snapshot.tar.xz'
    write_archive(snapshot, archive)
    assert archive.read_bytes().startswith(b'\xfd7zXZ\x00')
    restored = tmp_path / 'restored'
    with tarfile.open(archive, 'r:*') as tar:
        assert set(tar.getnames()) == {'manifest.json', 'publication.sqlite3'}
        tar.extractall(restored, filter='data')
    assert verify_restore(restored) == {'verified': True, 'databases': 1, 'state_files': 0}
