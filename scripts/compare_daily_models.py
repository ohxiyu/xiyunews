"""One-off comparison of public daily-edition samples. No publish or send."""

import argparse
import asyncio
from collections import Counter
from datetime import datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup
from rich.console import Console

from src.ai.analyzer import ContentAnalyzer
from src.ai.client import create_ai_client
from src.ai.enricher import ContentEnricher
from src.ai.tokens import reset_usage, task_usage_snapshot
from src.edition import edition_window_for_date
from src.models import Config, ContentItem
from src.orchestrator import BMTNewsOrchestrator
from src.services.x_delivery import _weighted_length
from src.x_quality import approved_text, candidates, compose, eligible

MODELS = ("deepseek-ai/DeepSeek-V3.2", "Qwen/Qwen3.5-35B-A3B")
DATE = "2026-11-21"
WINDOW = edition_window_for_date(DATE, "Asia/Shanghai")
FACT_RANKS = (1, 2, 3, 4, 5, 6, 7, 10, 11, 12)
CALL_LIMIT = 110
SOURCE_TERMS = ("navier", "glamsterdam", "wrapped monero", "sky protocol", "fluidkey")


def read_json(path):
    return json.loads(path.read_text())


def output_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def sample_order(item):
    return hashlib.sha256(item.id.encode()).hexdigest()


def content_paragraphs(node):
    return "\n\n".join(p.get_text(" ", strip=True) for p in node.select("p")) if node else ""


def clean_items(staged, published, config):
    raw_bytes = (staged / "data/staging-items.json").read_bytes()
    staged_items = [ContentItem.model_validate(row) for row in json.loads(raw_bytes)["items"]]
    by_url = {str(item.url): item for item in staged_items}
    edition_dir = published / "editions" / DATE
    public_edition = read_json(edition_dir / "edition.json")
    published_rows = {row["url"]: row for row in public_edition["items"]}
    archived_picks = [by_url[url] for url in published_rows]
    contained = [item for item in staged_items if WINDOW.start <= item.published_at < WINDOW.end]
    others = sorted((item for item in contained if str(item.url) not in published_rows), key=sample_order)
    chosen = {str(item.url): item for item in archived_picks}
    for term in SOURCE_TERMS:
        for item in [i for i in others if term in i.title.lower()][:2]:
            chosen[str(item.url)] = item
    quotas = {"rss": 8, "telegram": 6, "hackernews": 4, "google_news": 4, "github": 2}
    represented = Counter(item.source_type.value for item in chosen.values()
                          if str(item.url) not in published_rows)
    for item in others:
        kind, url = item.source_type.value, str(item.url)
        if url not in chosen and represented[kind] < quotas.get(kind, 0):
            chosen[url] = item
            represented[kind] += 1
    assert len(chosen) == len(archived_picks) + sum(quotas.values()) == 36
    assert all(item.ai_score is None and not item.ai_summary for item in chosen.values())

    # Take the original source identities from published state where available.
    # The shared X input text is read from the public article fragment verbatim.
    reader_state = read_json(published / "_data/bmtnews_state.json")
    known = dict(by_url)
    for row in reader_state["items"] + reader_state.get("dedup_history", []):
        item = ContentItem.model_validate(row)
        if str(item.url) not in known:
            known[str(item.url)] = item
    x_input = []
    for day in ("2026-11-20", DATE, "2026-11-22", "2026-11-23"):
        directory = published / "editions" / day
        rows = read_json(directory / "edition.json")["items"]
        soup = BeautifulSoup((directory / "zh.html").read_text(), "html.parser")
        cards = {article["id"]: article for article in soup.select("article.digest-item[id]")}
        for row in rows:
            item = known.get(row["url"])
            card = cards.get(f"zh-{day}-item-{row['rank']}")
            if item is None or card is None:
                continue
            item = item.model_copy(deep=True)
            item.ai_score = row["score"]
            item.metadata["title_zh"] = card.select_one("h2").get_text(" ", strip=True)
            item.metadata["detailed_summary_zh"] = content_paragraphs(
                card.select_one(".story-body > .story-summary-body")
            )
            item.metadata["background_zh"] = content_paragraphs(
                card.select_one(".story-background .story-summary-body")
            )
            if eligible(item, config) and len(candidates(item)) >= 2:
                x_input.append((day, row["rank"], item))
    assert x_input
    return sorted(chosen.values(), key=sample_order), published_rows, x_input, {
        "staged_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "candidate_pool": len(contained),
        "sample_source_types": dict(Counter(i.source_type.value for i in chosen.values())),
        "edition": DATE,
        "x_count": len(x_input),
        "x_dates": dict(Counter(day for day, _, _ in x_input)),
        "fact_count": len(FACT_RANKS),
    }


def row(item):
    return {
        "id": item.id, "url": str(item.url), "score": item.ai_score,
        "title": item.metadata.get("title_zh") or item.title,
        "category": item.metadata.get("category"),
        "summary": item.ai_summary,
        "detail": item.metadata.get("detailed_summary_zh"),
        "background": item.metadata.get("background_zh"),
        "status": item.metadata.get("enrichment_status"),
        "analysis_failed": item.ai_reason == "Analysis failed",
        "source_type": item.source_type.value,
    }


