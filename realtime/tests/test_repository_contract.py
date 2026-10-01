"""Exercise broken handoffs, versions, links and omitted PR evidence."""

import importlib.util
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "repository_check", ROOT / "scripts/check_repository.py"
)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_contract_rejects_inconsistent_documents(tmp_path):
    for name in (
        "AGENTS.md",
        "agent.md",
        "CLAUDE.md",
        "GEMINI.md",
        "VERSION",
        "pyproject.toml",
        "README.md",
    ):
        shutil.copy(ROOT / name, tmp_path / name)
    for name in ("docs", "src", "config", "scripts"):
        shutil.copytree(ROOT / name, tmp_path / name)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    assert module.check(tmp_path) == []
    (tmp_path / "VERSION").write_text("9.9.9\n")
    handoff = tmp_path / "docs/handoff.md"
    handoff.write_text(handoff.read_text() + "\n## Current execution pointer\n")
    with (tmp_path / "README.md").open("a") as stream:
        stream.write("\n[missing](docs/missing.md)\n")
    errors = module.check(tmp_path)
    assert any("differs" in error for error in errors)
    assert any("exactly one Current" in error for error in errors)
    assert any("Broken file link" in error for error in errors)


def test_application_diff_requires_evidence(monkeypatch):
    original = module.subprocess.check_output

    def output(command, **kwargs):
        if command[1] == "diff":
            git_root = Path(original(
                ["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True,
            ).strip()).resolve()
            prefix = ROOT.resolve().relative_to(git_root).as_posix()
            prefix = "" if prefix == "." else prefix + "/"
            return (prefix + "src/main.py\n").encode()
        return original(command, **kwargs)

    monkeypatch.setattr(module.subprocess, "check_output", output)
    errors = module.check(ROOT, "origin/main")
    assert "Application PR must update docs/handoff.md" in errors
    assert "Application PR must include a validation record" in errors
