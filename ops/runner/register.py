"""Enroll the fixed private repository runner; token arrives only on stdin."""
import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    if os.geteuid() == 0:
        raise SystemExit("Run as xiyunews-runner, never root.")
    root = Path("/opt/xiyunews-runner")
    if (root / ".runner").exists():
        raise SystemExit("Already enrolled; refusing credential replacement.")
    token = sys.stdin.readline().strip()
    if not token or len(token) > 1024 or not token.isalnum():
        raise SystemExit("Invalid registration token.")
    env = os.environ.copy()
    # Runner CommandSettings consumes and clears this documented input prefix.
    # The one-hour enrollment token is absent from arguments, files and output.
    env["ACTIONS_RUNNER_INPUT_TOKEN"] = token
    subprocess.run(
        [
            "./config.sh", "--unattended",
            "--url", "https://github.com/ohxiyu/xiyunews",
            "--name", "xiyunews-tokyo-1",
            "--labels", "xiyunews-tokyo",
            "--work", "_work",
        ],
        cwd=root,
        env=env,
        check=True,
    )


if __name__ == "__main__":
    main()
