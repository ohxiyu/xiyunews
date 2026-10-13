import json
from pathlib import Path
import sqlite3
import pytest
from ops.backup.backup import create_snapshot, verify_restore
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
    assert manifest['databases']['realtime']['tables']['receipts'] == 3
    assert verify_restore(target)['verified']
    with sqlite3.connect(target / 'realtime.sqlite3') as restored:
        assert restored.execute('SELECT status FROM receipts ORDER BY id').fetchall() == [('pending',), ('sent',), ('unknown',)]
    assert db.execute('SELECT COUNT(*) FROM receipts').fetchone()[0] == 3
    db.close()


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
