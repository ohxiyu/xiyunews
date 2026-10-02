import json
from pathlib import Path

import pytest

from scripts.prepare_edge_assets import prepare


def fixture(tmp_path: Path) -> Path:
    source = tmp_path / "rendered"
    for name, text in {
        "index.html": '<div data-latest-edition-date="2026-10-02"></div>',
        "api/latest.json": json.dumps({"date": "2026-10-02", "items": [{"id": "one"}]}),
        "s/index.html": "admin", "feed-zh.xml": "rss", "sitemap.xml": "sitemap",
        "_worker.js": "private implementation", "CNAME": "xiyu.news",
    }.items():
        path = source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return source


def test_stage_public_rendered_assets_only(tmp_path):
    source = fixture(tmp_path)
    destination = tmp_path / "assets"
    prepare(source, destination)
    assert (destination / "s/index.html").read_text() == "admin"
    assert not (destination / "_worker.js").exists()
    assert not (destination / "CNAME").exists()


@pytest.mark.parametrize("private", [".env", ".env.production", ".dev.vars", "nested/.git/config", "node_modules/package.json"])
def test_fail_closed_on_private_assets(tmp_path, private):
    source = fixture(tmp_path)
    path = source / private
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not a real credential")
    with pytest.raises(ValueError, match="private files"):
        prepare(source, tmp_path / "assets")


def test_refuse_stale_or_unrendered_output(tmp_path):
    source = fixture(tmp_path)
    (source / "index.html").write_text("---\nlayout: default\n---")
    with pytest.raises(ValueError, match="homepage"):
        prepare(source, tmp_path / "assets")


def test_refuse_existing_destination_and_symlinks(tmp_path):
    source = fixture(tmp_path)
    with pytest.raises(ValueError, match="separate directories"):
        prepare(source, source / "assets")
    target = tmp_path / "existing"
    target.mkdir()
    with pytest.raises(ValueError, match="already exist"):
        prepare(source, target)
    (source / "link").symlink_to(source / "index.html")
    with pytest.raises(ValueError, match="symlinks"):
        prepare(source, tmp_path / "assets")
