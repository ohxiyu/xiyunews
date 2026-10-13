"""Reviewed additive root installer; validates nginx before an ordinary reload."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import time


def inject(text):
    # Match a complete server block using balanced braces, never copying URLs.
    matches = []
    for match in re.finditer(r"\bserver\s*\{", text):
        depth, end = 1, match.end()
        while depth and end < len(text):
            depth += (text[end] == "{") - (text[end] == "}")
            end += 1
        block = text[match.start():end]
        if re.search(r"server_name\s+api\.xiyu\.news\s*;", block) and re.search(r"listen\s+443\b", block):
            matches.append(end - 1)
    if len(matches) != 1:
        raise ValueError("expected one api.xiyu.news HTTPS block")
    if "location = /ops/runtime.json" in text:
        return text
    snippet = '\n    location = /ops/runtime.json {\n        alias /var/lib/xiyunews-runtime/public/runtime.json;\n        default_type application/json;\n        add_header Cache-Control "no-store" always;\n        limit_except GET { deny all; }\n    }\n'
    end = matches[0]
    return text[:end] + snippet + text[end:]


def main():
    if os.geteuid() != 0:
        raise SystemExit("root installer required")
    source = Path(__file__).parent
    Path("/opt/xiyunews-runtime").mkdir(mode=0o755, exist_ok=True)
    Path("/var/lib/xiyunews-runtime/public").mkdir(mode=0o755, parents=True, exist_ok=True)
    for name in ("guardian.py",):
        shutil.copyfile(source / name, Path("/opt/xiyunews-runtime") / name)
    for name in ("xiyunews-guardian.service", "xiyunews-guardian.timer"):
        shutil.copyfile(source / name, Path("/etc/systemd/system") / name)
    nginx = Path("/etc/nginx/sites-available/fomobtc")
    original = nginx.read_text()
    updated = inject(original)
    if updated != original:
        backup = Path("/var/lib/xiyunews-runtime") / ("nginx-" + str(int(time.time())) + ".bak")
        shutil.copyfile(nginx, backup)
        backup.chmod(0o600)
        nginx.write_text(updated)
        try:
            subprocess.run(["nginx", "-t"], check=True, capture_output=True)
        except subprocess.CalledProcessError:
            nginx.write_text(original)
            raise RuntimeError("nginx validation failed; original restored") from None
        subprocess.run(["systemctl", "reload", "nginx"], check=True)
    for args in (("daemon-reload",), ("enable", "--now", "xiyunews-guardian.timer"), ("start", "xiyunews-guardian.service")):
        subprocess.run(["systemctl", *args], check=True)


if __name__ == "__main__":
    main()
