"""Rebuild the reader-only tracking index and pages, without AI or catalog mutation."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from ._file_utils import _atomic_write_text
from .event_pipeline import load_event_catalog
from .site_pages import build_event_index_data, render_event_page


def republish_tracking(root: Path, *, now: datetime | None = None, core_only: bool = False) -> Path:
    _, events = load_event_catalog(root / "_data/events.json")
    output = root / "_data/threads.json"
    payload = build_event_index_data(events, now=now)
    _atomic_write_text(output, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    # Deploy Docs restores the catalog but must also refresh existing detail
    # pages when their renderer changes. Keep compatibility redirects and API
    # evidence intact; only the current event targets are rendered here.
    for event in events:
        for language in (("zh",) if core_only else ("zh", "en")):
            prefix = "en-" if language == "en" else ""
            path = root / "events" / f"{prefix}{event.event_id}.html"
            path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write_text(path, render_event_page(event, language))
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--core-only", action="store_true")
    args = parser.parse_args()
    print(f"Rebuilt reader tracking index and detail pages: {republish_tracking(args.root, core_only=args.core_only)}; catalog and messages unchanged")
