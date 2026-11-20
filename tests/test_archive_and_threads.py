from src.dedup import fingerprint,same_thread,normalize_tag
"""Tests for the archive layer, thread linking, and entity grouping."""

from datetime import date, datetime, timezone
from pathlib import Path

from src.archive import (
    ArchiveRecord,
    build_records,
    load_archive,
    load_recent_archive,
    save_edition_records,
)
from src.models import ContentItem, SourceType


def make_item(
    item_id: str,
    *,
    title: str = "Title",
    tags: list[str] | None = None,
    score: float = 8.0,
    merged: list[str] | None = None,
) -> ContentItem:
    metadata = {"category": "crypto-markets", "feed_name": "Feed"}
    if merged:
        metadata["merged_sources"] = merged
    return ContentItem(
        id=item_id,
        source_type=SourceType.RSS,
        title=title,
        url=f"https://example.com/{item_id}",
        published_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
        ai_score=score,
        ai_tags=tags or [],
        metadata=metadata,
    )


def make_record(
    date_str: str,
    *,
    rank: int = 1,
    title_en: str = "",
    tags: list[str] | None = None,
    thread_id: str | None = None,
    url: str | None = None,
    score: float = 8.0,
) -> ArchiveRecord:
    return ArchiveRecord(
        date=date_str,
        rank=rank,
        item_id=f"{date_str}-{rank}",
        url=url or f"https://example.com/{date_str}-{rank}",
        title_en=title_en,
        title_zh=title_en,
        score=score,
        tags=tags or [],
        thread_id=thread_id,
    )


