"""Clean only this runner's job workspace; retain explicit business state."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import shutil
import sqlite3
import time
import uuid

WORK = Path("/opt/xiyunews-runner/_work")
STATE = Path("/home/xiyunews-runner/state")
PRODUCERS = {"xiyu.news Feed Collection", "xiyu.news Daily Edition", "Deploy Docs", "xiyu.news Weekly Review", "Editorial Rebuild"}
SNAPSHOTS = ("data/staging-items.json", "data/analysis-cache.json", "docs/_data/events.json", "docs/_data/event-legacy-urls.json", "docs/_data/bmtnews_state.json")


def workspace_path(value, work=WORK):
    target = Path(value)
    if target != work / "xiyunews" / "xiyunews" or target.is_symlink() or target.parent.is_symlink() or work.is_symlink():
        raise ValueError("not the owned repository job workspace")
    if target.exists() and (target.stat().st_uid != os.getuid() or target.resolve() != target.absolute()):
        raise ValueError("workspace owner or ancestry mismatch")
    return target


def export_snapshots(workspace, state):
    # Validate the whole batch before changing any mirror. Invalid business
    # state remains in the workspace for investigation, never silently deleted.
    snapshots = []
    for relative in SNAPSHOTS:
        source = workspace / relative
        if not source.exists():
            continue
        if source.is_symlink() or source.resolve() != source.absolute():
            raise ValueError("snapshot symlink")
        if source.stat().st_size > 64 * 1024 * 1024:
            raise ValueError("snapshot exceeds bound")
        raw = source.read_bytes()
        if not isinstance(json.loads(raw), dict):
            raise ValueError("invalid snapshot shape")
        snapshots.append((source.name, raw))
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name, raw in snapshots:
        temporary = state / (name + ".tmp")
        temporary.write_bytes(raw)
        temporary.chmod(0o600)
        temporary.replace(state / name)


def clean_workspace(workspace):
    if not workspace.exists():
        workspace.mkdir(mode=0o700, parents=True)
    for entry in workspace.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            entry.unlink()
        else:
            shutil.rmtree(entry)  # rmtree never follows nested directory links


def record_job(state, stage, metadata):
    active_file = state / "active-job.json"
    now = time.time()
    with sqlite3.connect(state / "publication.sqlite3", timeout=30) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE IF NOT EXISTS job_runs (invocation TEXT PRIMARY KEY, run_id TEXT NOT NULL, attempt TEXT NOT NULL, job TEXT NOT NULL, workflow TEXT NOT NULL, source_commit TEXT NOT NULL, status TEXT NOT NULL, started_at REAL NOT NULL, completed_at REAL)")
        active = json.loads(active_file.read_text()) if active_file.exists() else None
        if stage == "start":
            if active:
                db.execute("UPDATE job_runs SET status='interrupted', completed_at=? WHERE invocation=? AND status='started'", (now, active["invocation"]))
            invocation = str(uuid.uuid4())
            db.execute("INSERT INTO job_runs VALUES(?,?,?,?,?,?,?, ?, NULL)", (invocation, metadata["run_id"], metadata["attempt"], metadata["job"], metadata["workflow"], metadata["source_commit"], "started", now))
            active = {**metadata, "invocation": invocation}
            temporary = active_file.with_suffix(".tmp")
            temporary.write_text(json.dumps(active) + "\n")
            temporary.chmod(0o600)
            temporary.replace(active_file)
        elif active:
            if any(active.get(key) != metadata[key] for key in ("run_id", "attempt", "job")):
                raise ValueError("completion does not own active job")
            # Completion hooks also execute for failed jobs. GitHub's actual
            # conclusion remains authoritative; do not record success here.
            db.execute("UPDATE job_runs SET status='hook_completed', completed_at=? WHERE invocation=?", (now, active["invocation"]))
            active_file.unlink()
        db.execute("DELETE FROM job_runs WHERE invocation NOT IN (SELECT invocation FROM job_runs ORDER BY started_at DESC LIMIT 400) AND status != 'started'")
    (state / "publication.sqlite3").chmod(0o600)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("start", "complete"))
    args = parser.parse_args()
    if os.environ.get("GITHUB_REPOSITORY") != "ohxiyu/xiyunews":
        raise ValueError("unexpected repository")
    target = workspace_path(os.environ.get("GITHUB_WORKSPACE", ""))
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    if STATE.is_symlink() or STATE.stat().st_uid != os.getuid():
        raise ValueError("unsafe state directory")
    metadata = {key: os.environ.get(env, "") for key, env in (
        ("run_id", "GITHUB_RUN_ID"), ("attempt", "GITHUB_RUN_ATTEMPT"), ("job", "GITHUB_JOB"),
        ("workflow", "GITHUB_WORKFLOW"), ("source_commit", "GITHUB_SHA"))}
    metadata["ref"] = os.environ.get("GITHUB_REF", "")
    if not metadata["run_id"].isdigit() or not metadata["attempt"].isdigit():
        raise ValueError("missing job identity")
    with (STATE / "job-hook.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        active_file = STATE / "active-job.json"
        previous = json.loads(active_file.read_text()) if active_file.exists() else None
        if args.stage == "start" and previous and previous.get("ref") == "refs/heads/main" and previous.get("workflow") in PRODUCERS:
            export_snapshots(target, STATE)
        if args.stage == "complete" and os.environ.get("GITHUB_REF") == "refs/heads/main" and metadata["workflow"] in PRODUCERS:
            export_snapshots(target, STATE)
        record_job(STATE, args.stage, metadata)
        clean_workspace(target)
    print(json.dumps({"event": "job_workspace", "stage": args.stage, "clean": True}))


if __name__ == "__main__":
    main()
