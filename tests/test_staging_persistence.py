"""Offline real-Git coverage: no credentials, Actions, AI or production writes."""
from pathlib import Path
import subprocess

import pytest


SCRIPT = Path(__file__).parents[1] / "scripts/persist_staging_cache.sh"


def git(root, *args):
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


@pytest.fixture
def repo(tmp_path):
    remote = tmp_path / "remote.git"
    remote.mkdir()
    git(remote, "init", "--bare")
    work = tmp_path / "work"
    work.mkdir()
    git(work, "init", "-b", "main")
    git(work, "config", "user.name", "Offline test")
    git(work, "config", "user.email", "test@example.invalid")
    git(work, "remote", "add", "origin", str(remote))
    workflow = work / ".github/workflows/test.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("old workflow\n")
    git(work, "add", ".")
    git(work, "commit", "-m", "initial")
    git(work, "push", "origin", "HEAD:staging-cache")
    old = git(work, "rev-parse", "HEAD")
    workflow.write_text("changed workflow must not reach cache branch\n")
    git(work, "add", ".")
    git(work, "commit", "-m", "new main workflow")
    data = work / "data"
    data.mkdir()
    (data / "staging-items.json").write_text('{"items": [1]}\n')
    (data / "analysis-cache.json").write_text('{"cache": [2]}\n')
    return work, remote, old


def persist(work):
    return subprocess.run(["bash", str(SCRIPT)], cwd=work, text=True,
                          capture_output=True, check=True)


def test_cache_update_preserves_parent_workflows_and_main_worktree(repo):
    work, remote, old = repo
    main = git(work, "rev-parse", "HEAD")
    persist(work)
    new = git(remote, "rev-parse", "staging-cache")
    assert git(remote, "rev-parse", f"{new}^") == old
    assert git(remote, "show", f"{new}:.github/workflows/test.yml") == "old workflow"
    assert git(remote, "diff", "--name-only", old, new).splitlines() == [
        "data/analysis-cache.json", "data/staging-items.json"]
    assert git(work, "rev-parse", "HEAD") == main
    assert git(work, "branch", "--show-current") == "main"
    assert "unchanged" in persist(work).stdout
    assert git(remote, "rev-parse", "staging-cache") == new


def test_new_cache_branch_contains_only_cache_files(repo):
    work, remote, _ = repo
    git(remote, "update-ref", "-d", "refs/heads/staging-cache")
    persist(work)
    assert git(remote, "ls-tree", "-r", "--name-only", "staging-cache").splitlines() == [
        "data/analysis-cache.json", "data/staging-items.json"]
    assert git(remote, "rev-list", "--count", "staging-cache") == "1"


def test_missing_optional_cache_keeps_existing_blob(repo):
    work, remote, _ = repo
    persist(work)
    (work / "data/analysis-cache.json").unlink()
    (work / "data/staging-items.json").write_text('{"items": [3]}\n')
    persist(work)
    assert git(remote, "show", "staging-cache:data/analysis-cache.json") == '{"cache": [2]}'


def test_missing_staging_does_not_push(repo):
    work, remote, old = repo
    (work / "data/staging-items.json").unlink()
    assert "No staging" in persist(work).stdout
    assert git(remote, "rev-parse", "staging-cache") == old


def test_remote_failure_does_not_create_or_overwrite_branch(repo):
    work, remote, old = repo
    git(work, "remote", "set-url", "origin", str(work / "missing.git"))
    result = subprocess.run(["bash", str(SCRIPT)], cwd=work, capture_output=True)
    assert result.returncode != 0
    assert git(remote, "rev-parse", "staging-cache") == old


def test_production_collection_has_retired_the_cache_branch_writer():
    workflow = (SCRIPT.parents[1] / ".github/workflows/feed-collection.yml").read_text()
    assert "persist_staging_cache.sh" not in workflow
    assert "staging-cache" not in workflow
