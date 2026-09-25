"""Offline repository contract checks; no credentials or external requests."""

import argparse
import re
import subprocess
import tomllib
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
FIELDS = (
    "当前目标",
    "任务 Issue / 负责人",
    "工作分支 / 最后提交 / PR",
    "已经完成",
    "尚未完成",
    "已运行的验证及结果",
    "尚未验证的内容",
    "线上版本 / 对应源码提交",
    "阻塞与所需权限",
    "下一步具体动作",
)


def check(root: Path, base: str | None = None) -> list[str]:
    errors = []
    required = [
        "AGENTS.md",
        "agent.md",
        "CLAUDE.md",
        "GEMINI.md",
        "VERSION",
        "pyproject.toml",
        "docs/handoff.md",
        "docs/backlog.md",
        "docs/ui-rules.md",
        "docs/data-contract.md",
        "docs/releases/README.md",
        "docs/releases/template.md",
    ]
    for name in required:
        if not (root / name).is_file():
            errors.append(f"Missing {name}")
    if errors:
        return errors
    version = (root / "VERSION").read_text().strip()
    project = tomllib.loads((root / "pyproject.toml").read_text())
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
        errors.append("VERSION must be a semantic version")
    if version != project["project"]["version"]:
        errors.append("VERSION differs from pyproject.toml")
    release = root / "docs/releases" / f"{version}.md"
    if not release.is_file() or release.read_text().splitlines()[0] != f"# {version}":
        errors.append("Missing or inconsistent version release heading")
    handoff = (root / "docs/handoff.md").read_text()
    if handoff.splitlines().count("## Current execution pointer") != 1:
        errors.append("Require exactly one Current execution pointer")
    for field in FIELDS:
        values = re.findall(rf"^{re.escape(field)}\uFF1A(.+)$", handoff, re.M)
        if len(values) != 1 or not values[0].strip():
            errors.append(f"Require exactly one populated handoff field: {field}")
    for name in ("agent.md", "CLAUDE.md", "GEMINI.md"):
        if "[AGENTS.md](AGENTS.md)" not in (root / name).read_text():
            errors.append(f"{name} must link to AGENTS.md")
    tracked = (
        subprocess.check_output(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=root,
        )
        .decode()
        .split("\0")
    )
    for name in tracked:
        path = root / name
        if path.suffix != ".md" or not path.is_file():
            continue
        content = re.sub(r"```.*?```", "", path.read_text(), flags=re.S)
        # Inline links and reference definitions; anchors/external availability are not checked.
        targets = re.findall(r"\]\(<?([^\s)>]+)>?(?:\s+\"[^\"]*\")?\)", content)
        targets += re.findall(r"^\s*\[[^\]]+\]:\s*<?([^\s>]+)", content, re.M)
        for target in targets:
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            destination = root if url.path.startswith("/") else path.parent
            if not (destination / unquote(url.path).lstrip("/")).exists():
                errors.append(f"Broken file link in {name}: {target}")
    for path in (root / "docs/releases").glob("deploy-*.md"):
        content = path.read_text()
        for field in ("部署状态", "源码提交", "运行版本", "验收结果", "回退信息", "授权记录"):
            value = re.search(rf"^{field}\uFF1A(.+)$", content, re.M)
            if not value or re.search(r"待填|unknown|TBD", value[1], re.I):
                errors.append(f"{path.name}: incomplete {field}")
        if not re.search(r"^源码提交\uFF1A[0-9a-f]{40}$", content, re.M):
            errors.append(f"{path.name}: require full source SHA")
        if not re.search(r"^部署状态\uFF1A(deployed|rolled-back)$", content, re.M):
            errors.append(f"{path.name}: invalid deployment state")
    if base:
        changed = set(
            subprocess.check_output(
                ["git", "diff", "--name-only", f"{base}...HEAD"],
                cwd=root,
            )
            .decode()
            .splitlines()
        )
        application = any(
            name.startswith(("src/", "config/", "scripts/"))
            or name in {"run.py", "pyproject.toml", "VERSION"}
            or name.startswith("requirements")
            for name in changed
        )
        if application:
            if "docs/handoff.md" not in changed:
                errors.append("Application PR must update docs/handoff.md")
            if not any(
                name.startswith("docs/releases/")
                and name.endswith(".md")
                and Path(name).name not in {"README.md", "template.md"}
                and (root / name).is_file()
                for name in changed
            ):
                errors.append("Application PR must include a validation record")
    return errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", help="Compare committed PR changes against this git ref")
    args = parser.parse_args()
    failures = check(ROOT, args.base)
    if failures:
        raise SystemExit("\n".join(failures))
    print("Repository contract checks passed")
