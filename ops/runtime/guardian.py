"""Bounded runner guardian. Never reads application secrets or restarts a sender."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path("/var/lib/xiyunews-runtime")
UNIT = "xiyunews-runner.service"


def decide(state, busy, paused, ledger, now):
    """Pure decision: inactive enabled runner only; maximum 3 starts/day."""
    attempts = [float(t) for t in ledger if now - float(t) < 86400]
    eligible = state in {"inactive", "failed"} and not busy and not paused
    allowed = eligible and len(attempts) < 3 and (not attempts or now - max(attempts) >= 1800)
    return allowed, attempts


def command(*args):
    return subprocess.check_output(args, text=True, timeout=10).strip()


def main():
    if os.geteuid() != 0:
        raise SystemExit("root guardian required")
    now = time.time()
    state = command("systemctl", "show", UNIT, "--property=ActiveState", "--value")
    enabled = command("systemctl", "show", UNIT, "--property=UnitFileState", "--value") == "enabled"
    group = command("systemctl", "show", UNIT, "--property=ControlGroup", "--value")
    if not group and state in {"inactive", "failed"}:
        group = "/system.slice/xiyunews-runner.service"
    if not group.startswith("/system.slice/xiyunews-runner.service"):
        raise RuntimeError("unexpected runner cgroup")
    pids = Path("/sys/fs/cgroup" + group + "/cgroup.procs")
    busy = False
    for pid in pids.read_text().split() if pids.exists() else []:
        try:
            busy |= Path("/proc", pid, "comm").read_text().strip() == "Runner.Worker"
        except FileNotFoundError:
            pass
    ledger_path = ROOT / "starts.json"
    ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else []
    paused = (ROOT / "paused").exists() or not enabled
    allowed, attempts = decide(state, busy, paused, ledger, now)
    if allowed:
        attempts.append(now)
        # Commit BEFORE I/O. Even a timeout consumes the recovery budget.
        temporary = ledger_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(attempts))
        temporary.chmod(0o600)
        temporary.replace(ledger_path)
        command("systemctl", "start", UNIT)  # start is a no-op if a race already started it
        state = command("systemctl", "show", UNIT, "--property=ActiveState", "--value")
    status = "paused" if paused else "busy" if busy else "idle" if state == "active" else "stopped"
    payload = {"service": "xiyunews-runner", "status": status,
               "checked_at": int(now), "starts_24h": len(attempts)}
    output = ROOT / "public" / "runtime.json"
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload) + "\n")
    temporary.chmod(0o644)
    temporary.replace(output)
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
