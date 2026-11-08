import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

from tenacity import wait_none

from src.ai.enricher import ContentEnricher
from src.ai.prompts import CONTENT_ENRICHMENT_SYSTEM
from src.models import ContentItem, SourceType


def test_enrichment_retry_reports_final_type_without_provider_response(monkeypatch, capsys):
    calls = []
    async def complete(**kwargs):
        calls.append(kwargs["system"])
        if kwargs["system"].startswith("You are a translator."):
            return '{"title_zh":"安全更新","summary_zh":"项目发布安全更新。"}'
        raise TimeoutError("private-provider-response-must-not-leak")

    monkeypatch.setattr(ContentEnricher._enrich_item.retry, "wait", wait_none())
    client = SimpleNamespace(complete=complete, config=SimpleNamespace(enrichment_concurrency=1))
    item = ContentItem(id="diagnostic-story", title="Project releases security update",
        url="https://example.com/news", source_type=SourceType.RSS,
        published_at=datetime(2026, 11, 8, tzinfo=timezone.utc))
    asyncio.run(ContentEnricher(client).enrich_batch([item]))
    assert calls.count(CONTENT_ENRICHMENT_SYSTEM) == 3
    assert item.metadata["enrichment_status"] == "translation_only"
    output = capsys.readouterr().out
    assert "TimeoutError" in output
    assert "private-provider-response" not in output
    assert "AI enrichment processed: 1/1" in output