def test_save_edition_records_replaces_same_date(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    save_edition_records(
        [make_record("2026-08-09", rank=1, title_en="First run")],
        date="2026-08-09",
        root=root,
    )
    save_edition_records(
        [
            make_record("2026-08-09", rank=1, title_en="Rebuilt"),
            make_record("2026-08-09", rank=2, title_en="Second"),
        ],
        date="2026-08-09",
        root=root,
    )
    records = load_archive(root=root)
    assert [record.title_en for record in records] == ["Rebuilt", "Second"]


def test_save_edition_records_keeps_other_dates(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    save_edition_records(
        [make_record("2026-08-08", title_en="Older")],
        date="2026-08-08",
        root=root,
    )
    save_edition_records(
        [make_record("2026-08-09", title_en="Newer")],
        date="2026-08-09",
        root=root,
    )
    assert [r.title_en for r in load_archive(root=root)] == ["Older", "Newer"]


def test_load_archive_skips_corrupt_lines(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    root.mkdir()
    path = root / "2026-08.jsonl"
    good = make_record("2026-08-09", title_en="Good").model_dump_json()
    path.write_text(f"{good}\nnot json\n\n", encoding="utf-8")
    records = load_archive(root=root)
    assert [record.title_en for record in records] == ["Good"]


def test_load_recent_archive_filters_by_window(tmp_path: Path) -> None:
    root = tmp_path / "archive"
    save_edition_records(
        [make_record("2026-07-01", title_en="Old")], date="2026-07-01", root=root
    )
    save_edition_records(
        [make_record("2026-08-09", title_en="Fresh")], date="2026-08-09", root=root
    )
    recent = load_recent_archive(7, today=date(2026, 8, 9), root=root)
    assert [record.title_en for record in recent] == ["Fresh"]


def test_build_records_captures_provenance_and_threads() -> None:
    item = make_item(
        "story",
        title="Bybit hack",
        tags=["bybit", "security"],
        merged=["rss", "telegram"],
    )
    item.metadata["thread_id"] = "tabc"
    item.metadata["thread_day"] = 2
    records = build_records(
        [item], date="2026-08-09", top_category_of=lambda _item: "crypto"
    )
    assert records[0].sources_count == 2
    assert records[0].top_category == "crypto"
    assert records[0].thread_id == "tabc"
    assert records[0].thread_day == 2
    assert records[0].rank == 1


def test_normalize_tag_slugifies() -> None:
    assert normalize_tag("#Lazarus Group") == "lazarus-group"
    assert normalize_tag("X Layer") == "x-layer"
    assert normalize_tag("  ") == ""




def test_same_thread_matches_continuing_coverage() -> None:
    first = fingerprint(
        title_en="Bybit loses $1.5B in Lazarus Group hack",
        tags=["bybit", "lazarus-group", "security"],
    )
    follow_up = fingerprint(
        title_en="Bybit sues North Korea and Lazarus Group over hack",
        tags=["bybit", "lazarus-group", "north-korea"],
    )
    unrelated = fingerprint(
        title_en="Kraken details war-game load testing",
        tags=["kraken", "engineering"],
    )
    assert same_thread(first, follow_up)
    assert not same_thread(first, unrelated)


def test_same_thread_ignores_empty_fingerprints() -> None:
    assert not same_thread(fingerprint(), fingerprint(title_en="Anything here"))
















def test_anchors_link_continuing_coverage_that_shares_little_wording() -> None:
    """The case token overlap alone cannot see: same event, new wording."""
    day_one = fingerprint(
        title_zh="Coldcard 固件漏洞可能泄露助记词",
        title_en="Coldcard Firmware Flaw Exposes Seed Phrases",
        summary_zh="研究人员披露 Coldcard 硬件钱包固件漏洞，攻击者可能提取助记词。",
        summary_en=(
            "Researchers disclosed a firmware flaw in the Coldcard hardware "
            "wallet that could let an attacker extract the seed phrase."
        ),
        tags=["coldcard", "security", "hardware-wallet"],
    )
    day_two = fingerprint(
        title_zh="Coldcard 紧急发布固件补丁",
        title_en="Coldcard Ships Emergency Firmware Patch After Disclosure",
        summary_zh="Coldcard 针对助记词泄露漏洞发布紧急固件补丁，建议硬件钱包用户升级。",
        summary_en=(
            "Coldcard shipped an emergency firmware patch for the seed phrase "
            "disclosure flaw and urged hardware wallet users to upgrade."
        ),
        tags=["coldcard", "patch", "hardware-wallet"],
    )
    assert same_thread(day_one, day_two)


def test_shared_name_alone_does_not_make_a_thread() -> None:
    """Two unrelated stories about one company belong on its entity page."""
    revenue = fingerprint(
        title_zh="Coinbase 季度营收创纪录",
        title_en="Coinbase Reports Record Quarterly Revenue",
        summary_zh="Coinbase 公布季度财报，交易与订阅收入双双增长。",
        summary_en="Coinbase posted record quarterly revenue as income grew.",
        tags=["coinbase", "revenue"],
    )
    listings = fingerprint(
        title_zh="Coinbase 支持两条新公链",
        title_en="Coinbase Adds Support for Two New Networks",
        summary_zh="Coinbase 宣布为两条新公链提供充提支持。",
        summary_en="Coinbase announced deposit support for two new networks.",
        tags=["coinbase", "listings"],
    )
    assert not same_thread(revenue, listings)


def test_name_mentioned_only_in_passing_does_not_link() -> None:
    """An actor named in a body paragraph is not what the story is about."""
    subject = fingerprint(
        title_zh="Hyperliquid 的永续合约收入下滑",
        title_en="Hyperliquid Perpetuals Revenue Slips",
        summary_zh="Hyperliquid 的永续合约费用收入较上月下降，协议收入承压。",
        summary_en="Hyperliquid perpetual futures fee revenue fell month over month.",
        tags=["hyperliquid", "perp-futures"],
    )
    passing = fingerprint(
        title_zh="2026 年超 100 个加密项目倒闭",
        title_en="More Than 100 Crypto Projects Shut Down in 2026",
        summary_zh="2026 年超过 100 个协议倒闭，费用收入减半，Hyperliquid 等头部协议也受波及。",
        summary_en=(
            "More than 100 protocols shut down in 2026 as fee revenue halved, "
            "with leaders like Hyperliquid affected."
        ),
        tags=["market-shakeout", "venture-capital"],
    )
    assert not same_thread(subject, passing)
