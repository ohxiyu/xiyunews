"""Tests for low-signal rescue selection and edition header extras."""

from datetime import datetime, timezone
from types import SimpleNamespace

from rich.console import Console

from src.models import ContentItem, FilteringConfig, SourceType
from src.orchestrator import BMTNewsOrchestrator


def make_item(
    item_id: str,
    score: float | None,
    *,
    feed_name: str = "Example Feed",
) -> ContentItem:
    return ContentItem(
        id=item_id,
        source_type=SourceType.RSS,
        title=f"Title {item_id}",
        url=f"https://example.com/{item_id}",
        published_at=datetime.now(timezone.utc),
        ai_score=score,
        metadata={"feed_name": feed_name, "category": "crypto-markets"},
    )


def make_orchestrator() -> BMTNewsOrchestrator:
    orchestrator = BMTNewsOrchestrator.__new__(BMTNewsOrchestrator)
    orchestrator.config = SimpleNamespace(filtering=FilteringConfig())
    orchestrator.console = Console(record=True)
    return orchestrator


def test_rescue_picks_highest_scores_with_source_diversity() -> None:
    items = [
        make_item("a", 6.5, feed_name="Feed A"),
        make_item("b", 6.0, feed_name="Feed A"),
        make_item("c", 5.5, feed_name="Feed A"),
        make_item("d", 5.0, feed_name="Feed B"),
        make_item("e", None, feed_name="Feed C"),
    ]
    rescued = make_orchestrator()._rescue_low_signal_items(items, limit=3)
    assert [item.id for item in rescued] == ["a", "b", "d"]


def test_rescue_respects_limit() -> None:
    items = [make_item(str(i), 6.0 - i * 0.1, feed_name=f"F{i}") for i in range(8)]
    rescued = make_orchestrator()._rescue_low_signal_items(items, limit=5)
    assert len(rescued) == 5
