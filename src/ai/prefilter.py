"""Low-cost batched relevance prefilter for large candidate sets."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite

from bs4 import BeautifulSoup

from ..models import ContentItem
from .client import AIClient
from .errors import account_error
from .result_cache import AnalysisResultCache
from .utils import parse_json_response


PREFILTER_SYSTEM = """You are the fast first-pass editor for xiyu.news.
Rank candidates for a crypto-first daily briefing that may include a small
number of consequential AI/technology and public-policy stories. Penalize
promotions, generic market commentary, duplicates, and low-substance updates.
Return JSON only. Never rewrite or summarize the stories."""

PREFILTER_USER = """Score each candidate from 0 to 10 for whether it deserves
the slower full analysis pass. Preserve the supplied integer index.

{items}

Return exactly: {{"items":[{{"index":0,"score":7.5}}, ...]}}"""

COMPACT_RUBRIC = """Use the same absolute scale in every batch. Score 9-10 for
material security incidents, binding regulatory actions, completed major
transactions, consequential protocol changes or original breakthrough research.
Score 7-8 for material new developments, 5-6 for routine updates, 0-4 for
recaps, generic price moves, promotion and speculative commentary.
Give primary announcements and original research a fair score even with a
short body. Distinguish the actual new event from an opinion or market reaction.
Do not assume missing facts or treat an unverified claim as a confirmed result."""


@dataclass(frozen=True)
class PrefilterResult:
    items: list[ContentItem]
    evaluated: int
    removed: int
    failed_batches: int
    cache_hits: int = 0
    cache_misses: int = 0


class ContentPrefilter:
    """Score titles in batches, with fail-open behavior per failed batch."""

    def __init__(
        self, client: AIClient, *, batch_size: int = 20,
        cache: AnalysisResultCache | None = None,
    ) -> None:
        self.client = client
        self.batch_size = max(5, min(50, batch_size))
        self.cache = cache

    def _concurrency(self) -> int:
        config = getattr(self.client, "config", None)
        return max(1, min(8, int(getattr(config, "analysis_concurrency", 1))))

    async def select(
        self,
        items: list[ContentItem],
        *,
        maximum: int,
        reserve_per_category: int = 4,
        compact: bool = False,
        category_of: Callable[[ContentItem], str] | None = None,
        source_bonus: Callable[[ContentItem], float] | None = None,
    ) -> PrefilterResult:
        if len(items) <= maximum:
            return PrefilterResult(list(items), 0, 0, 0)

        indexed = list(enumerate(items))
        batches = [
            indexed[offset : offset + self.batch_size]
            for offset in range(0, len(indexed), self.batch_size)
        ]
        semaphore = asyncio.Semaphore(self._concurrency())
        terminal_error = None
        cache_hits = 0
        cache_misses = 0

        async def score_batch(
            batch: list[tuple[int, ContentItem]],
        ) -> tuple[dict[int, float] | None, set[int]]:
            lines = []
            batch_indices = {index for index, _ in batch}
            for index, item in batch:
                if compact:
                    title = " ".join(item.title.split())[:240]
                    body = (item.content or "").partition("--- Top Comments ---")[0].strip()
                    if body.startswith("<"):
                        body = BeautifulSoup(body[:1500], "html.parser").get_text(" ", strip=True)
                    body = body.removeprefix(item.title)
                    excerpt = " ".join(body.split())[:72]
                    details = [str(index), item.source_type.value,
                               str(item.metadata.get("category") or "other"), title]
                    if item.source_type.value == "hackernews" and item.metadata.get("score"):
                        details.append(f"HN points={item.metadata['score']}")
                    if excerpt:
                        details.append(excerpt)
                    lines.append(" | ".join(details))
                else:
                    excerpt = " ".join((item.content or "").split())[:360]
                    lines.append(f"[{index}] category={item.metadata.get('category', 'other')} "
                                 f"source={item.source_type.value} title={item.title} excerpt={excerpt}")
            if compact:
                entries = "\n".join(lines)
                user_prompt = (
                    COMPACT_RUBRIC + "\n\n"
                    f"Score all {len(batch)} stories from 0 to 10. "
                    'Return JSON {"scores":[[index,score],...]} with every supplied index once.\n\n' + entries
                )
            else:
                user_prompt = PREFILTER_USER.format(items="\n".join(lines))
            nonlocal cache_hits, cache_misses, terminal_error
            if self.cache is not None:
                cached = self.cache.get_prefilter_batch(PREFILTER_SYSTEM, user_prompt)
                raw_scores = cached.get("scores") if isinstance(cached, dict) else None
                if isinstance(raw_scores, dict) and set(raw_scores) == {
                    str(index) for index in batch_indices
                } and all(
                    isinstance(score, (int, float)) and not isinstance(score, bool)
                    and 0 <= score <= 10 and isfinite(score)
                    for score in raw_scores.values()
                ):
                    cache_hits += 1
                    return {int(index): float(score) for index, score in raw_scores.items()}, batch_indices
                cache_misses += 1
            try:
                async with semaphore:
                    if terminal_error is not None:
                        raise terminal_error
                    response = await self.client.complete(
                        system=PREFILTER_SYSTEM,
                        user=user_prompt,
                        response_format="json",
                    )
                payload = parse_json_response(response)
                if compact:
                    values = payload.get("scores") if isinstance(payload, dict) else None
                    if not isinstance(values, list) or len(values) != len(batch):
                        return None, batch_indices
                    rows = [{"index": pair[0], "score": pair[1]}
                            for pair in values if isinstance(pair, list) and len(pair) == 2]
                else:
                    rows = payload.get("items") if isinstance(payload, dict) else None
                if not isinstance(rows, list):
                    return None, batch_indices
                scores: dict[int, float] = {}
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    index = row.get("index")
                    score = row.get("score")
                    if (
                        isinstance(index, int)
                        and index in batch_indices
                        and isinstance(score, (int, float))
                        and not isinstance(score, bool)
                        and isfinite(score)
                    ):
                        scores[index] = max(0.0, min(10.0, float(score)))
                if len(scores) < (len(batch) if compact else max(1, len(batch) // 2)):
                    return None, batch_indices
                if self.cache is not None and len(scores) == len(batch_indices):
                    self.cache.store_prefilter_batch(PREFILTER_SYSTEM, user_prompt, scores)
                return scores, batch_indices
            except Exception as exc:
                blocked=account_error(exc)
                if blocked is not None:
                    terminal_error = blocked
                    raise blocked from None
                return None, batch_indices

        tasks = [asyncio.create_task(score_batch(batch)) for batch in batches]
        try:
            results = await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise
        scores: dict[int, float] = {}
        fail_open: set[int] = set()
        failed_batches = 0
        for result, indices in results:
            if result is None:
                failed_batches += 1
                fail_open.update(indices)
            else:
                scores.update(result)

        # Reserve a few candidates from every configured source category so a
        # broad crypto batch cannot erase scarce policy or AI coverage.
        reserved: set[int] = set() if compact else set(fail_open)
        by_category: dict[str, list[int]] = {}
        for index, item in indexed:
            category = category_of(item) if category_of else str(item.metadata.get("category") or "other")
            by_category.setdefault(category, []).append(index)
        def order(index: int) -> tuple[float, int]:
            bonus = source_bonus(items[index]) if source_bonus else 0
            return scores.get(index, 6.0) + bonus, -index

        for category_indices in by_category.values():
            if compact:
                category_indices.sort(key=order, reverse=True)
            else:
                category_indices.sort(key=lambda index: scores.get(index, -1), reverse=True)
            reserved.update(category_indices[: max(1, reserve_per_category)])

        ranked = sorted(
            (index for index in (set(scores) | fail_open if compact else scores) if index not in reserved),
            key=order,
            reverse=True,
        )
        if compact:
            # Keep source/category coverage but never let a failed batch or a
            # large number of leaf categories exceed the daily scoring cap.
            front = sorted(reserved, key=order, reverse=True)
            chosen = [items[index] for index in (front + ranked)[:maximum]]
            return PrefilterResult(chosen, len(scores), len(items) - len(chosen), failed_batches,
                                   cache_hits, cache_misses)
        target = max(maximum, len(reserved))
        selected = set(reserved)
        selected.update(ranked[: max(0, target - len(selected))])
        chosen = [item for index, item in indexed if index in selected]
        return PrefilterResult(
            chosen,
            evaluated=len(scores),
            removed=len(items) - len(chosen),
            failed_batches=failed_batches,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
        )
