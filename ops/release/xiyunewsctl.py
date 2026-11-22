#!/usr/bin/env python3
"""Operate the xiyu.news daily publication from one checkout."""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "ohxiyu/xiyunews"
DAILY_HEALTH = "https://xiyu.news/health"
EDITION = "https://xiyu.news/api/latest.json"
SHA = re.compile(r"[a-f0-9]{40}")


def run(*command, capture=False, data=None, timeout=90):
    return subprocess.run(command, cwd=ROOT, check=True, input=data,
                          stdout=subprocess.PIPE if capture else None, timeout=timeout).stdout


def response(url):
    raw = run("curl", "--silent", "--show-error", "--max-time", "15",
              "--proto", "=https", "--user-agent", "xiyunews-release/1.0",
              "--header", "Cache-Control: no-cache", "--write-out", "\n%{http_code}",
              url, capture=True, timeout=55)
    body, code = raw.rsplit(b"\n", 1)
    http_status = int(code)
    if http_status != 200:
        raise ValueError(f"{url} returned HTTP {http_status}")
    return http_status, json.loads(body)


def status():
    _, daily = response(DAILY_HEALTH)
    _, edition = response(EDITION)
    return {
        "product": "xiyu.news",
        "daily": {
            "revision": daily["site_source_commit"],
            "artifact": daily["site_artifact_commit"],
            "edition": edition["date"],
            "items": len(edition["items"]),
            "runtime": daily.get("runner"),
        },
    }


def main_revision():
    remote = run("git", "ls-remote", "https://github.com/" + REPOSITORY + ".git",
                 "refs/heads/main", capture=True).decode().split()
    if len(remote) != 2 or not SHA.fullmatch(remote[0]) or remote[1] != "refs/heads/main":
        raise ValueError("Could not verify the production main revision")
    return remote[0]


def check_revision(revision):
    if main_revision() != revision:
        raise ValueError("Production main moved. Start a new release for its current revision.")


def deploy_daily(revision):
    if response(DAILY_HEALTH)[1]["site_source_commit"] == revision:
        print(f"Daily site already serves {revision}", flush=True)
        return
    check_revision(revision)
    result = run("gh", "workflow", "run", "cloudflare-unified.yml", "--repo",
                 REPOSITORY, "--ref", "main", "-f", "force_deploy=true",
                 "-f", f"expected_source={revision}", capture=True).decode()
    match = re.search(rf"https://github\.com/{REPOSITORY}/actions/runs/([0-9]+)", result)
    if not match:
        raise ValueError("GitHub did not return the deployment run. Check Actions before retrying.")
    run_id = match[1]
    actual = run("gh", "api", f"repos/{REPOSITORY}/actions/runs/{run_id}",
                 "--jq", ".head_sha", capture=True).decode().strip()
    if actual != revision:
        raise ValueError("Deployment dispatch received a different main revision. Check the Actions run.")
    print(match[0], flush=True)
    run("gh", "run", "watch", run_id, "--repo", REPOSITORY, "--exit-status", timeout=2400)
    if response(DAILY_HEALTH)[1]["site_source_commit"] != revision:
        raise ValueError("The daily site did not report the requested source revision")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="show current production modules")
    commands.add_parser("deploy", help="release the current reviewed main revision")
    args = parser.parse_args()
    try:
        if args.command == "deploy":
            revision = main_revision()
            run("git", "cat-file", "-e", f"{revision}^{{commit}}")
            print(f"xiyu.news release {revision}", flush=True)
            deploy_daily(revision)
        print(json.dumps(status(), ensure_ascii=False, indent=2))
    except subprocess.SubprocessError as error:
        print(f"xiyu.news: {error.cmd[0]} did not complete successfully", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as error:
        print(f"xiyu.news: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
