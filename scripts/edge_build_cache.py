"""Immutable publication inputs and complete cached-output verification."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request

MANIFEST = ".xiyunews-build-cache.json"
INPUTS = ["docs", "src", "scripts", "ops/daily-dispatcher", "Gemfile", "Gemfile.lock", "pyproject.toml", "uv.lock", "_config.yml", ".github/workflows/cloudflare-unified.yml"]


def build_key(artifact, tree):
    if not re.fullmatch(r"[a-f0-9]{40}", artifact):
        raise ValueError("artifact must be exact SHA")
    return hashlib.sha256(b"xiyunews-build-v1:ruby3.3:python3.12\0" + artifact.encode() + b"\0" + tree).hexdigest()


def current_key(artifact):
    tree = subprocess.check_output(["git", "ls-tree", "-rz", "--full-tree", "HEAD", "--", *INPUTS])
    return build_key(artifact, tree)


def same_deployment(health, key, artifact, force=False):
    return not force and isinstance(health, dict) and health.get("service") == "xiyunews" and health.get("status") == "ok" and health.get("site_build_key") == key and health.get("site_artifact_commit") == artifact


def files(root):
    if root.is_symlink():
        raise ValueError("cache root symlink")
    result = {}
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise ValueError("cache symlink")
        relative = path.relative_to(root)
        if any(part in {".git", ".env", ".dev.vars"} or part.startswith((".env.", ".dev.vars.")) for part in relative.parts):
            raise ValueError("private cache file")
        if path.is_file() and path.name != MANIFEST:
            with path.open("rb") as handle:
                result[str(relative)] = hashlib.file_digest(handle, "sha256").hexdigest()
    return result


def record(root, key):
    paths = files(root)
    if not paths or "index.html" not in paths or "api/latest.json" not in paths:
        raise ValueError("incomplete render cache")
    (root / MANIFEST).write_text(json.dumps({"key": key, "files": paths}, sort_keys=True) + "\n")


def verify(root, key):
    try:
        actual = files(root)
        manifest = json.loads((root / MANIFEST).read_text())
        return bool(actual and manifest.get("key") == key and manifest.get("files") == actual)
    except (OSError, ValueError, TypeError):
        return False


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def public_health():
    try:
        request = urllib.request.Request("https://xiyu.news/health", headers={"Cache-Control": "no-cache",
            "Accept": "application/json", "User-Agent": "xiyunews-publication-validator/1.0"})
        with urllib.request.build_opener(NoRedirect).open(request, timeout=8) as response:
            body = response.read(64001)
        return json.loads(body) if len(body) <= 64000 else {}
    except (OSError, ValueError):
        return {}


def output(key, value):
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a") as handle:
            handle.write(f"{key}={value}\n")
    print(f"{key}={value}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("plan", "record", "verify"))
    parser.add_argument("--artifact")
    parser.add_argument("--key")
    parser.add_argument("--root", type=Path, default=Path(".edge-rendered"))
    args = parser.parse_args()
    if args.mode == "plan":
        key = current_key(args.artifact or "")
        output("key", key)
        output("skip", str(same_deployment(public_health(), key, args.artifact, os.environ.get("FORCE_DEPLOY") == "true")).lower())
    else:
        if not re.fullmatch(r"[a-f0-9]{64}", args.key or ""):
            raise ValueError("invalid build key")
        if args.mode == "record":
            record(args.root, args.key)
        else:
            valid = verify(args.root, args.key)
            if not valid and args.root.exists():
                # Only our generated sibling output; never a repository root,
                # tool cache, state directory or redirected path.
                if args.root.name != ".edge-rendered" or args.root.is_symlink() or args.root.resolve().parent != Path.cwd().resolve():
                    raise ValueError("refusing unsafe cache cleanup")
                shutil.rmtree(args.root)
            output("valid", str(valid).lower())


if __name__ == "__main__":
    main()
