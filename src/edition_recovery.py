"""Restore generated editions across day rollover, without AI or delivery."""
from __future__ import annotations

import argparse
import asyncio
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
import sqlite3
import subprocess

from ._file_utils import _atomic_write_text
from .daily_feed import DailyFeedState
from .edition import edition_window_for_date, items_in_edition_window
from .event_recovery import recover_catalog_links
from .models import Config, ContentItem
from .publication_state import StateConflict, active_store, canonical
from .run_report import RunReport


JOURNAL = Path("docs/_data/edition-journal.json")


def required_paths(day, languages):
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError("edition date must be canonical ISO date")
    return [Path(f"editions/{day}/edition.json"), *[
        p for lang in languages for p in (
            Path(f"_posts/{day}-summary-{lang}.md"), Path(f"editions/{day}/{lang}.html"))]]


def restore_published_files(root=Path("docs"), ref="origin/gh-pages"):
    """Restore only publication history, never source templates or local output."""
    paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", ref, "--",
        "_posts", "editions", "api/latest.json", "api/editions.json", "_data/edition-journal.json"], text=True).splitlines()
    for relative in paths:
        if not re.fullmatch(r"(?:_posts/\d{4}-\d{2}-\d{2}-summary-(?:zh|en)\.md|editions/\d{4}-\d{2}-\d{2}/(?:edition\.json|zh\.html|en\.html)|api/(?:latest|editions)\.json|_data/edition-journal\.json)", relative):
            continue
        target = root / relative
        if not target.exists():
            text = subprocess.check_output(["git", "show", ref + ":" + relative], text=True)
            target.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write_text(target, text)


def inspect_edition(state, languages=("zh", "en"), root=Path("docs")):
    """Validate all reader entry files, not just a process success or latest date."""
    missing = []
    for relative in required_paths(state.date, languages):
        path = root / relative
        if not path.is_file():
            missing.append(str(relative)); continue
        text = path.read_text()
        if relative.name == "edition.json":
            payload = json.loads(text)
            if payload.get("date") != state.date or len(payload.get("items", [])) != len(state.items):
                missing.append(str(relative)); continue
            for public, item in zip(payload["items"], state.items):
                if public.get("url") != str(item.url):
                    raise StateConflict("published edition differs from saved selection: " + state.date)
                for lang in languages:
                    title = item.metadata.get("title_" + lang) or item.title
                    summary = item.metadata.get("detailed_summary_" + lang) or item.metadata.get("detailed_summary") or item.ai_summary or ""
                    if public.get("title", {}).get(lang) != title or public.get("summary", {}).get(lang) != summary:
                        raise StateConflict("published text differs from saved selection: " + state.date)
        elif ((f'date: {state.date}\n' not in text if relative.suffix == ".md" else f'data-date="{state.date}"' not in text)
              or text.count('<article class="digest-item') != len(state.items)):
            missing.append(str(relative))
        else:
            from .publication_revision import story_revision
            lang = relative.stem if relative.suffix == ".html" else relative.stem.rsplit("-", 1)[-1]
            expected = [story_revision(str(i.url), i.metadata.get("title_" + lang) or i.title,
                i.metadata.get("detailed_summary_" + lang) or i.metadata.get("detailed_summary") or i.ai_summary or "") for i in state.items]
            actual = re.findall(r'data-content-revision="([a-f0-9]{64})"', text)
            if actual != expected:
                missing.append(str(relative))
    return missing


