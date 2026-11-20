"""Offline repository governance checks; never query credentials or production."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import tomllib
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
OWNED_DOCS = [
    "AGENTS.md", "agent.md", "CLAUDE.md", "GEMINI.md", "README.md",
    "project-docs/handoff.md", "project-docs/configuration.md",
    "project-docs/data-contract.md", "project-docs/ui-rules.md",
    "project-docs/x-distribution.md", "project-docs/daily-dispatcher.md",
    "project-docs/self-hosted-runner.md",
]
POINTER = "<!-- execution-pointer -->"
FIELDS = {"goal", "issue", "owner", "branch", "base", "status", "next", "blockers"}


def changed_paths(root, base, head):
    # Refs come from GitHub SHA environment variables, never interpolated shell.
    for value in (base, head):
        if not re.fullmatch(r"[0-9a-f]{40}", value):
            raise ValueError("base/head must be exact commit SHAs")
    return subprocess.check_output(
        ["git", "diff", "--name-only", "--diff-filter=ACMRD", f"{base}...{head}"],
        cwd=root, text=True,
    ).splitlines()


def check_change_evidence(paths, root=None):
    application = any(
        p.startswith(("src/", "docs/", "ops/", "data/", "realtime/"))
        or p in {"VERSION", "pyproject.toml", "uv.lock"}
        or p.startswith(".github/workflows/")
        for p in paths
    )
    errors = []
    if application:
        if "project-docs/handoff.md" not in paths:
            errors.append("application PR must update project-docs/handoff.md")

    return errors


def local_links(root, relative):
    path = root / relative
    if not path.exists():
        return [f"missing document: {relative}"]
    text = path.read_text()
    # Ignore fenced code examples. Validate links, not prose URL examples.
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    errors = []
    for match in re.finditer(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        target = match.group(1).strip().strip("<>")
        if urlsplit(target).scheme or target.startswith("//") or not target:
            continue
        target = unquote(target.split("#", 1)[0])
        if not target:
            continue
        if target.startswith('/') and relative.startswith('docs/'):
            # Jekyll root links refer to public routes, not the filesystem root.
            site = (root / 'docs').resolve()
            resolved = (site / target.lstrip('/')).resolve()
            candidates = [resolved]
            if target.endswith('/'):
                candidates += [resolved / 'index.md', resolved / 'index.html',
                               resolved.with_suffix('.md'), resolved.with_suffix('.html')]
            valid = resolved.is_relative_to(site) and any(candidate.is_file() for candidate in candidates)
        else:
            resolved = (path.parent / target).resolve()
            valid = resolved.is_relative_to(root.resolve()) and resolved.exists()
        if not valid:
            errors.append(f"{relative}: broken local link {target}")
    return errors


def check(root=ROOT, changed=()):
    errors = []
    try:
        version = (root / "VERSION").read_text().strip()
        if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version):
            errors.append("VERSION must be a semantic version")
        project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
        lock = tomllib.loads((root / "uv.lock").read_text())
        own = [p["version"] for p in lock["package"] if p["name"] == project["name"]]
        if project["version"] != version or own != [version]:
            errors.append("VERSION, pyproject.toml and uv.lock application version differ")
        package = json.loads((root / "ops/daily-dispatcher/package.json").read_text())
        npm_lock = json.loads((root / "ops/daily-dispatcher/package-lock.json").read_text())
        if not (package["version"] == npm_lock["version"] == npm_lock["packages"][""]["version"]):
            errors.append("dispatcher package/lock versions differ")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"invalid version files: {exc}")

    try:
        text = (root / "project-docs/handoff.md").read_text()
        if text.count(POINTER) != 1:
            raise ValueError("handoff must contain exactly one execution pointer")
        match = re.search(r"<!-- execution-pointer -->\s*```json\s*(.*?)\s*```", text, re.S)
        pointer = json.loads(match.group(1)) if match else {}
        if set(pointer) != FIELDS:
            raise ValueError("handoff pointer fields missing or unknown")
        if len(text.splitlines()) > 75:
            raise ValueError("handoff must fit one page (75 lines)")
        for name in FIELDS - {"blockers"}:
            if not isinstance(pointer[name], str) or not pointer[name].strip():
                raise ValueError(f"{name} must be a nonempty string")
        if not isinstance(pointer["blockers"], list) or any(not isinstance(x, str) or not x.strip() for x in pointer["blockers"]):
            raise ValueError("blockers must be a list of nonempty strings")
        if not re.fullmatch(r"https://github.com/ohxiyu/xiyunews/issues/\d+", pointer["issue"]):
            raise ValueError("pointer must reference a task Issue in this repository")
        if not pointer["branch"].startswith("agent/"):
            raise ValueError("pointer branch must be agent/*")
        if not re.fullmatch(r"[0-9a-f]{40}", pointer["base"]):
            raise ValueError("base must be an exact SHA")

    except (OSError, ValueError, KeyError, TypeError) as exc:
        errors.append(f"invalid handoff: {exc}")

    docs = set(OWNED_DOCS)
    docs.update(p for p in changed if p.endswith(".md") and (root / p).exists())
    for path in sorted(docs):
        errors.extend(local_links(root, path))
    for entry in ("agent.md", "CLAUDE.md", "GEMINI.md"):
        path = root / entry
        if path.exists() and ("AGENTS.md" not in path.read_text() or len(path.read_text().splitlines()) > 12):
            errors.append(f"{entry} must remain a short shared-rule entry")
    errors.extend(check_change_evidence(changed, root))
    return errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head")
    args = parser.parse_args()
    if bool(args.base) != bool(args.head):
        parser.error("--base and --head must be supplied together")
    try:
        paths = changed_paths(ROOT, args.base, args.head) if args.base else []
        errors = check(changed=paths)
    except (ValueError, subprocess.CalledProcessError) as exc:
        errors = [str(exc)]
    if errors:
        print("\n".join(f"ERROR: {error}" for error in errors))
        return 1
    print("Governance checks passed (versions, links and one-page task pointer).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
