"""The glance must tell a reader what mattered in both crypto and AI."""

import asyncio
import json
from datetime import datetime, timezone

from src.ai.summarizer import generate_edition_overviews
from src.models import ContentItem, SourceType


def story(rank: int, category: str, title: str) -> ContentItem:
    return ContentItem(
        id=f"s{rank}",
        source_type=SourceType.RSS,
        title=title,
        url=f"https://example.com/{rank}",
        published_at=datetime(2026, 9, 28, tzinfo=timezone.utc),
        ai_score=8.0,
        ai_summary=f"{title} summary.",
        metadata={"category": category, "title_zh": f"{title}（中文）", "title_en": title},
    )


ITEMS = [
    story(1, "crypto-markets", "Exchange hacked"),
    story(2, "crypto-regulation", "SEC ruling"),
    story(3, "crypto-protocols", "Ethereum upgrade"),
    story(4, "ai-labs", "New frontier model"),
]


class Client:
    def __init__(self, signals):
        self.signals = signals
        self.prompts = []

    async def complete(self, **kwargs):
        self.prompts.append(kwargs)
        return json.dumps({
            language: {"headline": "今日主线。" if language == "zh" else "The day's theme.",
                       "signals": self.signals}
            for language in ("zh", "en")
        })


def run(client, items=ITEMS):
    return asyncio.run(generate_edition_overviews(client, items, date="2026-09-28", languages=["zh", "en"]))


def test_stories_are_tagged_by_track_and_rules_require_both():
    client = Client([])
    run(client)
    user, system = client.prompts[0]["user"], client.prompts[0]["system"]
    assert "1. [Crypto]" in user and "4. [AI]" in user and "2. [Policy]" in user
    assert "highest-ranked [AI] story" in system


def test_missing_ai_signal_is_filled_from_the_ai_story_title():
    signals = [
        {"label": "安全", "text": "交易所遭攻击。", "item_rank": 1},
        {"label": "监管", "text": "SEC 作出裁定。", "item_rank": 2},
        {"label": "协议", "text": "以太坊升级。", "item_rank": 3},
    ]
    result = run(Client(signals))
    zh = result["zh"].signals
    assert [signal.item_rank for signal in zh] == [1, 2, 4]
    assert zh[-1].label == "AI" and zh[-1].text == "New frontier model（中文）"
    assert result["en"].signals[-1].text == "New frontier model"


def test_signals_that_already_cover_both_tracks_are_kept():
    signals = [
        {"label": "安全", "text": "交易所遭攻击。", "item_rank": 1},
        {"label": "模型", "text": "新前沿模型发布。", "item_rank": 4},
    ]
    zh = run(Client(signals))["zh"].signals
    assert [(signal.label, signal.item_rank) for signal in zh] == [("安全", 1), ("模型", 4)]


def test_crypto_is_filled_too_and_ai_is_not_invented_when_absent():
    no_ai = ITEMS[:3]
    signals = [{"label": "监管", "text": "SEC 作出裁定。", "item_rank": 2}]
    zh = run(Client(signals), no_ai)["zh"].signals
    assert [(signal.label, signal.item_rank) for signal in zh] == [("加密", 1), ("监管", 2)]


def test_headline_only_fallback_is_left_alone():
    assert run(Client([]))["zh"].signals == ()
