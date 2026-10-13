import json
import pytest
from scripts.edge_build_cache import build_key, same_deployment, record, verify


def test_immutable_inputs_and_recovery_override():
    artifact = 'a' * 40
    key = build_key(artifact, b'templates-v1')
    assert key != build_key('b' * 40, b'templates-v1')
    assert key != build_key(artifact, b'templates-v2')
    health = {'service':'xiyunews','status':'ok','site_build_key':key,'site_artifact_commit':artifact}
    assert same_deployment(health, key, artifact)
    assert not same_deployment(health, key, artifact, force=True)
    assert not same_deployment({**health,'status':'failed'}, key, artifact)
    assert not same_deployment(health, key, 'b' * 40)
    with pytest.raises(ValueError):
        build_key('main', b'')


def test_full_output_integrity_and_no_private_or_symlink_cache(tmp_path):
    (tmp_path / 'api').mkdir()
    (tmp_path / 'index.html').write_text('current edition')
    (tmp_path / 'api/latest.json').write_text('{}')
    key = 'c' * 64
    record(tmp_path, key)
    assert verify(tmp_path, key)
    assert not verify(tmp_path, 'd' * 64)
    (tmp_path / 'index.html').write_text('stale or tampered')
    assert not verify(tmp_path, key)
    record(tmp_path, key)
    (tmp_path / 'unexpected').write_text('extra file')
    assert not verify(tmp_path, key)
    (tmp_path / '.env').write_text('not a real secret')
    with pytest.raises(ValueError, match='private'):
        record(tmp_path, key)
    (tmp_path / '.env').unlink()
    (tmp_path / 'linked').symlink_to(tmp_path / 'index.html')
    assert not verify(tmp_path, key)
