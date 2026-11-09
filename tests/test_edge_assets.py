import json
from pathlib import Path
import pytest
from scripts.prepare_edge_assets import prepare,asset_budget


def fixture(tmp_path):
    source=tmp_path/'rendered'
    files={'index.html':'<html class="core-site"><link rel="stylesheet" href="/assets/css/core.css?v=hash"><script src="/assets/js/core.js"></script><div data-latest-edition-date="2026-11-09"></div></html>',
        'api/latest.json':json.dumps({'date':'2026-11-09','items':[{'id':'one'}]}),'history/index.html':'history','about/index.html':'about','feed.xml':'rss',
        'assets/css/core.css':'body{}','assets/js/core.js':'void 0;',
        's/index.html':'retired','events/old/index.html':'retired','api/events.json':'retired','feeds/crypto.xml':'retired',
        'editions/2026-11-08/en.html':'legacy English','_worker.js':'private implementation','CNAME':'xiyu.news'}
    for name,text in files.items():
        path=source/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
    return source


def test_stages_only_daily_public_surfaces_without_changing_immutable_input(tmp_path):
    source=fixture(tmp_path);target=tmp_path/'site';prepare(source,target)
    for name in ['s','events','api/events.json','feeds','editions/2026-11-08/en.html','_worker.js','CNAME']:
        assert not (target/name).exists()
    assert (source/'api/events.json').read_text()=='retired'
    assert (target/'api/latest.json').read_bytes()==(source/'api/latest.json').read_bytes()
    assert (target/'feed.xml').is_file()
    assert asset_budget(target)<20_000


@pytest.mark.parametrize('private',['.env','.env.production','.dev.vars','nested/.git/config','node_modules/package.json'])
def test_private_files_fail_before_staging(tmp_path,private):
    source=fixture(tmp_path);p=source/private;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('fixture')
    with pytest.raises(ValueError,match='private files'):prepare(source,tmp_path/'target')


def test_wrong_edition_missing_outputs_and_unsafe_destinations_fail(tmp_path):
    source=fixture(tmp_path)
    with pytest.raises(ValueError,match='separate directories'):prepare(source,source/'site')
    (source/'about/index.html').unlink()
    with pytest.raises(ValueError,match='about/index.html'):prepare(source,tmp_path/'target')


def test_budget_rejects_large_missing_and_external_assets(tmp_path):
    source=fixture(tmp_path)
    (source/'assets/js/core.js').write_text('x'*20_000)
    with pytest.raises(ValueError,match='exceeds 20KB'):prepare(source,tmp_path/'target')
    (source/'index.html').write_text('<script src="https://third-party.invalid/script.js"></script>')
    with pytest.raises(ValueError,match='external scripts'):asset_budget(source)


def test_symlink_and_stale_home_fail_closed(tmp_path):
    source=fixture(tmp_path);(source/'link').symlink_to(source/'index.html')
    with pytest.raises(ValueError,match='symlinks'):prepare(source,tmp_path/'site')
    (source/'link').unlink();(source/'index.html').write_text('old page')
    with pytest.raises(ValueError,match='homepage'):prepare(source,tmp_path/'site')
