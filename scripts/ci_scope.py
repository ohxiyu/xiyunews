"""Conservative CI scopes from an exact Git diff; no network or credentials."""
import argparse
import re
import subprocess


def classify(paths):
    flags = {key: False for key in ("python", "web", "edge")}
    docs = {"AGENTS.md", "agent.md", "CLAUDE.md", "GEMINI.md", "LICENSE"}
    for path in paths:
        if path.startswith("project-docs/") or path in docs or path.startswith("README"):
            continue
        if path.startswith((".github/", "ops/runner/")) or path == "scripts/ci_scope.py":
            return dict.fromkeys(flags, True)
        if path.startswith("ops/daily-dispatcher/"):
            flags["web"] = flags["edge"] = True
        elif path.startswith("docs/"):
            flags["web"] = flags["edge"] = True
        elif path.startswith("tests/") and path.endswith(".mjs"):
            flags["web"] = True
        elif path.startswith(("src/", "data/", "scripts/", "tests/")) or path in {"pyproject.toml", "uv.lock", "VERSION"}:
            flags["python"] = True
            if path.startswith(("src/web", "src/site", "src/weekly", "scripts/prepare_edge")):
                flags["edge"] = True
        elif path in {"_config.yml", "Gemfile", "Gemfile.lock", "CNAME"}:
            flags["web"] = flags["edge"] = True
        else:
            # New or unrecognized ownership is never silently skipped.
            return dict.fromkeys(flags, True)
    return flags


def changed_paths(base, head):
    for sha in (base, head):
        if not re.fullmatch(r"[0-9a-f]{40}", sha):
            raise ValueError("base/head must be exact SHAs")
    raw = subprocess.check_output(["git", "diff", "--name-only", "--no-renames", "-z", f"{base}...{head}"])
    return [path.decode() for path in raw.split(b"\0") if path]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base")
    parser.add_argument("--head")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    if args.all:
        result = dict.fromkeys(("python", "web", "edge"), True)
    elif args.base and args.head:
        result = classify(changed_paths(args.base, args.head))
    else:
        parser.error("use --all or both --base and --head")
    for key, value in result.items():
        print(f"{key}={str(value).lower()}")


if __name__ == "__main__":
    main()
