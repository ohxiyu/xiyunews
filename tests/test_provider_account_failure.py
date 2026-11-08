import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from tenacity import wait_none

from src.ai.analyzer import ContentAnalyzer
from src.ai.client import OpenAIClient
from src.ai.errors import ProviderAccountError, account_error
from src.models import AIConfig, ContentItem, SourceType


class ProviderFailure(Exception):
    def __init__(self, status):
        self.status_code = status
        super().__init__("private-provider-response-must-not-leak")


def items(count):
    return [ContentItem(id=f"rss:{i}", source_type=SourceType.RSS, title=f"Story {i}",
                        url=f"https://example.com/{i}",
                        published_at=datetime(2026, 11, 8, tzinfo=timezone.utc))
            for i in range(count)]


@pytest.mark.parametrize("status,reason", [(401, "authentication_failed"),
    (402, "insufficient_balance"), (403, "permission_denied")])
def test_account_error_stops_batch_without_zero_scores(status, reason):
    calls = []
    async def complete(**kwargs):
        calls.append(kwargs)
        raise ProviderFailure(status)
    client = SimpleNamespace(complete=complete, config=SimpleNamespace(
        throttle_sec=0, analysis_concurrency=1))
    batch = items(140)
    with pytest.raises(ProviderAccountError, match=reason) as caught:
        asyncio.run(ContentAnalyzer(client).analyze_batch(batch))
    assert len(calls) == 1  # Includes the real tenacity-decorated analysis path.
    assert all(item.ai_score is None for item in batch)
    assert "private-provider-response" not in str(caught.value)


def test_inflight_requests_are_cancelled_and_queue_is_not_started():
    async def scenario():
        started, cancelled = [], []
        ready = asyncio.Event()
        never = asyncio.Event()
        async def complete(**kwargs):
            index = len(started)
            started.append(index)
            if len(started) == 3:
                ready.set()
            await ready.wait()
            if index == 0:
                raise ProviderFailure(402)
            try:
                await never.wait()
            except asyncio.CancelledError:
                cancelled.append(index)
                raise
        client = SimpleNamespace(complete=complete, config=SimpleNamespace(
            throttle_sec=0, analysis_concurrency=3))
        with pytest.raises(ProviderAccountError):
            await ContentAnalyzer(client).analyze_batch(items(140))
        assert started == [0, 1, 2]
        assert sorted(cancelled) == [1, 2]
    asyncio.run(asyncio.wait_for(scenario(), timeout=10))


def test_client_latches_account_error_for_other_stages(monkeypatch):
    calls = []
    async def create(**kwargs):
        calls.append(kwargs)
        raise ProviderFailure(402)
    monkeypatch.setenv("TEST_AI_KEY", "test-only")
    monkeypatch.setattr("src.ai.client.AsyncOpenAI", lambda **kwargs: SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
    cfg = AIConfig(provider="deepseek", model="deepseek-flash", api_key_env="TEST_AI_KEY")
    async def scenario():
        client = OpenAIClient(cfg)
        for stage in ["prefilter", "analysis", "dedup"]:
            with pytest.raises(ProviderAccountError, match="insufficient_balance"):
                await client.complete(stage, "{}")
        assert len(calls) == 1
        # The latch is run-local: a fresh client can try again after account repair.
        with pytest.raises(ProviderAccountError):
            await OpenAIClient(cfg).complete("analysis", "{}")
        assert len(calls) == 2
    asyncio.run(scenario())


def test_transient_failure_still_retries_and_valid_result_is_kept(monkeypatch):
    calls = []
    async def complete(**kwargs):
        calls.append(kwargs)
        if len(calls) == 1:
            raise ProviderFailure(429)
        return '{"score":8,"reason":"new event","summary":"A report","tags":[]}'
    monkeypatch.setattr(ContentAnalyzer._analyze_item.retry, "wait", wait_none())
    batch = items(1)
    asyncio.run(ContentAnalyzer(SimpleNamespace(complete=complete)).analyze_batch(batch))
    assert len(calls) == 2
    assert batch[0].ai_score == 8


@pytest.mark.parametrize("exc", [ValueError("402 insufficient_balance"),
    ProviderFailure(429), ProviderFailure(500), SimpleNamespace(status_code=True)])
def test_untrusted_text_and_transient_status_do_not_trip_account_latch(exc):
    assert account_error(exc) is None


def test_account_failure_has_actionable_machine_readable_report():
    from src.run_report import RunReport, render_github_annotations
    report = RunReport.start(date="2026-11-08", timezone_name="Asia/Shanghai")
    report.fail(ProviderAccountError(402))
    payload = report.to_dict()
    assert payload["status"] == "failure"
    assert payload["metrics"]["provider_account_http_status"] == 402
    assert any(a["code"] == "ai_account_insufficient_balance" for a in payload["alerts"])
    assert any("充值" in line for line in render_github_annotations(payload))
