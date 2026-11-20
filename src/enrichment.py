"""Expand only the selected daily stories, reusing grounded enrichment cache."""
from __future__ import annotations
import time
from typing import List
from .models import ContentItem
from .ai.client import create_ai_client
from .ai.enricher import ContentEnricher
from .ai.result_cache import split_cached



class EnrichmentPipeline:
    async def _enrich_important_items(self, items: List[ContentItem]) -> None:
        """Enrich items with background knowledge (2nd AI pass).

        For each item that passed the score threshold, call AI to generate
        background knowledge based on the item's actual content.

        Args:
            items: Important items to enrich (modified in-place)
        """
        if not items:
            return

        started = time.perf_counter()
        self.console.print("📚 Enriching with background knowledge...")
        cache = self._result_cache()
        cached: list[ContentItem] = []
        misses = items
        if cache is not None:
            cached, misses = split_cached(cache, items, stage="enrichment")
            if self.last_run_report is not None:
                report = self.last_run_report
                report.set_metric(
                    "enrichment_cache_hits",
                    report.metrics.get("enrichment_cache_hits", 0) + len(cached),
                )
                report.set_metric(
                    "enrichment_cache_misses",
                    report.metrics.get("enrichment_cache_misses", 0) + len(misses),
                )
        if not misses:
            self.console.print(f"   Reused enrichment for {len(cached)} items\n")
            self._set_timing("enrichment", started)
            return
        ai_client = create_ai_client(self.config.ai)
        enricher = ContentEnricher(ai_client, languages=["zh"])
        enrichment_inputs = [item.model_copy(deep=True) for item in misses]
        await enricher.enrich_batch(misses)
        blocked_status = next((item.metadata.get("provider_account_http_status") for item in misses if item.metadata.get("provider_account_http_status")), None)
        if blocked_status and self.last_run_report is not None:
            self.last_run_report.set_metric("provider_account_http_status", blocked_status)
            self.last_run_report.add_alert("warning", "ai_account_blocked", f"AI账户HTTP {blocked_status}，停止调用；仅保留合格中文摘要。")
        if cache is not None:
            for item, input_item in zip(misses, enrichment_inputs):
                cache.store_enrichment(item, input_item=input_item)
            cache.save()
        self.console.print(
            f"   Enriched {len(misses)} items; reused {len(cached)}\n"
        )
        self._set_timing("enrichment", started)
