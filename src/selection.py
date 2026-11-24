"""AI scoring, conservative daily deduplication and quota balancing."""
from __future__ import annotations
import time
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import unquote_plus, urlsplit
from .models import SOURCE_TIERS, ContentItem, SourceType
from .daily_feed import item_identity
from .edition import EditionWindow
from .ai.client import create_ai_client
from .ai.analyzer import ContentAnalyzer
from .ai.prefilter import ContentPrefilter
from .ai.result_cache import AnalysisResultCache, split_cached
from .dedup import fingerprint, same_thread, legacy_story_assignments

_TRACKING_QUERY_PARAMETERS = {
    "_ga",
    "dclid",
    "fbclid",
    "gclid",
    "igshid",
    "li_fat_id",
    "mc_cid",
    "mc_eid",
    "msclkid",
    "ttclid",
    "twclid",
    "vero_id",
}
_LOW_SIGNAL_TITLE = re.compile(
    r"^(?:daily roundup|weekly roundup|market recap|(?:每日|每周)?行情回顾|早报[｜|：:]|晚报[｜|：:])"
    r"|(?:开始领取|免费领取|exclusive giveaway|sponsored post)",
    re.IGNORECASE,
)
_NEWS_SIGNAL = re.compile(
    r"漏洞|被盗|暂停|披露|批准|调查|裁决|发布|收购|破产|升级|异动|"
    r"\b(?:hack|breach|exploit|lawsuit|court|filed|launch|release|upgrade|ban|approved|acquire|investigation)\b",
    re.IGNORECASE,
)
_LOCAL_SHORTLIST_MAX = 800


def _deduplication_url_key(url: str) -> tuple[str, str, str, str, Optional[int], str, str]:
    """Return a conservative URL identity key for cross-source deduplication."""
    parsed = urlsplit(url)
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    port = parsed.port
    if (scheme, port) in {("http", 80), ("https", 443)}:
        port = None

    path = parsed.path.rstrip("/") or "/"
    query_parts = []
    for part in parsed.query.split("&") if parsed.query else []:
        name = unquote_plus(part.partition("=")[0]).lower()
        if name.startswith("utm_") or name in _TRACKING_QUERY_PARAMETERS:
            continue
        query_parts.append(part)

    return (
        scheme,
        parsed.username or "",
        parsed.password or "",
        host,
        port,
        path,
        "&".join(query_parts),
    )

@dataclass
class BalancedDigestResult:
    """Items and selection statistics from balanced digest filtering."""

    items: List[ContentItem]
    enabled: bool = False
    group_counts: Dict[str, int] = field(default_factory=dict)
    group_limits: Dict[str, Optional[int]] = field(default_factory=dict)
    duplicate_categories: List[str] = field(default_factory=list)
    borrowed_count: int = 0
    category_limit_deferred: int = 0
    source_limit_deferred: int = 0
    minimum_fill_count: int = 0

@dataclass
class FilteringPipelineResult:
    """Items and statistics from score, topic, and digest filtering."""

    items: List[ContentItem]
    threshold_count: int
    topic_dedup_count: int
    topic_dedup_removed: int
    balanced_digest: BalancedDigestResult

