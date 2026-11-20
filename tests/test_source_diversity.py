"""Rewrites of the same crypto news must not crowd out first-hand and
original reporting."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.models import CategoryGroupConfig, ContentItem, FilteringConfig, SourceType
from tests.test_balanced_digest import make_item, make_orchestrator

TIERS = {
    "primary": ["SEC Press Releases", "@binance_announcements"],
    "original": ["CoinDesk", "The Block"],
}


def test_tier_lookup_is_case_insensitive_and_defaults_to_secondary() -> None:
    filtering = FilteringConfig(source_tiers=TIERS)
    assert filtering.source_tier("coindesk") == "original"
    assert filtering.source_tier("@Binance_Announcements") == "primary"
    assert filtering.source_tier("CryptoSlate") == "secondary"
    with pytest.raises(ValidationError):
        FilteringConfig(source_tiers={"secondary": ["x"]})
    with pytest.raises(ValidationError):
        FilteringConfig(source_tier_limits={"secondary": 0})


def test_secondary_rewrites_are_capped_but_fill_a_short_edition() -> None:
    filtering = FilteringConfig(
        category_groups={"markets": CategoryGroupConfig(limit=8, categories=["markets"])},
        max_items_per_source=2,
        source_tiers=TIERS,
        source_tier_limits={"secondary": 2},
    )
    items = [
        make_item("slate-1", 9.5, "markets", feed_name="CryptoSlate"),
        make_item("decrypt-1", 9.4, "markets", feed_name="Decrypt"),
        make_item("ctg-1", 9.3, "markets", feed_name="Cointelegraph"),
        make_item("coindesk-1", 8.0, "markets", feed_name="CoinDesk"),
        make_item("block-1", 7.5, "markets", feed_name="The Block"),
    ]
    result = make_orchestrator(filtering).apply_balanced_digest(items)
    assert [item.id for item in result.items] == ["slate-1", "decrypt-1", "coindesk-1", "block-1"]
    assert result.source_limit_deferred == 1

    # A thin day still reaches the minimum: the cap is relaxed, not absolute.
    filtering.minimum_display_items = 5
    result = make_orchestrator(filtering).apply_balanced_digest(items, fill_to_minimum=True)
    assert len(result.items) == 5 and result.minimum_fill_count == 1


def test_one_outlet_shares_its_cap_across_collectors() -> None:
    filtering = FilteringConfig(
        category_groups={"markets": CategoryGroupConfig(limit=8, categories=["markets"])},
        max_items_per_source=2,
    )
    via_news = ContentItem(
        id="gn-coindesk",
        source_type=SourceType.GOOGLE_NEWS,
        title="gn",
        url="https://example.com/gn",
        published_at=datetime.now(timezone.utc),
        ai_score=9.9,
        metadata={"category": "markets", "source_name": "CoinDesk"},
    )
    items = [via_news] + [
        make_item(f"coindesk-{i}", 9 - i, "markets", feed_name="CoinDesk") for i in range(3)
    ]
    result = make_orchestrator(filtering).apply_balanced_digest(items)
    assert [item.id for item in result.items] == ["gn-coindesk", "coindesk-0"]


def test_duplicates_keep_the_first_hand_or_original_copy() -> None:
    orchestrator = make_orchestrator(FilteringConfig(source_tiers=TIERS))
    now = datetime.now(timezone.utc)
    rewrite = make_item("slate", 8.5, "markets", feed_name="CryptoSlate")
    original = make_item("coindesk", 8.0, "markets", feed_name="CoinDesk")
    official = make_item("sec", 7.6, "policy", feed_name="SEC Press Releases")
    weak_official = make_item("sec-weak", 6.0, "policy", feed_name="SEC Press Releases")
    for offset, item in enumerate((rewrite, original, official, weak_official)):
        item.published_at = now + timedelta(minutes=offset)

    items = [rewrite, original, official]
    assert orchestrator._preferred_first([0, 1, 2], items)[0] == 2
    assert orchestrator._preferred_first([0, 1], items) == [1, 0]
    # More than a point below the best copy: a lower tier's stronger report wins.
    items = [rewrite, weak_official]
    assert orchestrator._preferred_first([0, 1], items) == [0, 1]


def test_rewrite_cap_yields_to_the_crypto_target_and_spares_other_tracks() -> None:
    filtering = FilteringConfig(
        max_items=6,
        category_groups={
            "markets": CategoryGroupConfig(limit=6, categories=["markets"]),
            "technology": CategoryGroupConfig(limit=3, categories=["ai"]),
        },
        primary_groups=["markets"],
        primary_group_min_items=4,
        max_items_per_source=2,
        source_tiers=TIERS,
        source_tier_limits={"secondary": 1},
    )
    items = [
        make_item(f"rewrite-{i}", 9.5 - i / 10, "markets", feed_name=f"Rewrite{i}") for i in range(4)
    ] + [
        make_item("coindesk", 7.0, "markets", feed_name="CoinDesk"),
        make_item("ai-unrated-1", 6.0, "ai", feed_name="Some AI blog"),
        make_item("ai-unrated-2", 5.9, "ai", feed_name="Another AI blog"),
    ]
    result = make_orchestrator(filtering).apply_balanced_digest(items)
    ids = [item.id for item in result.items]
    # The crypto target (4) is met, rewrites topping up only what original
    # reporting could not fill; unrated AI sources are not capped.
    assert result.group_counts["markets"] == 4
    assert "coindesk" in ids
    assert {"ai-unrated-1", "ai-unrated-2"} <= set(ids)
