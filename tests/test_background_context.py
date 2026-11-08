"""Background grounding and bilingual parity; no live searches or model calls."""
import asyncio
import json
from datetime import datetime, timezone

import pytest

from src.ai.enricher import ContentEnricher
from src.ai.prompts import CONCEPT_EXTRACTION_SYSTEM, CONTENT_ENRICHMENT_SYSTEM
from src.ai.result_cache import AnalysisResultCache
from src.models import ContentItem, SourceType


def story():
    return ContentItem(id="context", title="Exchange announces a custody change",
        url="https://example.com/news", source_type=SourceType.RSS,
        content="The exchange holds customer funds and announced a custody change.",
        published_at=datetime(2026, 11, 8, tzinfo=timezone.utc))


class Client:
    def __init__(self, queries, background=None):
        self.queries, self.background, self.calls = queries, background, []

    async def complete(self, **kwargs):
        self.calls.append(kwargs)
        if kwargs["system"] == CONCEPT_EXTRACTION_SYSTEM:
            if isinstance(self.queries, Exception):
                raise self.queries
            return json.dumps({"queries": self.queries})
        assert kwargs["system"] == CONTENT_ENRICHMENT_SYSTEM
        return json.dumps({"title_zh": "交易所宣布托管变更", "whats_new_en": "A custody change was announced.",
            "whats_new_zh": "交易所宣布托管变更。", "background_en": "The exchange holds customer funds.",
            "background_zh": "该交易所托管客户资金。",
            "sources": ["https://example.com/custody", "https://invented.invalid/context"],
            **(self.background or {})})


@pytest.mark.parametrize("queries", [[], "malformed", [None, " "], TimeoutError("not logged")])
def test_empty_or_failed_extraction_still_searches_and_preserves_supported_context(monkeypatch, queries):
    client = Client(queries)
    enricher, item, searches = ContentEnricher(client), story(), []

    async def search(query, max_results=3):
        searches.append(query)
        return [{"title": "Custody documentation", "url": "https://example.com/custody",
            "body": "The exchange holds customer funds."}]

    monkeypatch.setattr(enricher, "_web_search", search)
    asyncio.run(enricher._enrich_item(item))
    assert searches == [item.title + " background context"]
    assert len(client.calls) == 2  # No additional background-repair model call.
    assert "The exchange holds customer funds." in client.calls[1]["user"]
    assert item.metadata["background_zh"] == "该交易所托管客户资金。"
    assert item.metadata["background_en"] == "The exchange holds customer funds."
    assert item.metadata["sources"] == [{"url": "https://example.com/custody", "title": "Custody documentation"}]


def test_queries_are_unique_bounded_strings_and_do_not_add_fallback(monkeypatch):
    client = Client([None, " custody   policy ", "CUSTODY policy", "exchange history", "official docs", "extra"])
    enricher, searches = ContentEnricher(client), []

    async def search(query, max_results=3):
        searches.append(query)
        return []

    monkeypatch.setattr(enricher, "_web_search", search)
    asyncio.run(enricher._enrich_item(story()))
    assert searches == ["custody policy", "exchange history", "official docs"]


@pytest.mark.parametrize("background,error", [
    ({"background_zh": " "}, "incomplete_bilingual_background"),
    ({"background_en": ""}, "incomplete_bilingual_background"),
    ({"background_zh": {"text": "not the agreed schema"}}, "invalid_background"),
])
def test_partial_or_non_text_background_is_not_accepted_as_complete(monkeypatch, background, error):
    enricher = ContentEnricher(Client([], background))
    async def search(*_args, **_kwargs):
        return []
    monkeypatch.setattr(enricher, "_web_search", search)
    # Exercise one attempt without the production retry delays.
    with pytest.raises(ValueError, match=error):
        asyncio.run(ContentEnricher._enrich_item.__wrapped__(enricher, story()))


def test_no_reliable_background_can_remain_empty_without_placeholder(monkeypatch):
    enricher = ContentEnricher(Client([], {"background_en": "", "background_zh": ""}))
    async def search(*_args, **_kwargs):
        return []
    monkeypatch.setattr(enricher, "_web_search", search)
    item = story()
    asyncio.run(enricher._enrich_item(item))
    assert not item.metadata.get("background_zh")
    assert not item.metadata.get("background_en")
    assert item.metadata["detailed_summary_zh"] == "交易所宣布托管变更。"


@pytest.mark.parametrize("change", ["model", "query_prompt", "writing_prompt"])
def test_old_background_cache_invalidates_on_model_or_context_prompt_change(tmp_path, monkeypatch, change):
    from src.ai import prompts
    path, item = tmp_path / "cache.json", story()
    item.metadata.update(background_zh="旧背景", background_en="Old context")
    cache = AnalysisResultCache(path, model="siliconflow:Qwen/Qwen3.5-27B")
    cache.store_enrichment(item)
    cache.save()
    if change == "query_prompt":
        monkeypatch.setattr(prompts, "CONCEPT_EXTRACTION_USER", "New query policy: {title}")
    if change == "writing_prompt":
        monkeypatch.setattr(prompts, "CONTENT_ENRICHMENT_SYSTEM", "New context policy")
    model = "siliconflow:deepseek-ai/DeepSeek-V3.2" if change == "model" else cache.model
    assert not AnalysisResultCache(path, model=model).restore_enrichment(story())
