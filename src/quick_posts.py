"""Publish the manual Quick Post stream without collection or AI calls.

The private/editorial registry remains in Git. Only an explicit public field
allowlist is emitted; drafts and internal notes never enter the public API.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
import html
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from ._file_utils import _atomic_write_text

CATEGORIES = {"", "crypto-markets", "crypto-exchange", "crypto-protocol",
              "crypto-security", "policy-regulation", "ai-technology", "macro-policy"}


def _batch_rows(row: dict) -> list[dict]:
    """Validate the whole group before flattening; never publish a partial batch."""
    def text(value: object, limit: int, required: bool = False) -> str:
        if not isinstance(value, str) or len(value) > limit or required and not value.strip():
            raise ValueError("Invalid batch text")
        return value.strip()

    def identity(value: object) -> str:
        value = text(value, 36, True)
        if not re.fullmatch(r"[a-f0-9-]{36}", value):
            raise ValueError("Invalid batch ID")
        return value

    root = identity(row.get("id"))
    text(row.get("raw"), 10000, True)
    entries = row.get("items")
    anchor = row.get("anchor_id")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 8:
        raise ValueError("Invalid batch size")
    if anchor is not None and (not isinstance(anchor, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,160}", anchor)):
        raise ValueError("Invalid anchor")
    if any(type(row.get(flag)) is not bool for flag in ("enabled", "pin", "breaking")):
        raise ValueError("Invalid batch flags")
    image = row.get("image") or ""
    if not isinstance(image, str) or image and not re.fullmatch(r"/assets/uploads/quick-[a-f0-9]{64}\.(png|jpg|webp)", image):
        raise ValueError("Invalid batch image")
    result, seen = [], {root}
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            raise ValueError("Invalid batch item")
        item_id = identity(item.get("id"))
        if item_id in seen:
            raise ValueError("Duplicate batch ID")
        seen.add(item_id)
        category, tags, sources = item.get("category") or "", item.get("tags"), item.get("sources")
        if category not in CATEGORIES or not isinstance(tags, list) or len(tags) > 10 or not isinstance(sources, list) or len(sources) > 10:
            raise ValueError("Invalid batch metadata")
        links = []
        for source in sources:
            if not isinstance(source, dict):
                raise ValueError("Invalid source")
            url = text(source.get("url"), 2048, True)
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
                raise ValueError("Unsafe source")
            links.append({"title": text(source.get("title") or "原文", 200, True), "url": url})
        result.append({
            "id": item_id, "title": text(item.get("title"), 200, True),
            "body": text(item.get("body"), 10000, True), "category": category,
            "background": text(item.get("background") or "", 2000),
            "market_impact": text(item.get("market_impact") or "", 2000),
            "tags": [text(tag, 50, True) for tag in tags], "sources": links,
            "url": links[0]["url"] if links else "", "image": image if index == 0 else "",
            "date": row["date"], "pin": row["pin"], "breaking": row["breaking"],
            "anchor_id": anchor, "batch_id": root, "batch_index": index, "batch_size": len(entries),
            "created_at": str(row.get("created_at") or ""), "updated_at": str(row.get("updated_at") or ""),
        })
    if len(json.dumps(entries, ensure_ascii=False, separators=(",", ":"))) > 60000:
        raise ValueError("Batch too large")
    return result


def public_posts(payload: object, today: date) -> list[dict]:
    rows = payload.get("items", []) if isinstance(payload, dict) else []
    result = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict) or row.get("type") not in {"quick_post", "quick_batch"} or row.get("enabled") is not True:
            continue
        try:
            day = date.fromisoformat(row["date"])
        except (KeyError, TypeError, ValueError):
            continue
        if not today - timedelta(days=1) <= day <= today:
            continue
        if row["type"] == "quick_batch":
            try:
                batch = _batch_rows(row)
                ids = {row["id"], *(item["id"] for item in batch)}
                if ids & seen:
                    continue
                seen.update(ids)
                result.extend(batch)
            except (KeyError, TypeError, ValueError):
                pass
            continue
        identity, body = row.get("id"), row.get("body")
        if not isinstance(identity, str) or not re.fullmatch(r"[a-f0-9-]{36}", identity) or identity in seen:
            continue
        if not isinstance(body, str) or not body.strip() or len(body) > 10000:
            continue
        if not today - timedelta(days=1) <= day <= today:
            continue
        url = str(row.get("url") or "")
        try:
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
                url = ""
        except ValueError:
            url = ""
        image = str(row.get("image") or "")
        if not re.fullmatch(r"/assets/uploads/quick-[a-f0-9]{64}\.(png|jpg|webp)", image):
            image = ""
        seen.add(identity)
        position = row.get("position")
        if type(position) is not int or not 0 <= position <= 1000:
            position = None
        result.append({
            "id": identity, "body": body.strip(), "url": url, "image": image,
            "date": day.isoformat(), "category": str(row.get("category") or ""),
            "pin": row.get("pin") is True, "breaking": row.get("breaking") is True,
            "created_at": str(row.get("created_at") or ""),
            "updated_at": str(row.get("updated_at") or ""),
            "position": position,
        })
    return sorted(result, key=lambda row: (row["date"], row["pin"], row["created_at"],
                  row.get("batch_id", row["id"]), -row.get("batch_index", 0)), reverse=True)


def render_posts(items: list[dict]) -> str:
    if not items:
        return ""
    parts = ['<section class="quick-post-stream" aria-label="Quick Post"><h2>Quick Post</h2>']
    for item in items:
        esc = lambda value: html.escape(str(value), quote=True)
        badges = (" · Breaking" if item["breaking"] else "") + (" · PIN" if item["pin"] else "")
        parts.append(f'<article class="quick-post-public" id="quick-{esc(item["id"])}">'
                     f'<small>xiyu.news · {esc(item["date"])}{badges}</small>')
        if item.get("title"):
            parts.append(f'<h2>{esc(item["title"])}</h2>')
        for paragraph in re.split(r"\n\s*\n", item["body"]):
            parts.append(f'<p>{esc(paragraph).replace(chr(10), "<br>")}</p>')
        if item["image"]:
            parts.append(f'<img src="{esc(item["image"])}" alt="Quick Post 配图" loading="lazy">')
        if item.get("batch_id"):
            parts.append('<details class="quick-post-details"><summary>背景、影响与参考资料</summary>')
            for key, label in (("market_impact", "市场影响"), ("background", "背景")):
                if item.get(key):
                    parts.append(f'<h3>{label}</h3><p>{esc(item[key])}</p>')
            for source in item["sources"]:
                parts.append(f'<a href="{esc(source["url"])}" target="_blank" rel="noopener noreferrer">{esc(source["title"])}</a>')
            if item["tags"]:
                parts.append('<p class="quick-post-tags">' + esc(" ".join("#" + tag for tag in item["tags"])) + "</p>")
            parts.append("</details>")
        elif item["url"]:
            parts.append(f'<a href="{esc(item["url"])}" target="_blank" rel="noopener noreferrer">Source ↗</a>')
        parts.append("</article>")
    parts.append("</section>")
    return "\n".join(parts)


def publish(source: Path, output: Path, today: date) -> None:
    # A corrupt registry must fail the build, not erase the public stream.
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("Invalid editorial registry")
    items = public_posts(payload, today)
    (output / "api").mkdir(parents=True, exist_ok=True)
    (output / "_data").mkdir(parents=True, exist_ok=True)
    _atomic_write_text(output / "api/quick-posts.json", json.dumps(
        {"version": 1, "date": today.isoformat(), "items": items}, ensure_ascii=False) + "\n")
    # JSON strings are output as text by Liquid, not re-parsed as Liquid code.
    _atomic_write_text(output / "_data/quick_posts.json", json.dumps(
        {"html": render_posts(items)}, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("data/editorial.json"))
    parser.add_argument("--output", type=Path, default=Path("docs"))
    parser.add_argument("--date", type=date.fromisoformat)
    args = parser.parse_args()
    publish(args.source, args.output, args.date or datetime.now(ZoneInfo("Asia/Shanghai")).date())


if __name__ == "__main__":
    main()
