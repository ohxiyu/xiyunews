"""Replay a historical edition against archived public inputs in scratch space."""

import argparse
import asyncio
from collections import Counter
from datetime import date, datetime, timedelta
import json
import os
from pathlib import Path
import shutil
import time
from unittest.mock import AsyncMock, patch

from bs4 import BeautifulSoup

from src.ai.client import create_ai_client
from src.ai.tokens import reset_usage, task_usage_snapshot
from src.daily_feed import DailyFeedState, load_published_daily_feed_state
from src.edition import edition_window_for_date
from src.models import Config, ContentItem, SourceType
from src.operations import estimate_cost
from src.orchestrator import BMTNewsOrchestrator
from src.selection import _deduplication_url_key
from src.storage.manager import StorageManager
from src.x_quality import approved_text, candidates, compose, eligible


def load(path):
    return json.loads(path.read_text())


def key(url):
    return _deduplication_url_key(str(url))


def paragraphs(element):
    return "\n\n".join(p.get_text(" ", strip=True) for p in element.select("p")) if element else ""


def published_items(archive, day, raw):
    directory = archive / "editions" / day
    manifest = load(directory / "edition.json")
    soup = BeautifulSoup((directory / "zh.html").read_text(), "html.parser")
    articles = {card["id"]: card for card in soup.select("article.digest-item[id]")}
    result = []
    for row in manifest["items"]:
        card = articles[f"zh-{day}-item-{row['rank']}"]
        title = card.select_one("h2").get_text(" ", strip=True)
        summary = paragraphs(card.select_one(".story-body > .story-summary-body"))
        item = raw.get(key(row["url"]))
        if item is None:
            source_time = card.select_one(".source-line time")
            moment = datetime.fromisoformat(source_time["datetime"]) if source_time else edition_window_for_date(day, "Asia/Shanghai").start
            item = ContentItem(id=card.get("data-story-id", card["id"]), source_type=SourceType.EDITORIAL,
                               title=title, url=row["url"], published_at=moment)
        item = item.model_copy(deep=True)
        item.ai_score = row["score"]
        item.ai_summary = summary
        item.metadata.update(title_zh=title, detailed_summary_zh=summary,
                             background_zh=paragraphs(card.select_one(".story-background .story-summary-body")))
        result.append(item)
    return result


def row(item):
    return {"id": item.id, "title": item.metadata.get("title_zh") or item.title,
            "url": str(item.url), "score": item.ai_score,
            "category": item.metadata.get("category"), "source_type": item.source_type.value,
            "summary": item.metadata.get("detailed_summary_zh") or item.ai_summary,
            "background": item.metadata.get("background_zh")}


async def x_replay(client, config, items):
    limit = min(280, config.x_delivery.max_post_chars)
    ready = [item for item in items if eligible(item, config) and len(candidates(item)) >= 2]
    slots = asyncio.Semaphore(config.ai.analysis_concurrency)

    async def check(item):
        async with slots:
            draft = await compose(client, item, limit=limit)
        return {"id": item.id, "url": str(item.url), "pass": bool(draft and approved_text(item, draft, limit=limit))}
    return await asyncio.gather(*(check(item) for item in ready))


async def main():
    parser = argparse.ArgumentParser()
    for name in ("stage", "archive", "scratch", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--edition", required=True)
    args = parser.parse_args()
    archive, scratch, output = (getattr(args, name).resolve() for name in ("archive", "scratch", "output"))
    inputs = load(args.stage)
    raw = {key(item.url): item for item in map(ContentItem.model_validate, inputs["items"])}
    config = Config.model_validate_json(Path("data/config.github.json").read_text())
    assert config.ai.model == "deepseek-ai/DeepSeek-V3.2"
    window = edition_window_for_date(args.edition, config.filtering.daily_timezone)
    start = window.end + timedelta(minutes=26)
    old_published = published_items(archive, args.edition, raw)
    assert all(key(item.url) in raw for item in old_published)
    previous_days = [(date.fromisoformat(args.edition) - timedelta(days=days)).isoformat() for days in (2, 1)]
    recent = [item for day in previous_days for item in published_items(archive, day, raw)]
    scratch.mkdir(parents=True, exist_ok=False)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.stage, scratch / "staging-input.json")
    os.chdir(scratch)
    Path("docs/_data").mkdir(parents=True)
    Path("docs/_data/bmtnews_state.json").write_text(DailyFeedState(
        date=previous_days[-1], timezone=window.timezone, updated_at=window.start, items=recent,
    ).model_dump_json())
    Path("data").mkdir()
    x_off = config.model_copy(deep=True)
    x_off.x_delivery.enabled = False
    runner = BMTNewsOrchestrator(x_off, StorageManager(data_dir=str(scratch / "data")))
    runner.fetch_all_sources = AsyncMock(return_value=[])

    async def frozen_search(self, query, max_results=3):
        return []  # Use the same fixed source text for each historical replay.

    started = time.perf_counter()
    with patch("src.ai.enricher.ContentEnricher._cached_web_search", frozen_search):
        await runner.run_daily_edition(staging_path=scratch / "staging-input.json",
                                       edition_date=args.edition, now=start)
    elapsed = round(time.perf_counter() - started, 2)
    report = load(Path("data/run-report.json"))
    usage = report["ai_usage"]
    current = load_published_daily_feed_state(args.edition, window.timezone).items
    for path in (Path("docs/_posts") / f"{args.edition}-summary-zh.md",
                 Path("docs/editions") / args.edition / "edition.json",
                 Path("docs/editions") / args.edition / "zh.html"):
        assert path.is_file() and path.stat().st_size
    reset_usage()
    client = create_ai_client(config.ai)
    try:
        baseline_x = await x_replay(client, config, old_published)
        reset_usage()
        new_x = await x_replay(client, config, current)
        x_usage = task_usage_snapshot()
    finally:
        await client.client.close()

    baseline_keys = {key(item.url) for item in old_published}
    current_keys = {key(item.url) for item in current}
    metrics = report["metrics"]
    result = {"edition": args.edition, "seconds": elapsed, "metrics": metrics,
              "timings": report.get("timings_sec", {}), "usage": usage, "cost": estimate_cost(usage),
              "old": [row(item) for item in old_published],
              "new": [row(item) for item in current],
              "baseline_overlap": len(baseline_keys & current_keys),
              "baseline_x": baseline_x, "new_x": new_x, "x_cost": estimate_cost(x_usage),
              "audit": {"analyzed_cap": metrics.get("analyzed_today", 0) <= 80,
                        "token_ceiling": metrics.get("ai_total_tokens", 0) + sum(
                            r["input_tokens"] + r["output_tokens"] for r in x_usage) <= 200_000,
                        "minimum_articles": len(current) >= config.filtering.minimum_display_items,
                        "score_floor": all(item.ai_score >= config.filtering.ai_score_threshold for item in current)},
              "sources": dict(Counter(item.source_type.value for item in current))}
    (output / f"{args.edition}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps({"date": args.edition, "seconds": elapsed, "tokens": metrics["ai_total_tokens"],
                      "selected": len(current), "overlap": result["baseline_overlap"],
                      "x_before": [sum(p["pass"] for p in baseline_x), len(baseline_x)],
                      "x_after": [sum(p["pass"] for p in new_x), len(new_x)],
                      "audit": result["audit"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
