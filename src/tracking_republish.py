"""Rebuild the reader-only tracking index, without AI or catalog mutation."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from ._file_utils import _atomic_write_text
from .event_pipeline import load_event_catalog
from .site_pages import build_event_index_data


def republish_tracking(root: Path, *, now: datetime | None = None) -> Path:
    _, events = load_event_catalog(root / "_data/events.json")
    output = root / "_data/threads.json"
    payload = build_event_index_data(events, now=now)
    _atomic_write_text(output, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    print(f"Rebuilt reader tracking index: {republish_tracking(args.root)}; catalog and messages unchanged")