class SelectionPipeline:
    def _local_daily_shortlist(self, items: List[ContentItem]) -> List[ContentItem]:
        """Reduce exact syndication and reserve coverage across source categories."""
        ordered = sorted(items, key=lambda item: (
            bool(_LOW_SIGNAL_TITLE.search(item.title)),
            SOURCE_TIERS.index(self._source_tier(item)),
            not bool(_NEWS_SIGNAL.search(item.title)),
            -item.published_at.timestamp(),
            item.id,
        ))
        unique = {}
        for item in ordered:
            title_key = " ".join(item.title.casefold().split())
            unique.setdefault(title_key or item.id, item)
        counts: dict[str, int] = defaultdict(int)
        reserved, rest = [], []
        for item in unique.values():
            category = str(item.metadata.get("category") or "other")
            if counts[category] < 4:
                reserved.append(item)
                counts[category] += 1
            else:
                rest.append(item)
        return (reserved + rest)[:_LOCAL_SHORTLIST_MAX]

    async def _daily_scoring_order(self, items: List[ContentItem]) -> List[ContentItem]:
        limit = self.config.ai.prefilter_max_candidates
        shortlist = self._local_daily_shortlist(items)
        if self.last_run_report:
            self.last_run_report.set_metric("local_shortlist_candidates", len(shortlist))
        if len(shortlist) <= limit:
            return shortlist
        category_groups = {category: key for key, group in self.config.filtering.category_groups.items()
                           for category in group.categories}
        result = await ContentPrefilter(
            create_ai_client(self.config.ai), batch_size=self.config.ai.prefilter_batch_size,
            cache=self._result_cache(),
        ).select(shortlist, maximum=limit, reserve_per_category=3, compact=True,
                 category_of=lambda item: category_groups.get(item.metadata.get("category"), "other"))
        self._record_prefilter(result)
        return result.items

    def _record_prefilter(self, result) -> None:
        if self.last_run_report:
            for key, value in {
                "prefilter_evaluated": result.evaluated,
                "prefilter_removed": result.removed,
                "prefilter_failed_batches": result.failed_batches,
                "prefilter_cache_hits": result.cache_hits,
                "prefilter_cache_misses": result.cache_misses,
            }.items():
                self.last_run_report.set_metric(key, self.last_run_report.metrics.get(key, 0) + value)

    async def _analyze_daily_batch(self, items: List[ContentItem], *, edition_window: EditionWindow):
        """Evaluate a first pass and retain ranked reserves for an underfilled slate."""
        target = self.config.ai.daily_score_target
        if target is None:
            return await self._analyze_content(items, edition_window=edition_window), []
        order = await self._daily_scoring_order(items)
        first = await self._analyze_content(order[:target], edition_window=edition_window, preselected=True)
        floor = self.config.filtering.ai_score_threshold
        qualified = sorted(
            (item.ai_score for item in first
             if item.ai_score is not None and item.ai_score >= floor and not item.metadata.get("chinese_invalid")),
            reverse=True,
        )
        wanted = self.config.filtering.max_items or 14
        reserve = order[target:]
        if reserve and (len(qualified) < wanted or qualified[wanted - 1] <= floor + 0.25):
            first.extend(await self._analyze_content(reserve, edition_window=edition_window, preselected=True))
            reserve = []
        return first, reserve

    def _result_cache(self) -> AnalysisResultCache | None:
        if not self.config.ai.result_cache_enabled:
            return None
        if self._analysis_cache is None:
            self._analysis_cache = AnalysisResultCache(
                Path(self.config.ai.result_cache_path),
                model=f"{self.config.ai.provider.value}:{self.config.ai.model}",
                ttl_days=self.config.ai.result_cache_ttl_days,
                max_entries=self.config.ai.result_cache_max_entries,
                prompt_revision=hashlib.sha256(json.dumps({
                    "version": "generation-direct-scoring-v1",
                    "economy": self.config.ai.economy_mode,
                    "temperature": self.config.ai.temperature,
                    "languages": self.config.ai.languages,
                    "categories": self._analysis_categories(),
                    "base_url": self.config.ai.base_url,
                    "scorer": f"{self.config.ai.provider.value}:{self.config.ai.model}",
                }, sort_keys=True).encode()).hexdigest(),
            )
        return self._analysis_cache

    def _source_tier(self, item: ContentItem) -> str:
        """primary / original / secondary, from filtering.source_tiers."""
        if item.source_type in (SourceType.GITHUB, SourceType.EDITORIAL):
            return "primary"  # Releases and editor picks are first-hand.
        return self.config.filtering.source_tier(self._sub_source_label(item))

    def _preferred_first(self, group: List[int], items: List[ContentItem]) -> List[int]:
        """Put the copy of a story worth showing first.

        Among copies scoring within one point of the best, a first-hand
        source beats original reporting, which beats a rewrite; then the
        higher score, then the earlier report.
        """
        best = max((items[index].ai_score or 0) for index in group)
        rank = {tier: position for position, tier in enumerate(SOURCE_TIERS)}

        def key(index: int):
            item = items[index]
            score = item.ai_score or 0
            close = score >= best - 1.0
            return (
                not close,
                rank[self._source_tier(item)],
                -score,
                item.published_at,
                index,
            )

        chosen = min(group, key=key)
        return [chosen, *(index for index in group if index != chosen)]

    @staticmethod
    def _sub_source_label(item: ContentItem) -> str:
        """Return a human-readable sub-source label for an item."""
        meta = item.metadata
        if meta.get("subreddit"):
            return f"r/{meta['subreddit']}"
        if meta.get("feed_name"):
            return meta["feed_name"]
        if meta.get("channel"):
            return f"@{meta['channel']}"
        if meta.get("period") and meta.get("repo"):
            return f"ossinsight:{meta.get('primary_language', 'all')}"
        if meta.get("repo"):
            return meta["repo"]
        if meta.get("watchlist"):
            return meta["watchlist"]
        if meta.get("source_name"):
            return meta["source_name"]
        if meta.get("gn_query"):
            return f"google_news:{meta['gn_query']}"
        if meta.get("domain"):
            return meta["domain"]
        return item.author or "unknown"

    def _rescue_low_signal_items(
        self,
        items: List[ContentItem],
        *,
        limit: int,
        max_per_source: int = 2,
    ) -> List[ContentItem]:
        """Pick the highest-scored analyzed items for a low-signal edition.

        Used only when nothing reached the score threshold, so the edition
        publishes a short ranked digest instead of an empty page. Diversity
        is kept with a small per-source cap.
        """
        scored = sorted(
            (item for item in items if item.ai_score is not None),
            key=lambda item: item.ai_score or 0,
            reverse=True,
        )
        rescued: List[ContentItem] = []
        per_source: Dict[str, int] = defaultdict(int)
        for item in scored:
            source_key = (
                f"{item.source_type.value}/{self._sub_source_label(item)}"
            )
            if per_source[source_key] >= max_per_source:
                continue
            rescued.append(item)
            per_source[source_key] += 1
            if len(rescued) >= limit:
                break
        return rescued

    def _source_breakdown(self, items: List[ContentItem]) -> Dict[str, int]:
        """Count items by the source key used by digest diversity limits."""
        counts: Dict[str, int] = defaultdict(int)
        for item in items:
            counts[
                f"{item.source_type.value}/{self._sub_source_label(item)}"
            ] += 1
        return dict(sorted(counts.items()))

    def _group_breakdown(self, items: List[ContentItem]) -> Dict[str, int]:
        """Count items by configured quota group using display labels."""
        groups = self.config.filtering.category_groups
        category_to_group: Dict[str, str] = {}
        for group_key, group in groups.items():
            for category in group.categories:
                category_to_group.setdefault(category, group_key)

        counts: Dict[str, int] = defaultdict(int)
        default_group = self.config.filtering.default_group
        for item in items:
            category = item.metadata.get("category")
            group_key = (
                category_to_group.get(category, default_group)
                if isinstance(category, str)
                else default_group
            )
            group = groups.get(group_key)
            label = group.name or group_key if group is not None else group_key
            counts[label] += 1
        return dict(sorted(counts.items()))

    def merge_cross_source_duplicates(self, items: List[ContentItem]) -> List[ContentItem]:
        """Merge items that point to the same URL from different sources.

        This is a stable stage helper for integrations such as MCP.

        Keeps the item with the richest content and combines metadata.

        Args:
            items: Items to deduplicate

        Returns:
            List[ContentItem]: Deduplicated items
        """
        # Group by normalized URL
        url_groups: Dict[tuple[str, str, str, str, Optional[int], str, str], List[ContentItem]] = {}
        for item in items:
            key = _deduplication_url_key(str(item.url))
            url_groups.setdefault(key, []).append(item)

        merged = []
        for group in url_groups.values():
            group_copies = [item.model_copy(deep=True) for item in group]
            if len(group) == 1:
                merged.append(group_copies[0])
                continue

            # Pick the item with the richest content as primary
            primary = max(group_copies, key=lambda x: len(x.content or ""))

            # Merge metadata and source info from other items
            all_sources: List[str] = []
            for item in group_copies:
                label = self._provenance_label(item)
                if label not in all_sources:
                    all_sources.append(label)
                # Merge metadata (engagement, discussion, etc.)
                for mk, mv in item.metadata.items():
                    if mk not in primary.metadata or not primary.metadata[mk]:
                        primary.metadata[mk] = mv

                # Append content (e.g., comments from another source)
                if item is not primary and item.content:
                    if primary.content and item.content not in primary.content:
                        primary.content = (primary.content or "") + f"\n\n--- From {item.source_type.value} ---\n" + item.content

            primary.metadata["merged_sources"] = all_sources
            merged.append(primary)

        return merged

    def _distinct_daily_events(self, items: List[ContentItem]) -> List[ContentItem]:
        """Keep the newest story per known event before quota selection.

        Event timelines retain all updates; the daily ranking needs only the
        latest state. Editorial picks stay pinned and are never auto-removed.
        """
        known, updates_by_event = legacy_story_assignments()
        representatives = {}
        for item in items:
            if item.id in known:
                item.metadata["event_id"], item.metadata["event_update_id"] = known[item.id]
            if item.metadata.get("event_id") in updates_by_event:
                item.metadata["event_updates"] = updates_by_event[item.metadata["event_id"]]
            key = item.metadata.get("event_id")
            if not key or item.source_type == SourceType.EDITORIAL:
                continue
            previous = representatives.get(key)
            if previous is None or item.published_at > previous.published_at:
                representatives[key] = item
        result = []
        emitted = set()
        for item in items:
            key = item.metadata.get("event_id")
            if not key or item.source_type == SourceType.EDITORIAL:
                result.append(item)
                continue
            primary = representatives[key]
            # Different updates are not independent confirmations of the
            # latest development; do not inflate the source count.
            if item is not primary and item.metadata.get("event_update_id") == primary.metadata.get("event_update_id"):
                self._record_confirming_source(primary, item)
            if key not in emitted:
                result.append(primary)
                emitted.add(key)
        return result

    def merge_event_update_duplicates(self, items: List[ContentItem]) -> List[ContentItem]:
        """One feed entry per confirmed event update, regardless of AI dedup."""
        result: List[ContentItem] = []
        seen: dict[tuple[str, str], ContentItem] = {}
        for item in items:
            key = (item.metadata.get("event_id"), item.metadata.get("event_update_id"))
            if all(key) and key in seen:
                self._record_confirming_source(seen[key], item)
                continue
            if all(key):
                seen[key] = item
            result.append(item)
        return result

    def _provenance_label(self, item: ContentItem) -> str:
        """Name the outlet behind an item, falling back to its source type."""
        label = self._sub_source_label(item)
        if not label or label == "unknown":
            return item.source_type.value
        return label

    def _record_confirming_source(
        self,
        primary: ContentItem,
        duplicate: ContentItem,
    ) -> None:
        """Add the duplicate's outlet to the primary's confirming sources."""
        sources = primary.metadata.get("merged_sources")
        if not isinstance(sources, list):
            sources = []
        merged = list(sources) or [self._provenance_label(primary)]
        for label in (
            duplicate.metadata.get("merged_sources")
            if isinstance(duplicate.metadata.get("merged_sources"), list)
            else [self._provenance_label(duplicate)]
        ):
            if label and label not in merged:
                merged.append(label)
        primary.metadata["merged_sources"] = merged

    async def merge_topic_duplicates(
        self,
        items: List[ContentItem],
        *,
        log: bool = True,
        daily_events: bool = False,
        exhaustive: bool = False,
    ) -> List[ContentItem]:
        """Merge items covering the same topic using AI semantic deduplication.

        This is a stable stage helper for integrations such as MCP.

        Compare bounded local clusters, retrying invalid responses once.
        Items must already be sorted by ai_score descending so that the first
        item in each duplicate group is always the highest-scored one.
        Content (comments) from duplicate items is merged into the primary.

        Stop publication if comparisons remain unavailable after retry.
        """
        if len(items) <= 1:
            return items

        started = time.perf_counter()
        original_items = items
        prints = [
            fingerprint(
                title_zh=str(item.metadata.get("title_zh") or ""),
                title_en=str(item.metadata.get("title_en") or item.title),
                summary_zh=str(item.metadata.get("detailed_summary_zh") or ""),
                summary_en=str(item.ai_summary or ""),
                tags=item.ai_tags,
            )
            for item in items
        ]
        parent = list(range(len(items)))

        def find(index: int) -> int:
            while parent[index] != index:
                parent[index] = parent[parent[index]]
                index = parent[index]
            return index

        def union(left: int, right: int) -> None:
            left_root, right_root = find(left), find(right)
            if left_root != right_root:
                parent[right_root] = left_root

        for left in range(len(items)):
            for right in range(left + 1, len(items)):
                if exhaustive or same_thread(prints[left], prints[right]):
                    union(left, right)
        group_sizes: Dict[int, int] = defaultdict(int)
        for index in range(len(items)):
            group_sizes[find(index)] += 1
        candidate_indices = [
            index for index in range(len(items)) if group_sizes[find(index)] > 1
        ]
        if not candidate_indices:
            self._set_timing("topic_dedup", started)
            return items
        items = [items[index] for index in candidate_indices]
        if self.last_run_report is not None:
            self.last_run_report.set_metric(
                "daily_event_dedup_ai_candidates" if daily_events else "topic_dedup_ai_candidates", len(items)
            )

        from .ai.topic_dedup import duplicate_groups as compare_duplicates
        from .ai.prompts import DAILY_EVENT_DEDUP_SYSTEM, TOPIC_DEDUP_SYSTEM

        clusters: Dict[int, List[int]] = defaultdict(list)
        for local, original in enumerate(candidate_indices):
            clusters[find(original)].append(local)
        duplicate_groups = await compare_duplicates(
            create_ai_client(self.config.ai), items, list(clusters.values()),
            system=DAILY_EVENT_DEDUP_SYSTEM if daily_events else TOPIC_DEDUP_SYSTEM,
            cache=self._result_cache(),
        )
        if daily_events:
            duplicate_groups = [
                sorted(group, key=lambda index: items[index].published_at, reverse=True)
                for group in duplicate_groups
            ]
        else:
            # Same story from several outlets: show the first-hand or
            # original report, not whichever rewrite was fetched first.
            duplicate_groups = [
                self._preferred_first(group, items)
                for group in duplicate_groups
                if isinstance(group, list)
                and len(group) > 1
                and all(isinstance(i, int) and 0 <= i < len(items) for i in group)
            ]

        if not duplicate_groups:
            self._set_timing("topic_dedup", started)
            return original_items

        # Build a set of indices to drop (all non-primary duplicates)
        drop_indices: set[int] = set()
        for group in duplicate_groups:
            if not isinstance(group, list) or len(group) < 2:
                continue
            primary_idx = group[0]
            if primary_idx < 0 or primary_idx >= len(items):
                continue
            primary = items[primary_idx]
            for dup_idx in group[1:]:
                if not isinstance(dup_idx, int) or dup_idx < 0 or dup_idx >= len(items):
                    continue
                if dup_idx == primary_idx:
                    continue
                dup = items[dup_idx]
                # Record that another outlet independently carried the story.
                # Most duplicates are the same event under different URLs, so
                # this — not URL-level dedup — is what makes the provenance
                # badge meaningful.
                if not daily_events:
                    self._record_confirming_source(primary, dup)
                # Merge comments/content from the duplicate into the primary
                if dup.content and not daily_events:
                    if not primary.content or dup.content not in primary.content:
                        label = dup.source_type.value
                        primary.content = (primary.content or "") + f"\n\n--- From {label} ---\n{dup.content}"
                if log:
                    self.console.print(
                        f"   [dim]dedup: keep [{primary_idx}] {primary.title}[/dim]\n"
                        f"   [dim]       drop [{dup_idx}] {dup.title}[/dim]"
                    )
                drop_indices.add(dup_idx)

        dropped_ids = {id(items[index]) for index in drop_indices}
        self._set_timing("topic_dedup", started)
        return [item for item in original_items if id(item) not in dropped_ids]

    async def _audit_daily_ranking(
        self, pool: List[ContentItem], selection: BalancedDigestResult,
    ) -> tuple[List[ContentItem], BalancedDigestResult]:
        """Audit every selected pair, then recheck any quota-safe refill.

        At most three passes; the last pass keeps only checked survivors.
        Never infer duplicates merely from an entity name or a local cluster.
        """
        pool = list(pool)
        removed = 0
        passes = 0
        for attempt in range(3):
            before = selection.items
            if len(before) <= 1:
                break
            if len(before) > 24:
                raise RuntimeError("Daily ranking audit exceeds 24-item safety bound")
            passes += 1
            checked = self._distinct_daily_events(
                await self.merge_topic_duplicates(
                    before, daily_events=True, exhaustive=True,
                )
            )
            survivors = {id(item) for item in checked}
            dropped = {id(item) for item in before} - survivors
            if not dropped:
                break
            removed += len(dropped)
            pool = [item for item in pool if id(item) not in dropped]
            # Each refill is checked on the next pass. At the budget boundary
            # publish a short, checked edition rather than unchecked backfill.
            selection = self.apply_balanced_digest(
                checked if attempt == 2 else pool,
                log=False, allow_primary_borrowing=True, fill_to_minimum=True,
            )
        if self.last_run_report is not None:
            report = self.last_run_report
            report.set_metric("ranking_audit_removed", report.metrics.get("ranking_audit_removed", 0) + removed)
            report.set_metric("ranking_audit_passes", report.metrics.get("ranking_audit_passes", 0) + passes)
        return pool, selection

    async def filter_items(
        self,
        items: List[ContentItem],
        *,
        threshold: Optional[float] = None,
        topic_dedup: bool = True,
        apply_balance: bool = True,
        log: bool = True,
        dedup_context: Optional[List[ContentItem]] = None,
    ) -> FilteringPipelineResult:
        """Apply score thresholding, published-history dedup, and balancing."""
        effective_threshold = (
            threshold
            if threshold is not None
            else self.config.filtering.ai_score_threshold
        )
        threshold_items = [
            item
            for item in items
            if item.ai_score is not None and item.ai_score >= effective_threshold
            and not item.metadata.get("chinese_invalid")
        ]
        threshold_items.sort(key=lambda item: item.ai_score or 0, reverse=True)

        if log:
            self.console.print(
                f"⭐️ {len(threshold_items)} items scored ≥ {effective_threshold}\n"
            )

        deduped_items = threshold_items
        if topic_dedup and deduped_items:
            context_items = dedup_context or []
            if context_items:
                published_identities = {
                    item_identity(item) for item in context_items
                }
                deduped_items = [
                    item
                    for item in deduped_items
                    if item_identity(item) not in published_identities
                ]

                if deduped_items:
                    # Published context comes first so the existing topic
                    # deduplicator keeps the first publication of an event.
                    context_copies = [
                        item.model_copy(update={"ai_score": 11.0}, deep=True)
                        for item in context_items
                    ]
                    combined = [*context_copies, *deduped_items]
                    merged = await self.merge_topic_duplicates(
                        combined,
                        log=log,
                    )
                    survivors = {id(item) for item in merged}
                    deduped_items = [
                        item for item in deduped_items if id(item) in survivors
                    ]
            else:
                deduped_items = await self.merge_topic_duplicates(
                    deduped_items,
                    log=log,
                )
        topic_dedup_removed = len(threshold_items) - len(deduped_items)

        if log and topic_dedup_removed:
            self.console.print(
                f"🧹 Removed {topic_dedup_removed} topic duplicates "
                f"→ {len(deduped_items)} unique items\n"
            )

        balanced_digest = (
            self.apply_balanced_digest(deduped_items, log=log)
            if apply_balance
            else BalancedDigestResult(items=deduped_items)
        )
        return FilteringPipelineResult(
            items=balanced_digest.items,
            threshold_count=len(threshold_items),
            topic_dedup_count=len(deduped_items),
            topic_dedup_removed=topic_dedup_removed,
            balanced_digest=balanced_digest,
        )

    def apply_balanced_digest(
        self,
        items: List[ContentItem],
        *,
        log: bool = True,
        allow_primary_borrowing: bool = False,
        fill_to_minimum: bool = False,
    ) -> BalancedDigestResult:
        """Apply configured category quotas and the final item cap.

        Categories are read from ``item.metadata["category"]``. If a category
        appears in more than one configured group, the first group in config
        order wins.
        """
        filtering = self.config.filtering
        groups = filtering.category_groups
        max_items = filtering.max_items

        if not groups and max_items is None:
            return BalancedDigestResult(items=items)

        sorted_items = sorted(
            items,
            key=lambda item: item.ai_score or 0,
            reverse=True,
        )

        category_to_group: Dict[str, str] = {}
        duplicate_categories: List[str] = []
        for group_key, group in groups.items():
            for category in group.categories:
                if category in category_to_group:
                    if category_to_group[category] != group_key:
                        duplicate_categories.append(category)
                    continue
                category_to_group[category] = group_key

        if log:
            for category in sorted(set(duplicate_categories)):
                first_group = category_to_group[category]
                self.console.print(
                    f"[yellow]Warning: category '{category}' is configured in multiple "
                    f"groups; using '{first_group}'.[/yellow]"
                )

        selected: List[tuple[ContentItem, str]] = []
        selected_object_ids: set[int] = set()
        group_counts: Dict[str, int] = defaultdict(int)
        source_counts: Dict[str, int] = defaultdict(int)
        category_deferred_ids: set[int] = set()
        source_deferred_ids: set[int] = set()
        default_group = filtering.default_group

        def group_for(item: ContentItem) -> str:
            category = item.metadata.get("category")
            return (
                category_to_group.get(category, default_group)
                if isinstance(category, str)
                else default_group
            )

        def source_for(item: ContentItem) -> str:
            # One outlet, one budget: CoinDesk via RSS and via Google News
            # share the same cap.
            return self._sub_source_label(item).strip().lower()

        tier_counts: Dict[str, int] = defaultdict(int)
        tier_scope = set(filtering.primary_groups)

        def select(
            item: ContentItem,
            group_key: str,
            *,
            group_limit: Optional[int] = None,
            enforce_group_limit: bool = True,
            enforce_source_limit: bool = True,
            enforce_tier_limit: bool = True,
        ) -> bool:
            if id(item) in selected_object_ids:
                return False
            if max_items is not None and len(selected) >= max_items:
                return False
            if enforce_group_limit:
                limit = group_limit
                if limit is None:
                    if group_key in groups:
                        limit = groups[group_key].limit
                    else:
                        limit = filtering.default_group_limit

                if limit is not None and group_counts[group_key] >= limit:
                    category_deferred_ids.add(id(item))
                    return False

            source_key = source_for(item)
            source_limit = filtering.max_items_per_source
            if (
                enforce_source_limit
                and source_limit is not None
                and source_counts[source_key] >= source_limit
            ):
                source_deferred_ids.add(id(item))
                return False
            tier = self._source_tier(item)
            tier_limit = filtering.source_tier_limits.get(tier)
            # The tier cap is about the crypto track, where outlets rewrite
            # one another; AI and policy keep their own quotas.
            if (
                enforce_source_limit
                and enforce_tier_limit
                and tier_limit is not None
                and (not tier_scope or group_key in tier_scope)
                and tier_counts[tier] >= tier_limit
            ):
                source_deferred_ids.add(id(item))
                return False

            selected.append((item, group_key))
            selected_object_ids.add(id(item))
            group_counts[group_key] += 1
            source_counts[source_key] += 1
            if not tier_scope or group_key in tier_scope:
                tier_counts[tier] += 1
            return True

        primary_groups = set(filtering.primary_groups)
        primary_minimum = filtering.primary_group_min_items or 0
        if primary_groups and primary_minimum:
            # First with the rewrite cap; if original and first-hand reports
            # cannot reach the crypto target, rewrites make up the rest.
            for enforce_tier in (True, False):
                for item in sorted_items:
                    if sum(group_counts[g] for g in primary_groups) >= primary_minimum:
                        break
                    group_key = group_for(item)
                    if group_key not in primary_groups:
                        continue
                    select(item, group_key, enforce_tier_limit=enforce_tier)

        # Reserved slots (e.g. AI 3 of 14) are filled before the open ranking
        # so a busy crypto day cannot crowd a whole track out of the edition.
        for group_key, group in groups.items():
            if not group.min_items:
                continue
            for item in sorted_items:
                if group_counts[group_key] >= group.min_items:
                    break
                if group_for(item) == group_key:
                    select(item, group_key)

        for item in sorted_items:
            select(item, group_for(item))

        borrowed_count = 0
        borrow_limit = filtering.primary_group_borrow_limit
        if allow_primary_borrowing and primary_groups and borrow_limit is not None:
            for item in sorted_items:
                if id(item) in selected_object_ids:
                    continue
                if max_items is not None and len(selected) >= max_items:
                    break
                group_key = group_for(item)
                if group_key not in primary_groups:
                    continue
                effective_limit = max(groups[group_key].limit, borrow_limit)
                if select(item, group_key, group_limit=effective_limit):
                    borrowed_count += 1

        minimum_fill_count = 0
        minimum_display = filtering.minimum_display_items
        if fill_to_minimum and minimum_display is not None:
            fill_target = (
                min(minimum_display, max_items)
                if max_items is not None
                else minimum_display
            )
            for item in sorted_items:
                if len(selected) >= fill_target:
                    break
                if id(item) in selected_object_ids:
                    continue
                group_key = group_for(item)
                # AI and policy caps are hard limits. Only the Crypto primary
                # track may exceed its normal/borrowed cap to avoid a short
                # edition, and every recovery item has already cleared score
                # and topic/history deduplication.
                recovery_limit: Optional[int] = None
                if group_key not in primary_groups:
                    if group_key in groups:
                        recovery_limit = groups[group_key].limit
                    else:
                        recovery_limit = filtering.default_group_limit
                    if (
                        recovery_limit is not None
                        and group_counts[group_key] >= recovery_limit
                    ):
                        category_deferred_ids.add(id(item))
                        continue
                if select(
                    item,
                    group_key,
                    group_limit=recovery_limit,
                    enforce_group_limit=group_key not in primary_groups,
                    enforce_source_limit=False,
                ):
                    minimum_fill_count += 1

        selected.sort(
            key=lambda pair: pair[0].ai_score or 0,
            reverse=True,
        )

        final_counts: Dict[str, int] = defaultdict(int)
        for _, group_key in selected:
            final_counts[group_key] += 1

        group_limits: Dict[str, Optional[int]] = {
            group_key: group.limit for group_key, group in groups.items()
        }
        if allow_primary_borrowing and borrow_limit is not None:
            for group_key in primary_groups:
                group_limits[group_key] = max(
                    groups[group_key].limit,
                    borrow_limit,
                )
        group_limits.setdefault(default_group, filtering.default_group_limit)

        if log:
            self.console.print(
                f"⚖️ Balanced digest selected {len(selected)}/{len(items)} items"
            )
            for group_key, group in groups.items():
                label = group.name or group_key
                effective_limit = group_limits[group_key]
                self.console.print(
                    f"      • {label}: "
                    f"{final_counts.get(group_key, 0)}/{effective_limit}"
                )
            if (
                final_counts.get(default_group, 0)
                or filtering.default_group_limit is not None
            ):
                limit_label = (
                    str(filtering.default_group_limit)
                    if filtering.default_group_limit is not None
                    else "unlimited"
                )
                self.console.print(
                    f"      • {default_group}: "
                    f"{final_counts.get(default_group, 0)}/{limit_label}"
                )
            self.console.print("")

        return BalancedDigestResult(
            items=[item for item, _ in selected],
            enabled=True,
            group_counts=dict(final_counts),
            group_limits=group_limits,
            duplicate_categories=sorted(set(duplicate_categories)),
            borrowed_count=borrowed_count,
            category_limit_deferred=len(category_deferred_ids),
            source_limit_deferred=len(source_deferred_ids),
            minimum_fill_count=minimum_fill_count,
        )

    async def _analyze_content(
        self, items: List[ContentItem], *, edition_window: EditionWindow | None = None,
        preselected: bool = False,
    ) -> List[ContentItem]:
        """Reuse valid results before paying for prefiltering unseen inputs."""
        started = time.perf_counter()
        cache = self._result_cache()
        cached, misses = split_cached(cache, items, stage="analysis") if cache else ([], list(items))
        limit = self.config.ai.prefilter_max_candidates
        # Reserve a quarter of the budget for new inputs even if old cache
        # hits fill the pool. Final scoring, not cache status, determines rank.
        new_budget = max(limit // 4, limit - len(cached))
        ai_client = create_ai_client(self.config.ai) if misses else None
        if not preselected and self.config.ai.prefilter_enabled and len(misses) > new_budget:
            self.console.print(f"AI prefilter started: {len(misses)} candidates")
            result = await ContentPrefilter(
                ai_client, batch_size=self.config.ai.prefilter_batch_size,
                cache=cache,
            ).select(misses, maximum=new_budget)
            misses = result.items
            self.console.print(
                f"AI prefilter complete: {len(misses)} selected, "
                f"{result.failed_batches} failed batches"
            )
            self._record_prefilter(result)
        if self.last_run_report:
            for key, value in {"analysis_cache_hits": len(cached), "analysis_cache_misses": len(misses)}.items():
                self.last_run_report.set_metric(key, self.last_run_report.metrics.get(key, 0) + value)
        if misses:
            self.console.print(
                f"AI analysis started: {len(misses)} items, "
                f"{self.config.ai.provider.value}:{self.config.ai.model}"
            )
            await ContentAnalyzer(
                ai_client, allowed_categories=self._analysis_categories(),
                edition_window=edition_window,
            ).analyze_batch(misses)
            self.console.print(f"AI analysis complete: {len(misses)} items")
            if cache:
                for item in misses:
                    cache.store_analysis(item)
                cache.save()
        selected = [*cached, *misses]
        if self.last_run_report is not None:
            score_models = defaultdict(int)
            for item in selected:
                if item.ai_score is not None:
                    score_models[str(item.metadata.get("score_model") or "unknown")] += 1
            self.last_run_report.set_breakdown("score_models", dict(score_models))
        if self.config.ai.prefilter_enabled:
            selected.sort(key=lambda item: (item.ai_score or 0, item.published_at, item.id), reverse=True)
            selected = selected[:limit]
        self._set_timing("analysis", started)
        return selected

    def _analysis_categories(self) -> List[str]:
        """Return the configured leaf categories accepted from AI analysis."""
        return sorted(
            {
                category
                for group in self.config.filtering.category_groups.values()
                for category in group.categories
            }
        )
