"""Prepare Telegram group text from an immutable published snapshot, without AI."""
from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
import re

from .telegram_delivery import _first_complete_sentence, _plain_text, _safe_http_url, _shorten

SNAPSHOT_PATH = "api/_telegram-group.json"


def text(value, limit=420):
    return _shorten(_plain_text(value), limit)


def brief(value):
    return _first_complete_sentence(value, "zh")


def pack(entries, header, footer, limit=3600):
    size = lambda value: len(value.encode("utf-16-le")) // 2
    parts, current = [], header
    for entry in entries:
        if size(header + "\n\n" + entry + footer) > limit:
            raise ValueError("one entry exceeds the safe message size")
        if size(current + "\n\n" + entry + footer) > limit:
            parts.append(current + footer)
            current = header
        current += "\n\n" + entry
    if current != header:
        parts.append(current + footer)
    return parts


def build_snapshot(edition, index, artifact):
    date = edition.get("date", "")
    if not re.fullmatch(r"20\d\d-\d\d-\d\d", date) or not edition.get("items"):
        raise ValueError("missing published edition")
    if not re.fullmatch(r"[a-f0-9]{40}", artifact):
        raise ValueError("immutable artifact SHA required")
    day_link = "https://xiyu.news/" + date.replace("-", "/") + "/summary-zh"
    header = f"<b>xiyu.news · 每日信息流 · {date}</b>\n今日 {len(edition['items'])} 条重点资讯"
    overview = brief(edition.get("overview", {}).get("zh", ""))
    if overview:
        header += "\n" + html.escape(overview)
    entries = []
    for item in edition["items"]:
        rank = item["rank"]
        if type(rank) is not int or rank < 1:
            raise ValueError("invalid published rank")
        title = text(item.get("title", {}).get("zh") or item.get("title", {}).get("en"), 120)
        if not title:
            raise ValueError("missing published title")
        anchor = f"{day_link}#zh-{date}-item-{rank}"
        entry = f'<b>{rank:02}</b> <a href="{anchor}">{html.escape(title)}</a>'
        if rank <= 3:
            summary = brief(item.get("summary", {}).get("zh", ""))
            if summary:
                entry += "\n" + html.escape(summary)
        entries.append(entry)
    footer = f'\n\n<a href="{day_link}">阅读完整信息流 →</a>'
    feed = pack(entries, header, footer)
    focused = {row["event_id"] for row in index.get("focus", [])[:6]}
    rows = {}
    for key in ("focus", "threads", "dormant", "archived", "other", "completed"):
        for row in index.get(key, []):
            rows[row["event_id"]] = row
    events = []
    for event_id, row in rows.items():
        if not re.fullmatch(r"evt_[a-z0-9]+", event_id):
            continue
        # Retired URL stubs are not live TrackedEvents. Do not invent dates.
        if not row.get("latest_at") or not row.get("status"):
            if event_id in focused:
                raise ValueError("focus event has no material timestamp/status")
            continue
        updates = []
        for update in row.get("timeline", [])[:3]:
            update_id = update.get("update_id", "")
            if not re.fullmatch(r"upd_[a-z0-9]+", update_id):
                continue
            refs = []
            for source in update.get("sources", [])[:2]:
                url = _safe_http_url(source.get("url"))
                if url and len(url) <= 300:
                    refs.append({"url": url, "label": text(source.get("label") or "来源", 40)})
            updates.append({"id": update_id, "date": update["date"],
                "kind": text(update.get("type_zh"), 20),
                "text": brief(update.get("text_zh") or update.get("text_en")), "sources": refs})
        events.append({"id": event_id, "focus": event_id in focused,
            "title": text(row.get("title_zh") or row.get("title_en"), 120),
            "status": row["status"], "status_label": text(row.get("status_zh"), 30),
            "state": brief(row.get("summary_zh") or row.get("summary_en")),
            "background": brief(row.get("background_zh") or row.get("background_en")),
            "latest_at": row["latest_at"], "updates": updates})
    return {"version": 1, "date": date, "artifact": artifact,
        "feed_parts": feed, "events": events}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--artifact", required=True)
    args = parser.parse_args()
    edition = json.loads((args.source / "api/latest.json").read_text())
    index = json.loads((args.source / "_data/threads.json").read_text())
    snapshot = build_snapshot(edition, index, args.artifact)
    output = args.destination / SNAPSHOT_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False) + "\n")
    print(f"Prepared published group snapshot for {snapshot['date']}; no AI, no sends")


if __name__ == "__main__":
    main()
