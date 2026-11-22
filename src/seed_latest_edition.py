"""Load the validated current public edition into Cloudflare's single record."""
from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
from re import fullmatch
from time import sleep

from .edge_state import Transport
from .publication_state import StateConflict


def bundle(assets: Path, artifact: str, build: str) -> dict:
    if not fullmatch(r"[0-9a-f]{40}", artifact) or not build:
        raise ValueError("expected the immutable deployment identity")
    api = (assets / "api/latest.json").read_text()
    payload = json.loads(api)
    day = date.fromisoformat(payload["date"]).isoformat()
    if day != payload["date"] or not payload["items"]:
        raise ValueError("expected one dated, nonempty public edition")
    route = day.replace("-", "/") + "/summary-zh.html"
    return {
        "day": day,
        "artifact": artifact,
        "build": build,
        "home": (assets / "index.html").read_text(),
        "page": (assets / route).read_text(),
        "api": api,
        "rss": (assets / "feed.xml").read_text(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--assets", required=True, type=Path)
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--build", required=True)
    args = parser.parse_args()
    payload = bundle(args.assets, args.artifact, args.build)
    transport = Transport()
    # The new Worker version can need a few seconds to reach the caller's POP.
    for attempt in range(6):
        try:
            result = transport.call("publish-latest", payload)
            break
        except StateConflict as exc:
            if attempt == 5 or str(exc) not in (
                "private state request rejected: 404",
                "private state request rejected: 409",
            ):
                raise
            sleep(5)
    if result != {"published": payload["day"], "artifact": args.artifact}:
        raise StateConflict("latest edition write did not confirm the requested snapshot")
    print("Current public edition stored in Cloudflare: " + payload["day"])


if __name__ == "__main__":
    main()
