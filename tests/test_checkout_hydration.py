import os
from pathlib import Path
import subprocess

import pytest

from scripts import hydrate_checkout


def test_bounded_fetch_restores_exact_full_tree_and_retries_one_failed_batch(tmp_path, monkeypatch):
    git = lambda *args: subprocess.run(['git', *map(str, args)], check=True, capture_output=True)
    origin = tmp_path / 'origin.git'
    source = tmp_path / 'source'
    git('init', source)
    git('-C', source, 'config', 'user.name', 'fixture')
    git('-C', source, 'config', 'user.email', 'fixture@example.com')
    (source / 'src').mkdir(); (source / 'src/app.py').write_text('application')
    documents = source / 'project-docs'; documents.mkdir()
    for index in range(11):
        (documents / f'file {index}.png').write_bytes(os.urandom(100 + index))
    (documents / 'link').symlink_to('file 0.png')
    git('-C', source, 'add', '.')
    git('-C', source, 'commit', '-m', 'fixture')
    git('clone', '--bare', source, origin)
    git('--git-dir', origin, 'config', 'uploadpack.allowFilter', 'true')
    git('--git-dir', origin, 'config', 'uploadpack.allowAnySHA1InWant', 'true')
    checkout = tmp_path / 'checkout'
    git('clone', '--filter=blob:none', '--no-checkout', origin.as_uri(), checkout)
    git('-C', checkout, 'sparse-checkout', 'set', 'src')
    git('-C', checkout, 'checkout')
    assert not (checkout / 'project-docs').exists()
    monkeypatch.chdir(checkout)
    monkeypatch.setenv('GH_TOKEN', 'fixture-token-never-on-command-line')
    cache = tmp_path / 'cache'
    monkeypatch.setenv('XIYUNEWS_DOCUMENT_CACHE', str(cache))
    calls, failed = [], False
    run = subprocess.run
    def checked_run(args, **kwargs):
        nonlocal failed
        assert 'fixture-token-never-on-command-line' not in ' '.join(args)
        if 'fetch' in args:
            calls.append(args)
            assert len(kwargs['input'].splitlines()) <= 4
            assert 'GH_TOKEN' not in kwargs['env']
            if not failed:
                failed = True
                raise subprocess.CalledProcessError(128, args, stderr=b'sensitive test transport detail')
        return run(args, **kwargs)
    monkeypatch.setattr(hydrate_checkout.subprocess, 'run', checked_run)
    monkeypatch.setattr(hydrate_checkout.time, 'sleep', lambda _: None)
    head = git('rev-parse', 'HEAD').stdout
    hydrate_checkout.hydrate()
    assert len(calls) == 4
    assert git('rev-parse', 'HEAD').stdout == head
    assert not git('status', '--porcelain').stdout
    for path in documents.iterdir():
        target = checkout / 'project-docs' / path.name
        assert target.is_symlink() == path.is_symlink()
        assert target.read_bytes() == path.read_bytes()
    with pytest.raises(ValueError):
        hydrate_checkout.hydrate(batch_size=100)
    second = tmp_path / 'second'
    git('clone', '--filter=blob:none', '--no-checkout', origin.as_uri(), second)
    git('-C', second, 'sparse-checkout', 'set', 'src')
    git('-C', second, 'checkout')
    monkeypatch.chdir(second)
    hydrate_checkout.hydrate()
    assert len(calls) == 4  # Exact cached objects avoid downloading screenshots again.
    assert not git('status', '--porcelain').stdout
    next(iter(cache.iterdir())).write_bytes(b'corrupt cache')
    with pytest.raises(ValueError, match='digest mismatch'):
        hydrate_checkout.hydrate()
