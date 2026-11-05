import json
import os
from pathlib import Path
import sqlite3
import pytest
from ops.runner.job_hooks import workspace_path, clean_workspace, export_snapshots, record_job
from ops.runner import job_hooks


def test_exact_workspace_and_symlinks_preserve_outside_data(tmp_path):
    base = tmp_path / '_work'
    workspace = base / 'xiyunews/xiyunews'
    workspace.mkdir(parents=True)
    tools = tmp_path / 'tools'
    tools.mkdir()
    (tools / 'valuable').write_text('tool cache remains')
    (workspace / 'linked').symlink_to(tools, target_is_directory=True)
    (workspace / 'temporary').write_text('job output')
    assert workspace_path(str(workspace), base) == workspace
    clean_workspace(workspace)
    assert not list(workspace.iterdir())
    assert (tools / 'valuable').read_text() == 'tool cache remains'
    with pytest.raises(ValueError):
        workspace_path(str(tmp_path), base)
    workspace.rmdir()
    workspace.symlink_to(tools, target_is_directory=True)
    with pytest.raises(ValueError):
        workspace_path(str(workspace), base)


def test_business_snapshots_validated_before_cleanup_and_no_env_copy(tmp_path):
    workspace, state = tmp_path / 'job', tmp_path / 'state'
    (workspace / 'data').mkdir(parents=True)
    (workspace / 'data/analysis-cache.json').write_text('{"entries":{}}')
    (workspace / '.env').write_text('not a real secret')
    export_snapshots(workspace, state)
    assert json.loads((state / 'analysis-cache.json').read_text()) == {'entries': {}}
    assert not (state / '.env').exists()
    (workspace / 'data/staging-items.json').write_text('broken')
    with pytest.raises(ValueError):
        export_snapshots(workspace, state)
    assert (workspace / 'data/staging-items.json').exists()


def test_matrix_jobs_unique_and_completion_never_claims_success(tmp_path):
    metadata = {'run_id':'123','attempt':'1','job':'matrix','workflow':'CI','source_commit':'a' * 40}
    record_job(tmp_path, 'start', metadata)
    record_job(tmp_path, 'complete', metadata)
    record_job(tmp_path, 'start', metadata)
    record_job(tmp_path, 'start', {**metadata, 'job':'next'})
    with sqlite3.connect(tmp_path / 'publication.sqlite3') as db:
        assert db.execute('SELECT COUNT(*) FROM job_runs').fetchone()[0] == 3
        assert set(row[0] for row in db.execute('SELECT status FROM job_runs')) == {'started','interrupted','hook_completed'}
    with pytest.raises(ValueError, match='does not own'):
        record_job(tmp_path, 'complete', metadata)


def test_invalid_business_snapshot_still_reclaims_old_clones_but_keeps_workspace(tmp_path, monkeypatch):
    workspace, state = tmp_path / 'workspace', tmp_path / 'state'
    (workspace / 'data').mkdir(parents=True)
    (workspace / 'data/staging-items.json').write_text('invalid JSON')
    monkeypatch.setattr(job_hooks, 'STATE', state)
    monkeypatch.setattr(job_hooks, 'workspace_path', lambda value: workspace)
    monkeypatch.setenv('GITHUB_REPOSITORY', 'ohxiyu/xiyunews')
    monkeypatch.setenv('GITHUB_RUN_ID', '123')
    monkeypatch.setenv('GITHUB_RUN_ATTEMPT', '1')
    monkeypatch.setenv('GITHUB_WORKFLOW', 'Deploy Docs')
    monkeypatch.setenv('GITHUB_REF', 'refs/heads/main')
    monkeypatch.setattr('sys.argv', ['job_hooks.py', 'complete'])
    cleanups = []
    monkeypatch.setattr(job_hooks, 'clean_deployment_temps', lambda **kwargs: cleanups.append(kwargs) or {})
    with pytest.raises(ValueError):
        job_hooks.main()
    assert cleanups == [{'apply': True}]
    assert (workspace / 'data/staging-items.json').read_text() == 'invalid JSON'
    monkeypatch.setenv('GITHUB_REPOSITORY', 'another/repository')
    cleanups.clear()
    with pytest.raises(ValueError, match='unexpected repository'):
        job_hooks.main()
    assert cleanups == []
