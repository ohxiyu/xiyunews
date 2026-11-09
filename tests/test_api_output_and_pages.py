"""Daily machine outputs retain dates and Chinese source text."""
import json
from datetime import datetime,timezone
from src.api_output import build_edition_payload,write_edition_api,write_editions_index
from src.archive import ArchiveRecord


def record(day='2026-11-09'):
    return ArchiveRecord(date=day,rank=1,item_id='one',url='https://example.com/one',
        title_zh='中文标题',summary_zh='事实摘要',title_en='Legacy title',score=8)


def test_new_payload_is_chinese_only_and_revisioned():
    p=build_edition_payload([record()],date='2026-11-09',stats={'displayed':1},
        window_start=datetime(2026,11,8,23,tzinfo=timezone.utc))
    assert p['items'][0]['title']=={'zh':'中文标题'}
    assert p['items'][0]['summary']=={'zh':'事实摘要'}
    assert len(p['items'][0]['content_revision']['zh'])==64
    assert set(p['items'][0]['content_revision'])=={'zh'}
    assert 'market' not in p and 'overview' not in p
    assert 'event' not in p['items'][0] and 'thread' not in p['items'][0]
    assert p['window']['start']=='2026-11-08T23:00:00Z'


def test_historical_recovery_never_moves_latest_backwards(tmp_path):
    for day in ('2026-11-09','2026-11-08'):
        write_edition_api(build_edition_payload([record(day)],date=day,stats={}),date=day,
            editions_root=tmp_path/'editions',api_root=tmp_path/'api')
    assert json.loads((tmp_path/'api/latest.json').read_text())['date']=='2026-11-09'
    assert (tmp_path/'editions/2026-11-08/edition.json').is_file()


def test_history_index_counts_each_edition_without_rewriting_content(tmp_path):
    path=write_editions_index([record('2026-11-08'),record()],api_root=tmp_path)
    assert [r['date'] for r in json.loads(path.read_text())['editions']]==['2026-11-09','2026-11-08']


def test_recovery_preserves_published_json_bytes_and_legacy_fields(tmp_path):
    p=build_edition_payload([record()],date='2026-11-09',stats={})
    p['legacy']={'title_en':'Keep original record'}
    editions=tmp_path/'editions';api=tmp_path/'api'
    write_edition_api(p,date=p['date'],editions_root=editions,api_root=api)
    dated=editions/p['date']/'edition.json';original=dated.read_bytes()
    p.pop('legacy');p['generated_at']='2026-11-09T12:00:00Z'
    write_edition_api(p,date=p['date'],editions_root=editions,api_root=api)
    assert dated.read_bytes()==original==(api/'latest.json').read_bytes()


def test_changed_published_words_fail_without_touching_either_pointer(tmp_path):
    import pytest
    p=build_edition_payload([record()],date='2026-11-09',stats={})
    editions=tmp_path/'editions';api=tmp_path/'api'
    write_edition_api(p,date=p['date'],editions_root=editions,api_root=api)
    dated=editions/p['date']/'edition.json';original=dated.read_bytes()
    p['items'][0]['summary']['zh']='改写历史事实'
    with pytest.raises(ValueError,match='refusing overwrite'):
        write_edition_api(p,date=p['date'],editions_root=editions,api_root=api)
    assert dated.read_bytes()==original==(api/'latest.json').read_bytes()
