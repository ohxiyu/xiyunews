import importlib.util
import json
from pathlib import Path
import shutil

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("governance", ROOT / "scripts/check_governance.py")
governance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(governance)


@pytest.fixture
def tree(tmp_path):
    paths = [*governance.OWNED_DOCS, "VERSION", "pyproject.toml", "uv.lock",
             "ops/daily-dispatcher/package.json", "ops/daily-dispatcher/package-lock.json"]
    paths += [str(p.relative_to(ROOT)) for p in (ROOT / "project-docs").rglob("*") if p.is_file()]
    # Handoff/release records may link the authoritative brand specification.
    paths += ["brand/logo-spec.md", "LICENSE", "CONTENT-LICENSE.md", "THIRD_PARTY_NOTICES.md"]
    for relative in set(paths):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def test_repository_governance():
    assert governance.check() == []


def test_versions_are_component_scoped(tree):
    assert governance.check(tree) == []
    (tree / "VERSION").write_text("9.0.0\n")
    assert any("version" in e for e in governance.check(tree))


def test_worker_lock_mismatch(tree):
    path = tree / "ops/daily-dispatcher/package-lock.json"
    payload = json.loads(path.read_text())
    payload["packages"][""]["version"] = "2.0.0"
    path.write_text(json.dumps(payload))
    assert any("dispatcher" in e for e in governance.check(tree))


@pytest.mark.parametrize("target", ["missing.md", "../../../../outside.md"])
def test_broken_or_escaping_links(tree, target):
    (tree / "agent.md").write_text(f"[rules](AGENTS.md) [bad]({target})")
    assert any("broken local link" in e for e in governance.check(tree))


def test_duplicate_pointer_rejected(tree):
    path = tree / "project-docs/handoff.md"
    path.write_text(path.read_text() + "\n<!-- execution-pointer -->\n")
    assert any("exactly one" in e for e in governance.check(tree))


@pytest.mark.parametrize("field,value", [("issue", "https://example.com/1"), ("branch", "main"), ("base", "not-a-sha"), ("blockers", [1])])
def test_invalid_task_identity_rejected(tree, field, value):
    path = tree / "project-docs/handoff.md"
    import re
    text = path.read_text(); match = re.search(r"```json\s*(.*?)\s*```", text, re.S)
    pointer = json.loads(match.group(1)); pointer[field] = value
    path.write_text(text[:match.start(1)] + json.dumps(pointer) + text[match.end(1):])
    assert any("invalid handoff" in e for e in governance.check(tree))


def test_application_pr_needs_only_current_handoff():
    assert governance.check_change_evidence(["src/models.py"]) == ["application PR must update project-docs/handoff.md"]
    assert governance.check_change_evidence(["src/models.py", "project-docs/handoff.md"]) == []
    assert governance.check_change_evidence(["README.md"]) == []


def test_git_refs_are_not_shell_input(tmp_path):
    with pytest.raises(ValueError):
        governance.changed_paths(tmp_path, "main;echo unsafe", "a" * 40)


def test_no_release_archive_or_five_stage_evidence_required(tree):
    (tree / "project-docs/releases/1.1.0.md").unlink(missing_ok=True)
    assert governance.check_change_evidence(["src/models.py", "project-docs/handoff.md", "project-docs/releases/deleted.md"], tree) == []
    assert governance.check(tree) == []


def test_handoff_stays_one_page(tree):
    path = tree / "project-docs/handoff.md"
    path.write_text(path.read_text() + "\n" * 76)
    assert any("one page" in error for error in governance.check(tree))


def test_site_root_links_resolve_within_jekyll_source(tmp_path):
    page=tmp_path/'docs/about/index.md';page.parent.mkdir(parents=True)
    (tmp_path/'docs/feed.xml').write_text('<rss/>')
    (tmp_path/'docs/history.html').write_text('---\npermalink: /history/\n---')
    page.write_text('[RSS](/feed.xml) [History](/history/)')
    assert governance.local_links(tmp_path,'docs/about/index.md')==[]
    page.write_text('[missing](/missing/) [escape](/../VERSION)')
    assert len(governance.local_links(tmp_path,'docs/about/index.md'))==2
