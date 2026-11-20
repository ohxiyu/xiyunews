import os
from pathlib import Path
import subprocess

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'ops/runner/setup-ruby-cache.sh'


@pytest.mark.parametrize('role', ['ci', 'producer'])
def test_locked_dependencies_use_separate_persistent_paths_and_offline_first(tmp_path, role):
    binaries = tmp_path / 'bin'; binaries.mkdir()
    (tmp_path / 'Gemfile.lock').write_text('locked fixture')
    ruby = binaries / 'ruby'
    ruby.write_text('#!/bin/sh\nprintf "%064d" 0\n'); ruby.chmod(0o700)
    bundle = binaries / 'bundle'
    bundle.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$TRACE_FILE"\n[ "$1" != check ]\n'); bundle.chmod(0o700)
    trace = tmp_path / 'trace'
    cache = tmp_path / 'cache'
    env = {**os.environ, 'PATH': str(binaries) + os.pathsep + os.environ['PATH'],
           'TRACE_FILE': str(trace), 'XIYUNEWS_BUNDLE_CACHE_ROOT': str(cache)}
    result = subprocess.run(['bash', str(SCRIPT), role], cwd=tmp_path, env=env, capture_output=True)
    assert result.returncode == 0, result.stderr.decode()
    lines = trace.read_text().splitlines()
    assert lines == [f'config set --local path {cache}/{role}/ruby-3.3/{"0" * 64}/installed',
                     f'config set --local cache_path {cache}/{role}/ruby-3.3/{"0" * 64}/cache',
                     'config set --local deployment true', 'check', 'install --local']
    assert (tmp_path / 'Gemfile.lock').read_text() == 'locked fixture'
    assert not (cache / ('producer' if role == 'ci' else 'ci')).exists()
    result = subprocess.run(['bash', str(SCRIPT), '../producer'], cwd=tmp_path, env=env, capture_output=True)
    assert result.returncode == 64
    assert trace.read_text().splitlines() == lines
