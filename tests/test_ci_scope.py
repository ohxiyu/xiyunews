"""CI scope safety: unrelated docs, cross-module changes, deletions and unknowns."""
import subprocess

import pytest

from scripts.ci_scope import changed_paths, classify


@pytest.mark.parametrize("paths,expected", [
    (["project-docs/handoff.md"], set()),
    (["README.md", "project-docs/releases/verification.md"], set()),
    (["src/scrapers/rss.py", "tests/test_rss.py"], {"python"}),
    (["docs/assets/js/reader.js"], {"web", "edge"}),
    (["src/web_feed.py"], {"python", "edge"}),
    (["ops/daily-dispatcher/src/unified.ts"], {"web", "edge"}),
    (["src/models.py", "docs/_layouts/default.html"], {"python", "web", "edge"}),
    ([".github/workflows/daily-summary.yml"], {"python", "web", "edge"}),
    (["scripts/ci_scope.py"], {"python", "web", "edge"}),
    (["new-owner/file.txt"], {"python", "web", "edge"}),
])
def test_safety_boundaries(paths, expected):
    assert {key for key, value in classify(paths).items() if value} == expected


def test_real_git_rename_and_deletion_keep_old_module_scope(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=tmp_path, text=True).strip()
    git("init", "-b", "main")
    git("config", "user.name", "Offline test")
    git("config", "user.email", "test@example.invalid")
    source = tmp_path / "src/scrapers/rss.py"
    source.parent.mkdir(parents=True)
    source.write_text("old source\n")
    git("add", ".")
    git("commit", "-m", "before")
    before = git("rev-parse", "HEAD")
    doc = tmp_path / "project-docs/archive.md"
    doc.parent.mkdir()
    source.rename(doc)
    git("add", "-A")
    git("commit", "-m", "move")
    after = git("rev-parse", "HEAD")
    monkeypatch.chdir(tmp_path)
    paths = changed_paths(before, after)
    assert "src/scrapers/rss.py" in paths
    assert classify(paths)["python"]


def test_arbitrary_revision_input_is_rejected():
    with pytest.raises(ValueError):
        changed_paths("main; unexpected", "0" * 40)