def import_retained_history(store, runner, *, today, days=14):
    """Recover pre-journal selections only when report and retained set agree.

    A retained dedup list proves membership/text, not original tied-score rank.
    Require original report count AND complete source/category distributions;
    ambiguity or partial retention must fail, never invent a new selection.
    """
    from .edition import edition_window_for_date
    saved = {r["date"] for r in store.saved_editions()}
    with store.connect() as db:
        rows = list(db.execute("SELECT edition,report FROM publication_runs WHERE kind='daily_publish' ORDER BY recorded_at"))
    reports = {}
    def source_counts(rows):
        # Public daily state retains Telegram author names without the display
        # '@' prefix; this is the same channel identity, never a new source.
        result = {}
        for key, count in rows.items():
            key = key.replace("telegram/@", "telegram/", 1) if key.startswith("telegram/@") else key
            result[key] = result.get(key, 0) + count
        return result
    for day, raw in rows:
        report = json.loads(raw)
        if report.get("metrics", {}).get("edition_candidates") and report.get("metrics", {}).get("displayed_today"):
            reports.setdefault(day, report)
    sources = []
    with store.connect() as db:
        sources += [("current", row[0]) for row in db.execute("SELECT payload FROM publication_documents WHERE name='daily'")]
    backups = sorted((store.path.parent / "recovery-backups").glob("*/publication.sqlite3"))[-8:]
    for path in backups:
        if path.is_symlink() or path.parent.is_symlink() or path.stat().st_uid != store.path.stat().st_uid:
            raise ValueError("unsafe retained edition backup")
        db = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
        try:
            db.execute("PRAGMA query_only=ON")
            sources += [(path.parent.name, row[0]) for row in db.execute("SELECT payload FROM publication_documents WHERE name='daily'")]
        finally:
            db.close()
    restored = []
    for day, report in reports.items():
        if day in saved or not today - timedelta(days=days) <= date.fromisoformat(day) <= today:
            continue
        # Existing published editions need no legacy reconstruction at all.
        if Path(f"docs/editions/{day}/edition.json").is_file():
            continue
        window = edition_window_for_date(day, report["timezone"])
        candidates = {}
        for origin, raw in sources:
            retained = DailyFeedState.model_validate_json(raw)
            if retained.date == day:
                candidates[canonical([i.model_dump(mode="json") for i in retained.items])] = (origin, retained.items, True)
                continue
            items = items_in_edition_window(retained.dedup_history, window)
            if (len(items) != report["metrics"]["displayed_today"]
                or source_counts(runner._source_breakdown(items)) != source_counts(report["breakdowns"].get("final_selected_sources", {}))
                or runner._group_breakdown(items) != report["breakdowns"].get("final_selected_groups")
                or not all(i.metadata.get("detailed_summary_zh") and i.metadata.get("detailed_summary_en") for i in items)):
                continue
            candidates[canonical([i.model_dump(mode="json") for i in items])] = (origin, items, False)
        if len(candidates) != 1:
            raise StateConflict("missing edition has no unique complete retained selection: " + day)
        origin, items, exact_order = next(iter(candidates.values()))
        state = DailyFeedState(date=day, timezone=report["timezone"],
            updated_at=datetime.fromisoformat(report["started_at"]), items=items)
        store.remember_edition(state.model_dump(mode="json"))
        restored.append({"date": day, "items": len(items), "source": origin,
            "original_tied_rank_available": exact_order})
    return restored


async def recover_editions(runner, store, *, now=None):
    """Render missing durable selections, leaving current state/receipts intact."""
    from .archive import load_recent_archive
    from .api_output import write_editions_index
    from .event_pipeline import EVENT_CATALOG_PATH
    now = now or datetime.now(timezone.utc)
    languages = list(runner.config.ai.languages) or ["zh"]
    # A previous successful Git export is a portable recovery input too.
    if JOURNAL.is_file():
        raw = json.loads(JOURNAL.read_text())
        if raw.get("version") != 1:
            raise ValueError("unsupported edition journal")
        for value in raw["editions"]:
            incoming = DailyFeedState.model_validate(value)
            known = {r["date"]: r for r in store.saved_editions()}
            if incoming.date in known:
                # The trusted local selection may be newer than Git. Never
                # import over it or silently replace a newer journal snapshot.
                continue
            store.remember_edition(value)
    imported = import_retained_history(store, runner, today=now.date())
    repaired = []
    for raw in store.saved_editions():
        state = DailyFeedState.model_validate(raw)
        missing = inspect_edition(state, languages)
        if not missing:
            continue
        if EVENT_CATALOG_PATH.exists():
            recover_catalog_links(state.items, edition=state.date)
        report = RunReport.start(date=state.date, timezone_name=state.timezone, started_at=now, kind="static_recovery")
        metrics = store.latest_edition_metrics(state.date)
        report.metrics.update({k: metrics[k] for k in ("edition_candidates", "analyzed_today", "high_priority") if k in metrics})
        report.set_metric("displayed_today", len(state.items))
        window = edition_window_for_date(state.date, state.timezone)
        await runner._publish_outputs(state.items, date=state.date, total_candidates=metrics.get("edition_candidates", 0),
            timezone_name=state.timezone, run_report=report, window_start=window.start, window_end=window.end, static_only=True)
        runner._publish_archive_artifacts(state.items, date=state.date, run_report=report, window_start=window.start, window_end=window.end)
        if inspect_edition(state, languages):
            raise RuntimeError("static recovery did not produce complete edition: " + state.date)
        repaired.append({"date": state.date, "items": len(state.items), "missing": missing})
    # Always include all archive dates, including holes older than latest.
    write_editions_index(load_recent_archive(120, today=now.date()))
    if repaired:
        runner._publish_current_event_pages()
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(JOURNAL, json.dumps({"version": 1, "editions": store.saved_editions()}, ensure_ascii=False, indent=2) + "\n")
    return {"repaired": repaired, "imported": imported, "ai_calls": 0, "channel_calls": 0}


def main():
    from .orchestrator import BMTNewsOrchestrator
    from .storage.manager import StorageManager
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("data/config.github.json"))
    args = parser.parse_args()
    store = active_store()
    if store is None:
        print(json.dumps({"repaired": [], "reason": "no production state backend"})); return
    restore_published_files()
    runner = BMTNewsOrchestrator(Config.model_validate_json(args.config.read_text()), StorageManager())
    print(json.dumps(asyncio.run(recover_editions(runner, store)), ensure_ascii=False))


if __name__ == "__main__":
    main()