def cost(usage, model):
    total = Decimal(0)
    for entry in usage:
        incoming = entry["input_tokens"]
        cache = entry["cached_input_tokens"]
        outgoing = entry["output_tokens"]
        if model == MODELS[0]:
            total += 4 * (incoming - cache) + Decimal("0.40") * cache + 6 * outgoing
        elif incoming >= 128_000:
            total += Decimal("1.60") * incoming + Decimal("12.80") * outgoing
        else:
            total += Decimal("0.40") * incoming + Decimal("3.20") * outgoing
    return str(total / 1_000_000)


async def run_arm(config, model, items, published_rows, x_input):
    reset_usage()
    config = config.model_copy(deep=True)
    config.ai.model = model
    config.ai.result_cache_enabled = False
    client = create_ai_client(config.ai)
    client.client = client.client.with_options(max_retries=0)
    request = client._do_request
    counters = Counter()
    requests_usage = []

    async def bounded_request(**kwargs):
        if counters["attempts"] >= CALL_LIMIT:
            counters["limit_reached"] += 1
            raise RuntimeError("model comparison request budget exhausted")
        counters["attempts"] += 1
        try:
            response = await request(**kwargs)
            counters["responses"] += 1
            if usage := response.usage:
                cached = getattr(usage, "prompt_cache_hit_tokens", None)
                if cached is None:
                    cached = getattr(usage.prompt_tokens_details, "cached_tokens", None)
                requests_usage.append({
                    "input_tokens": usage.prompt_tokens,
                    "output_tokens": usage.completion_tokens,
                    "cached_input_tokens": cached or 0,
                })
            else:
                counters["missing_usage"] += 1
            return response
        except Exception:
            counters["transport_or_api_errors"] += 1
            raise

    client._do_request = bounded_request
    runner = object.__new__(BMTNewsOrchestrator)
    runner.config = config
    runner.console = Console()
    runner.last_run_report = None
    runner._analysis_cache = None
    items = [item.model_copy(deep=True) for item in items]
    fact_items = []
    result = {"model": model}
    try:
        analyzer = ContentAnalyzer(client, allowed_categories=runner._analysis_categories(),
                                   edition_window=WINDOW)
        await analyzer.analyze_batch(items)
        result["scoring"] = [row(item) for item in items]
        fact_items = [item.model_copy(deep=True) for item in items
                      if published_rows.get(str(item.url), {}).get("rank") in FACT_RANKS]
        try:
            with patch("src.selection.create_ai_client", return_value=client):
                selection = await runner.filter_items(items, apply_balance=False, log=False)
                balanced = runner.apply_balanced_digest(selection.items, log=False,
                                                         allow_primary_borrowing=True, fill_to_minimum=True)
                _, balanced = await runner._audit_daily_ranking(selection.items, balanced)
            result["selection"] = [row(item) for item in balanced.items]
            result["selection_meta"] = {"threshold": selection.threshold_count,
                                        "after_topic_dedup": selection.topic_dedup_count}
        except RuntimeError as exc:
            result["selection"] = []
            result["selection_meta"] = {"error": type(exc).__name__}
        enricher = ContentEnricher(client)

        async def frozen_search(query):
            return []  # Both arms see the same archived source text already in the prompt.

        enricher._cached_web_search = frozen_search
        await enricher.enrich_batch(fact_items)
        result["fact"] = [row(item) for item in fact_items]
        result["x"] = []
        limit = min(config.x_delivery.max_post_chars, 280)
        for day, rank, item in x_input:
            draft = await compose(client, item, limit=limit)
            result["x"].append({"day": day, "rank": rank, "id": item.id,
                                "title": item.metadata["title_zh"], "draft": draft,
                                "pass": bool(draft and approved_text(item, draft, limit=limit)),
                                "weighted_length": _weighted_length(draft) if draft else None})
    finally:
        result["usage"] = task_usage_snapshot()
        result["billed_tokens"] = {
            key: sum(entry[key] for entry in requests_usage)
            for key in ("input_tokens", "output_tokens", "cached_input_tokens")
        }
        result["cost_cny"] = cost(requests_usage, model)
        result["requests"] = dict(counters)
        await client.client.close()
    return result


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", type=Path, required=True)
    parser.add_argument("--published", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-only", action="store_true")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    config = Config.model_validate_json(Path("data/config.github.json").read_text())
    items, published_rows, x_input, sample = clean_items(args.staged, args.published, config)
    print(json.dumps(sample, ensure_ascii=False), flush=True)
    ordered = [(published_rows.get(str(item.url), {}).get("rank"), item) for item in items]
    output_json(args.output / "sample.json", {
        **sample,
        "articles": [{"id": item.id, "title": item.title, "url": str(item.url),
                      "published_at": item.published_at.isoformat(), "original_rank": rank,
                      **({"content": item.content} if args.sample_only else {})} for rank, item in ordered],
        "x": [{"day": day, "rank": rank, "id": item.id,
               "title": item.metadata["title_zh"], "possible_sentences": candidates(item)}
              for day, rank, item in x_input],
    })
    if args.sample_only:
        return
    for model in MODELS:
        result = await run_arm(config, model, items, published_rows, x_input)
        output_json(args.output / (model.split("/")[-1] + ".json"), result)
        print(json.dumps({"model": model, "requests": result["requests"],
                          "cost_cny": result["cost_cny"], "selected": len(result["selection"]),
                          "x_pass": sum(post["pass"] for post in result["x"])}, ensure_ascii=False), flush=True)
        assert not result["requests"].get("limit_reached")


if __name__ == "__main__":
    asyncio.run(main())
