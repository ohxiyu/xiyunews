"""Static Chinese edition JSON; no secondary event/category APIs."""
from __future__ import annotations
import json
from datetime import datetime,timezone
from pathlib import Path
from typing import Sequence,List
from ._file_utils import _atomic_write_text
from .archive import ArchiveRecord
from .publication_revision import story_revision
API_ROOT=Path('docs/api')
EDITIONS_ROOT=Path('docs/editions')
DEFAULT_SITE_URL='https://xiyu.news'


def _iso(moment: datetime | None) -> str | None:
    if moment is None:
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")

def build_edition_payload(
    records: Sequence[ArchiveRecord],
    *,
    date: str,
    stats: dict[str, int],
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    site_url: str = DEFAULT_SITE_URL,
) -> dict:
    """Build the public JSON document for one edition."""
    base = site_url.rstrip("/")
    items = []
    for record in records:
        items.append(
            {
                "rank": record.rank,
                "url": record.url,
                "title": {"zh": record.title_zh},
                "summary": {"zh": record.summary_zh},
                "content_revision": {
                    "zh": story_revision(record.url, record.title_zh, record.summary_zh),
                },
                "score": record.score,
                "category": record.category,
                "top_category": record.top_category,
                "source": {
                    "type": record.source_type,
                    "label": record.source_label,
                },
                "tags": record.tags,
                "sources_count": record.sources_count,
            }
        )
    payload = {
        "version": 1,
        "content_revision_version": 1,
        "date": date,
        "generated_at": _iso(datetime.now(timezone.utc)),
        "site": base,
        "window": {"start": _iso(window_start), "end": _iso(window_end)},
        "stats": dict(stats),
        "items": items,
    }
    return payload

def write_edition_api(
    payload: dict,
    *,
    date: str,
    editions_root: Path = EDITIONS_ROOT,
    api_root: Path = API_ROOT,
) -> List[Path]:
    """Write ``edition.json`` for the date plus the ``latest.json`` pointer."""
    body = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    edition_path = editions_root / date / "edition.json"
    edition_path.parent.mkdir(parents=True, exist_ok=True)
    if edition_path.exists():
        existing = json.loads(edition_path.read_text())
        def texts(value):
            return [(row.get('id'), row.get('url'), row.get('title', {}).get('zh'),
                     row.get('summary', {}).get('zh')) for row in value.get('items', [])]
        if existing.get('date') != date or texts(existing) != texts(payload):
            raise ValueError('Published edition differs from saved selection; refusing overwrite')
        # Static recovery must preserve the original publication timestamp and
        # legacy fields as well as its words. New schemas apply to new editions.
        body = edition_path.read_text()
    else:
        _atomic_write_text(edition_path, body)

    latest_path = api_root / "latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    # A late historical repair must not move the current feed backwards.
    latest = json.loads(latest_path.read_text()) if latest_path.exists() else None
    if latest is not None and str(latest.get("date", "")) > date:
        return [edition_path]
    _atomic_write_text(latest_path, body)
    return [edition_path, latest_path]

def write_editions_index(
    records: Sequence[ArchiveRecord],
    *,
    api_root: Path = API_ROOT,
    site_url: str = DEFAULT_SITE_URL,
    limit: int = 90,
) -> Path:
    """Write the list of available editions for API consumers."""
    base = site_url.rstrip("/")
    counts: dict[str, int] = {}
    for record in records:
        counts[record.date] = counts.get(record.date, 0) + 1
    dates = sorted(counts, reverse=True)[:limit]
    payload = {
        "version": 1,
        "generated_at": _iso(datetime.now(timezone.utc)),
        "editions": [
            {
                "date": date,
                "items": counts[date],
                "json": f"{base}/editions/{date}/edition.json",
            }
            for date in dates
        ],
    }
    api_root.mkdir(parents=True, exist_ok=True)
    path = api_root / "editions.json"
    _atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    return path
