"""Independent stdlib online backup; only encrypted files leave root storage."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path("/var/backups/xiyunews")
EXPORT = Path("/home/xiyunews-runner/backup-export")
DATABASES = {"realtime": Path("/var/lib/fomobtc/fomobtc.sqlite3"),
             "publication": Path("/home/xiyunews-runner/state/publication.sqlite3")}


def deployment_manifest():
    result = {}
    for name, url, fields in (
        ("website", "https://xiyu.news/health", ("site_source_commit", "site_artifact_commit", "version_id")),
        ("realtime", "https://api.xiyu.news/api/health", ("source_commit", "version")),
    ):
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                body = response.read(64001)
            if len(body) > 64000:
                raise ValueError("health response too large")
            health = json.loads(body)
            result[name] = {key: value for key in fields if isinstance((value := health.get(key)), str) and re.fullmatch(r"[a-zA-Z0-9.-]{1,64}", value)}
        except (OSError, ValueError):
            result[name] = {"verification": "unavailable"}
    return result


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def database_manifest(path):
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=30) as db:
        if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("SQLite integrity check failed")
        tables = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        counts = {name: db.execute('SELECT COUNT(*) FROM "' + name.replace('"', '""') + '"').fetchone()[0] for (name,) in tables}
    return {"sha256": digest(path), "bytes": path.stat().st_size, "tables": counts}


def snapshot_database(source, target):
    if source.is_symlink() or target.exists():
        raise ValueError("unsafe SQLite backup path")
    with sqlite3.connect(f"file:{source}?mode=ro", uri=True, timeout=30) as original:
        with sqlite3.connect(target) as backup:
            original.backup(backup, pages=128, sleep=0.05)
    target.chmod(0o600)
    return database_manifest(target)


def create_snapshot(destination, databases=DATABASES, state=Path("/home/xiyunews-runner/state")):
    manifest = {"format": 1, "created_at": datetime.now(timezone.utc).isoformat(), "databases": {}, "state_files": {}}
    for name, source in databases.items():
        if not source.exists():
            if name == "realtime":
                raise FileNotFoundError("realtime database missing")
            continue
        info = snapshot_database(source, destination / (name + ".sqlite3"))
        manifest["databases"][name] = info
    # Only owned checkpoint snapshots, never .env/config/private keys/logs.
    for source in state.glob("*.json") if state.exists() else []:
        if source.is_symlink():
            raise ValueError("symlink in state snapshots")
        data = source.read_bytes()
        json.loads(data)
        target = destination / ("state-" + source.name)
        target.write_bytes(data)
        target.chmod(0o600)
        manifest["state_files"][target.name] = {"sha256": digest(target), "bytes": len(data)}
    (destination / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    return manifest


def verify_restore(directory):
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest.get("format") != 1 or not manifest.get("databases"):
        raise ValueError("invalid backup manifest")
    for name, expected in manifest["databases"].items():
        if name not in DATABASES:
            raise ValueError("unknown database")
        if database_manifest(directory / (name + ".sqlite3")) != expected:
            raise ValueError("restored database does not match manifest")
    for name, expected in manifest["state_files"].items():
        if not name.startswith("state-") or Path(name).name != name:
            raise ValueError("unsafe state filename")
        path = directory / name
        if digest(path) != expected["sha256"] or path.stat().st_size != expected["bytes"]:
            raise ValueError("restored state does not match manifest")
        json.loads(path.read_bytes())
    # Counts only, never messages, wallet addresses, receipts or credentials.
    return {"verified": True, "databases": len(manifest["databases"]), "state_files": len(manifest["state_files"])}


def run_backup():
    if os.geteuid() != 0:
        raise SystemExit("root backup required")
    os.umask(0o077)
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    if ROOT.is_symlink() or EXPORT.is_symlink():
        raise ValueError("unsafe backup root")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / ("xiyunews-" + stamp + ".tar.gz.age")
    if output.exists():
        raise ValueError("backup already exists")
    with tempfile.TemporaryDirectory(prefix="snapshot-", dir=ROOT) as temporary:
        directory = Path(temporary)
        snapshot = directory / "snapshot"
        snapshot.mkdir(mode=0o700)
        manifest = create_snapshot(snapshot)
        manifest["deployment"] = deployment_manifest()
        (snapshot / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
        verify_restore(snapshot)
        archive = directory / "snapshot.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            for path in sorted(snapshot.iterdir()):
                tar.add(path, arcname=path.name, recursive=False)
        subprocess.run(["age", "-R", "/etc/xiyunews-backup-recipient.pub", "-o", str(output), str(archive)], check=True, timeout=180)
    # Bound existing artifact storage use; fail closed rather than raising quota.
    if output.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("encrypted backup exceeds 8MiB off-host storage budget")
    export_file = EXPORT / "latest.tar.gz.age"
    temporary_export = EXPORT / "latest.tmp"
    shutil.copyfile(output, temporary_export)
    temporary_export.chmod(0o644)
    temporary_export.replace(export_file)
    summary = {"format": 1, "created_at": stamp, "sha256": digest(output), "bytes": output.stat().st_size}
    temporary_manifest = EXPORT / "manifest.tmp"
    temporary_manifest.write_text(json.dumps(summary) + "\n")
    temporary_manifest.chmod(0o644)
    temporary_manifest.replace(EXPORT / "manifest.json")
    # Seven owned encrypted versions locally; never touch original releases/DB.
    for expired in sorted(ROOT.glob("xiyunews-????????T??????Z.tar.gz.age"))[:-7]:
        if expired.is_symlink():
            raise ValueError("unsafe retention entry")
        expired.unlink()
    print(json.dumps(summary))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify_restore(args.verify)))
    else:
        run_backup()
