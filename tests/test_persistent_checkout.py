"""Exercise actual workflow fetch commands against isolated local Git remotes."""
from pathlib import Path
import shlex
import subprocess

import pytest


ROOT = Path(__file__).parents[1]
FETCH_COMMANDS = [
    (path.name, line.strip())
    for path in sorted((ROOT / ".github/workflows").glob("*.yml"))
    for line in path.read_text().splitlines()
    if line.strip().startswith("git fetch ") and "gh-pages:refs/" in line
]


def git(root, *args, input=None):
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True, input=input,
        stderr=subprocess.DEVNULL,
    ).strip()


@pytest.mark.parametrize("workflow,command", FETCH_COMMANDS)
def test_persistent_fetch_reads_latest_without_remote_write(tmp_path, workflow, command):
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "--bare", str(remote))
    publisher = tmp_path / "publisher"
    git(tmp_path, "init", "-b", "main", str(publisher))
    git(publisher, "config", "user.name", "Offline test")
    git(publisher, "config", "user.email", "test@example.invalid")
    git(publisher, "remote", "add", "origin", remote.as_uri())
    state = publisher / "state.json"
    state.write_text('{"edition":"old"}\n')
    git(publisher, "add", ".")
    git(publisher, "commit", "-m", "initial")
    git(publisher, "push", "origin", "HEAD:main", "HEAD:gh-pages")

    runner = tmp_path / "runner"
    git(tmp_path, "init", str(runner))
    git(runner, "remote", "add", "origin", remote.as_uri())
    git(runner, "fetch", "--depth=1", "origin", "gh-pages:refs/remotes/origin/gh-pages")
    old = git(runner, "rev-parse", "origin/gh-pages")

    state.write_text('{"edition":"latest"}\n')
    git(publisher, "add", ".")
    tree = git(publisher, "write-tree")
    latest = git(publisher, "commit-tree", tree, input="independent snapshot\n")
    git(publisher, "push", "origin", f"{latest}:refs/heads/published-next")
    # Fixture-only independent history; never touches a real repository.
    git(remote, "update-ref", "refs/heads/gh-pages", latest)
    before = git(remote, "show-ref")
    original = subprocess.run(
        ["git", "fetch", "--depth=1", "origin", "gh-pages:refs/remotes/origin/gh-pages"],
        cwd=runner, text=True, capture_output=True,
    )
    assert original.returncode != 0
    assert "non-fast-forward" in original.stderr
    assert git(runner, "rev-parse", "origin/gh-pages") == old

    subprocess.run(shlex.split(command), cwd=runner, check=True, capture_output=True)
    assert git(runner, "rev-parse", "origin/gh-pages") == latest, workflow
    assert git(runner, "show", "origin/gh-pages:state.json") == '{"edition":"latest"}'
    assert git(remote, "show-ref") == before
