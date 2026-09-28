"""The weekly review goes to Telegram and X once per week."""

from __future__ import annotations

import asyncio
from datetime import date
from types import SimpleNamespace

from rich.console import Console

from src.archive import ArchiveRecord
from src.models import TelegramDeliveryConfig, XDeliveryConfig
from src.run_report import RunReport
from src.services.telegram_delivery import TelegramDeliveryResult, TelegramDeliveryStatus
from src.services.x_delivery import PostOutcome, _weighted_length
from src.weekly import (
    WeeklyDigest,
    build_weekly_context,
    load_week_deliveries,
    weekly_push_texts,
)

DIGEST = WeeklyDigest.model_validate({
    "throughline": {
        "title": "监管收紧与 AI 问责同周发生",
        "summary": "纽约起诉 Polymarket，澳大利亚要求 OpenAI 与 Anthropic 出席听证，监管对预测市场和 AI 代理同时加码。" * 2,
    },
    "items": [
        {"section": "continuing", "title": f"事件 {n} <b>", "change": "变化", "why_it_matters": "影响", "evidence_ids": []}
        for n in range(6)
    ],
})


def context():
    record = ArchiveRecord(date="2026-09-27", rank=1, item_id="a", url="https://example.com/a", title_zh="标题")
    return build_weekly_context([record], end=date(2026, 9, 28), days=7)


def test_push_texts_are_built_from_the_digest_only():
    telegram, x_text = weekly_push_texts(DIGEST, context(), site_url="https://bmt.news/", x_limit=280)
    assert "<b>监管收紧与 AI 问责同周发生</b>" in telegram
    assert "事件 0 &lt;b&gt;" in telegram and "事件 4" not in telegram  # top four, escaped
    assert 'href="https://bmt.news/weekly/2026-09-28/"' in telegram
    assert "http" not in x_text and _weighted_length(x_text) <= 280
    assert x_text.startswith("本周回顾")


class Telegram:
    def __init__(self):
        self.sent = []

    async def send_html(self, message, *, label):
        self.sent.append(message)
        return TelegramDeliveryResult(TelegramDeliveryStatus.SUCCESS)


class X:
    def __init__(self, kind="sent"):
        self.kind = kind
        self.posts = []

    def not_ready_reason(self):
        return ""

    async def publish_post(self, text):
        self.posts.append(text)
        return PostOutcome(self.kind, "HTTP", "777" if self.kind == "sent" else "")


def orchestrator(telegram, x):
    from src.orchestrator import BMTNewsOrchestrator

    runner = BMTNewsOrchestrator.__new__(BMTNewsOrchestrator)
    runner.console = Console(record=True)
    runner.config = SimpleNamespace(
        x_delivery=XDeliveryConfig(enabled=True, mode="drip"),
        telegram_delivery=TelegramDeliveryConfig(enabled=True),
    )
    runner.telegram_publisher = telegram
    runner.x_publisher = x
    return runner


def run(runner, tmp_path, monkeypatch):
    import src.weekly as weekly

    monkeypatch.setattr(weekly, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(weekly, "known_weeks", lambda: ["2026-09-28"])
    report = RunReport.start(date="2026-09-28", timezone_name="Asia/Shanghai", kind="weekly_review")
    asyncio.run(runner._push_weekly(DIGEST, context(), run_report=report))
    return report


def test_weekly_is_pushed_once_and_receipts_stop_a_rerun(tmp_path, monkeypatch):
    telegram, x = Telegram(), X()
    runner = orchestrator(telegram, x)
    run(runner, tmp_path, monkeypatch)
    run(runner, tmp_path, monkeypatch)
    assert len(telegram.sent) == 1 and len(x.posts) == 1
    receipts = load_week_deliveries("2026-09-28", data_root=tmp_path)
    assert receipts == {"telegram": {"status": "sent"}, "x": {"status": "sent", "tweet_id": "777", "detail": "HTTP"}}


def test_unknown_x_outcome_is_recorded_and_never_retried(tmp_path, monkeypatch):
    x = X("unknown")
    runner = orchestrator(None, x)
    report = run(runner, tmp_path, monkeypatch)
    run(runner, tmp_path, monkeypatch)
    assert len(x.posts) == 1
    assert any(alert.code == "weekly_x_unknown" for alert in report.alerts)


def test_nothing_created_on_x_may_be_retried_by_a_rerun(tmp_path, monkeypatch):
    x = X("rate_limited")
    runner = orchestrator(None, x)
    run(runner, tmp_path, monkeypatch)
    x.kind = "sent"
    run(runner, tmp_path, monkeypatch)
    assert len(x.posts) == 2
    assert load_week_deliveries("2026-09-28", data_root=tmp_path)["x"]["status"] == "sent"
