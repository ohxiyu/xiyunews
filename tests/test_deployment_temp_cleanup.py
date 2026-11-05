import fcntl
import os
from pathlib import Path

import pytest

from ops.runner.deploy_temp_cleanup import cleanup

NOW = 1793850000


def clone(root, stamp):
    path = root / f'actions_github_pages_{stamp}'
    (path / '.git').mkdir(parents=True)
    (path / 'index.html').write_text('regenerable deployment output')
    return path


def test_only_unused_owned_deployment_clones_are_removed(tmp_path):
    root, proc = tmp_path / 'home', tmp_path / 'proc'
    root.mkdir(); proc.mkdir()
    old = clone(root, (NOW - 90000) * 1000)
    young = clone(root, (NOW - 100) * 1000)
    active = clone(root, (NOW - 100000) * 1000)
    outside = tmp_path / 'business'; outside.mkdir()
    valuable = outside / 'data.db'; valuable.write_text('business data')
    (old / 'linked-business').symlink_to(outside, target_is_directory=True)
    linked = root / f'actions_github_pages_{(NOW - 110000) * 1000}'
    linked.symlink_to(outside, target_is_directory=True)
    suspicious = root / 'actions_github_pages_unknown'; suspicious.mkdir()
    no_git = root / f'actions_github_pages_{(NOW - 120000) * 1000}'; no_git.mkdir()
    fake_git = root / f'actions_github_pages_{(NOW - 130000) * 1000}'; fake_git.mkdir()
    (fake_git / '.git').symlink_to(outside, target_is_directory=True)
    process = proc / '123'; (process / 'fd').mkdir(parents=True)
    (process / 'cwd').symlink_to(root)
    (process / 'fd/3').symlink_to(active / 'index.html')
    dry = cleanup(root, min_age=86400, now=NOW, proc=proc)
    assert dry == {'removed': 0, 'eligible': 1, 'in_use': 1}
    assert old.exists()
    result = cleanup(root, min_age=86400, now=NOW, proc=proc, apply=True)
    assert result == {'removed': 1, 'eligible': 1, 'in_use': 1}
    assert not old.exists()
    assert all(p.exists() for p in (young, active, linked, suspicious, no_git, fake_git))
    assert valuable.read_text() == 'business data'
    (process / 'fd/3').unlink()
    assert cleanup(root, now=NOW, proc=proc, apply=True)['removed'] == 1
    assert young.exists()
    assert valuable.read_text() == 'business data'


def test_unsafe_roots_lock_and_future_names_are_preserved(tmp_path):
    root, proc = tmp_path / 'home', tmp_path / 'proc'
    root.mkdir(); proc.mkdir()
    future = clone(root, (NOW + 1) * 1000)
    assert cleanup(root, now=NOW, proc=proc, apply=True)['removed'] == 0
    assert future.exists()
    link = tmp_path / 'symlink'; link.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError):
        cleanup(link, now=NOW, proc=proc, apply=True)
    with pytest.raises(ValueError):
        cleanup(root, min_age=-1, proc=proc)
    with (root / '.deployment-temp-cleanup.lock').open('r') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert cleanup(root, proc=proc)['skipped'] == 'locked'
    (root / '.deployment-temp-cleanup.lock').unlink()
    outside = tmp_path / 'valuable'; outside.write_text('preserve')
    (root / '.deployment-temp-cleanup.lock').symlink_to(outside)
    with pytest.raises(OSError):
        cleanup(root, proc=proc, apply=True)
    assert outside.read_text() == 'preserve'
