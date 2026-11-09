from pathlib import Path
import pytest
from scripts.overlay_core_site import overlay, REQUIRED_FILES, REQUIRED_DIRECTORIES


def fixture(tmp_path):
    source, published = tmp_path / "source", tmp_path / "published"
    source.mkdir(); published.mkdir()
    for name in REQUIRED_DIRECTORIES:
        (source / name).mkdir(); (source / name / "current.html").write_text("new template")
    for name in REQUIRED_FILES:
        (source / name).parent.mkdir(parents=True,exist_ok=True)
        (source / name).write_text("new source: " + name)
    (published / "api").mkdir(); (published / "api/latest.json").write_text("immutable published payload")
    return source, published


def test_absent_optional_sass_succeeds_without_overwriting_publication(tmp_path):
    source, published = fixture(tmp_path)
    overlay(source, published)
    assert (published / "_layouts/current.html").read_text() == "new template"
    assert (published / "history.html").read_text() == "new source: history.html"
    assert (published / "api/latest.json").read_text() == "immutable published payload"
    assert not (published / "_sass").exists()


def test_present_optional_sass_is_copied(tmp_path):
    source, published = fixture(tmp_path)
    (source / "_sass").mkdir(); (source / "_sass/tokens.scss").write_text("$brand: blue;")
    overlay(source, published)
    assert (published / "_sass/tokens.scss").read_text() == "$brand: blue;"


def test_missing_required_input_fails_before_any_write(tmp_path):
    source, published = fixture(tmp_path)
    (source / "history.html").unlink()
    with pytest.raises(ValueError, match="history.html"):
        overlay(source, published)
    assert not (published / "_layouts").exists()
    assert (published / "api/latest.json").read_text() == "immutable published payload"


def test_ci_and_production_execute_the_same_overlay():
    for name in ["ci.yml", "cloudflare-unified.yml"]:
        workflow=Path(".github/workflows",name).read_text()
        assert "python3 scripts/overlay_core_site.py docs .edge-source" in workflow
        assert 'cp -a "docs/$directory/."' not in workflow
