#!/usr/bin/env python3
"""Operate the xiyu.news publication and realtime services from one checkout."""

import argparse
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
REPOSITORY = "ohxiyu/xiyunews"
DAILY_HEALTH = "https://xiyu.news/health"
REALTIME_HEALTH = "https://api.xiyu.news/api/health"
REALTIME_READY = "https://api.xiyu.news/api/ready"
EDITION = "https://xiyu.news/api/latest.json"
RELEASE_SCRIPT = "ops/release/install-realtime.sh"
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
    if http_status != 200 and (url, http_status) != (REALTIME_READY, 503):
        raise ValueError(f"{url} returned HTTP {http_status}")
    return http_status, json.loads(body)


def status():
    _, daily = response(DAILY_HEALTH)
    _, edition = response(EDITION)
    realtime_status, realtime = response(REALTIME_READY)
    return {
        "product": "xiyu.news",
        "daily": {
            "revision": daily["site_source_commit"],
            "artifact": daily["site_artifact_commit"],
            "edition": edition["date"],
            "items": len(edition["items"]),
            "runtime": daily.get("runner"),
        },
        "realtime": {
            "revision": realtime["source_commit"],
            "ready": realtime_status == 200 and realtime["ready"] is True,
            "telegram_enabled": realtime["telegram_enabled"],
            "sources_requiring_attention": {
                name: source["state"] for name, source in realtime["sources"].items()
                if source["state"] in {"error", "blocked", "warming", "degraded", "stale"}
            },
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


def deploy_realtime(revision, ssh_config, host):
    if response(REALTIME_HEALTH)[1]["source_commit"] == revision:
        print(f"Realtime service already runs {revision}", flush=True)
        return
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", host):
        raise ValueError("Use a host alias from the operator's SSH configuration")
    check_revision(revision)
    installer = run("git", "show", f"{revision}:{RELEASE_SCRIPT}", capture=True).decode()
    archive = run("git", "archive", revision, "realtime", capture=True)
    command = shlex.join(["sudo", "-n", "bash", "-c", installer, "--", revision])
    run("ssh", "-F", str(ssh_config), "-o", "BatchMode=yes",
        "-o", "StrictHostKeyChecking=yes", "-o", "ConnectTimeout=10",
        host, command, data=archive, timeout=900)
    if response(REALTIME_HEALTH)[1]["source_commit"] != revision:
        raise ValueError("The public realtime API did not report the requested source revision")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="show current production modules")
    deploy = commands.add_parser("deploy", help="release the current reviewed main revision")
    deploy.add_argument("--component", choices=("all", "daily", "realtime"), default="all")
    deploy.add_argument("--ssh-config", type=Path, help="existing Tokyo operator SSH configuration")
    deploy.add_argument("--host", default="xiyunews-tokyo")
    args = parser.parse_args()
    try:
        if args.command == "deploy":
            if args.component != "daily" and (not args.ssh_config or not args.ssh_config.is_file()):
                parser.error("--ssh-config must identify the existing Tokyo SSH configuration")
            revision = main_revision()
            run("git", "cat-file", "-e", f"{revision}^{{commit}}")
            print(f"xiyu.news release {revision}", flush=True)
            if args.component != "realtime":
                deploy_daily(revision)
            if args.component != "daily":
                deploy_realtime(revision, args.ssh_config, args.host)
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
