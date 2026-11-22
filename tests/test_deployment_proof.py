"""Production receipts bind a real current edition to its exact producer bytes."""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from scripts.verify_daily_deployment import matches
from src.deployment_proof import valid_proof

NOW = datetime(2026, 11, 9, 0, 0, tzinfo=timezone.utc)
REPORT = b'{"kind":"daily_publish"}\n'
STATE = b'{"date":"2026-11-09"}\n'


def proof():
    return dict(version=1, verified=True, source_run_id='123', edition_date='2026-11-09',
                source_report_sha256=hashlib.sha256(REPORT).hexdigest(),
                selection_sha256=hashlib.sha256(STATE).hexdigest(), source_commit='a'*40,
                artifact_commit='b'*40, verified_at=NOW.isoformat())


def test_proof_requires_exact_bytes_and_current_day():
    p = proof()
    assert valid_proof(p, REPORT, STATE, now=NOW)
    assert not valid_proof(p, REPORT+b' ', STATE, now=NOW)
    assert not valid_proof(p, REPORT, STATE+b' ', now=NOW)
    assert not valid_proof(p, REPORT, STATE, now=NOW+timedelta(days=1))


@pytest.mark.parametrize('change', [dict(verified=False), dict(source_run_id=None),
    dict(source_commit='main'), dict(artifact_commit=''), dict(verified_at='invalid'),
    dict(verified_at='2026-11-09T00:00:00'), dict(verified_at='2026-11-10T00:00:00+00:00')])
def test_invalid_or_non_daily_deployment_never_authorizes_delivery(change):
    assert not valid_proof(proof() | change, REPORT, STATE, now=NOW)


def fixture():
    expected = {'date':'2026-11-09','content_revision_version':1,
                'items':[{'content_revision':{'zh':'c'*64}},{'content_revision':{'zh':'d'*64}}]}
    article=lambda char: '<article class="digest-item" data-content-revision="'+char*64+'"><section>references</section></article>'
    edition=article('c')+article('d')
    home='<header data-latest-edition-date="2026-11-09"></header><section class="daily-day" data-date="2026-11-09">'+edition+'</section>'
    health=dict(status='ok', service='xiyunews',site_build_key='key',site_artifact_commit='b'*40,
                site_source_commit='a'*40,version_id='real-worker')
    return health,expected,home,edition


def test_production_matches_complete_first_day_despite_nested_reference_sections():
    health,payload,home,edition=fixture()
    assert matches(health,payload,payload,build_key='key',artifact='b'*40,home=home,edition_html=edition)
    for changed in [home.replace('c'*64,'e'*64),home.replace('data-date="2026-11-09"','data-date="2026-11-08"'),home+edition]:
        assert not matches(health,payload,payload,build_key='key',artifact='b'*40,home=changed,edition_html=edition)
    assert not matches(health,payload|{'items':[]},payload,build_key='key',artifact='b'*40,home=home,edition_html=edition)
    assert not matches(health,payload,payload,build_key='wrong',artifact='b'*40,home=home,edition_html=edition)


def test_operations_verifies_original_producer_bytes_before_local_enrichment(tmp_path,monkeypatch):
    from src import operations, deployment_proof
    path=tmp_path/'report.json'
    report={'kind':'daily_publish','run_id':'one','date':'2026-11-09','started_at':NOW.isoformat(),
            'metrics':{'displayed_today':2},'ai_usage':[]}
    path.write_text(json.dumps(report));original=path.read_bytes()
    state=tmp_path/'state.json';state.write_bytes(STATE)
    receipt=tmp_path/'proof.json';receipt.write_text('{}')
    seen=[]
    monkeypatch.setattr(operations,'active_store',lambda:None)
    monkeypatch.setattr(deployment_proof,'valid_proof',lambda p,r,s:seen.append(r) or r==original)
    operations.finalize(path,'success',publication_proof=receipt,published_state=state)
    assert seen==[original]
    assert json.loads(path.read_text())["operations"]["publication_verified"] is True
    assert 'ai_cost' in json.loads(path.read_text())
