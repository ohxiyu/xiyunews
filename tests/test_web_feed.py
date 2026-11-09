"""Tests for static-first public feed rendering."""

from datetime import datetime, timezone
from pathlib import Path

from bs4 import BeautifulSoup

from src.models import ContentItem, SourceType
from src.web_feed import render_web_feed


def test_recent_editions_share_one_date_link_per_edition() -> None:
    template = Path("docs/_includes/edition-header.html").read_text()
    nav = template.split('<nav class="day-nav"', 1)[1].split("</nav>", 1)[0]
    # Both home and archived editions use the same seven dates. The newest
    # date is also the way home, rather than a second misleading Today link.
    assert nav.count("<a ") == 1
    assert "for post in nav_posts limit:7" in nav
    assert "if forloop.first %}{% assign nav_url = home_url" in nav
    assert '{{ nav_url | relative_url }}' in nav
    assert '{{ post.date | date: "%m.%d" }}' in nav
    assert 'aria-current="true"' in nav
    assert "nav_key == include.current" in nav
    assert "day-nav-today" not in nav
    assert "Today" not in nav
    assert "今日" not in nav


def make_item(
    item_id: str,
    category: str,
    *,
    score: float = 8.0,
) -> ContentItem:
    return ContentItem(
        id=item_id,
        source_type=SourceType.RSS,
        title=f"Title {item_id}",
        url=f"https://example.com/{item_id}",
        author="publisher",
        published_at=datetime(2026, 7, 30, 16, 30, tzinfo=timezone.utc),
        metadata={
            "category": category,
            "feed_name": "Example Feed",
            "detailed_summary_zh": f"摘要 {item_id}",
            "detailed_summary_en": f"Summary {item_id}",
        },
        ai_score=score,
        ai_summary=f"Fallback {item_id}",
        ai_tags=["News"],
    )


def test_background_precedes_report_and_analysis_references_follow_source():
    item = make_item("reading-order", "crypto-markets")
    item.metadata.update(background_zh="背景事实", market_impact_zh="明确的分析判断",
                         community_discussion_zh="有依据的讨论", reference_links=[{"url":"https://example.com/evidence","title":"原始证据"}])
    page = BeautifulSoup(render_web_feed([item], date="2026-10-13", total_fetched=1,
                                        language="zh", display_timezone="Asia/Shanghai"), "html.parser")
    article = page.select_one("article.digest-item")
    children = list(article.select_one(".digest-item-content").children)
    background = article.select_one('[data-context-placement="background"]')
    after = article.select_one('[data-context-placement="after"]')
    assert background.has_attr("open")
    assert not after.has_attr("open")
    assert after.find("summary") is not None
    assert children.index(background) < children.index(article.select_one(".story-summary-body"))
    assert children.index(after) > children.index(article.select_one(".source-line"))
    assert "背景事实" in background.get_text() and "明确的分析判断" not in background.get_text()
    assert "明确的分析判断" in after.get_text() and "背景事实" not in after.get_text()
    assert "有依据的讨论" in after.get_text()
    assert article.select_one(".story-summary-body").get_text() == "摘要 reading-order"


def test_render_web_feed_outputs_final_cards_and_top_level_filters() -> None:
    items = [
        make_item("market", "crypto-markets", score=9.4),
        make_item("ai", "ai-labs", score=8.8),
        make_item("policy", "macro-regulation", score=8.4),
        make_item("protocol", "crypto-protocols", score=8.0),
    ]

    markup = render_web_feed(
        items,
        date="2026-07-31",
        total_fetched=42,
        language="zh",
        display_timezone="Asia/Shanghai",
    )
    page = BeautifulSoup(markup, "html.parser")

    layout = page.select_one(
        ".daily-feed-layout.is-editorial-grid"
        ".feed-rendered-static[data-feed-render-version='3']"
    )
    assert layout
    assert [child.get("class", []) for child in layout.find_all(recursive=False)] == [
        ["feed-orientation"],
        ["daily-story-stream"],
        ["headline-rail"],
    ]
    assert len(page.select(".digest-item")) == 4
    assert len(page.select(".digest-item.is-priority")) == 3
    assert [
        button["data-category"]
        for button in page.select("[data-static-filters] button")
    ] == ["all", "crypto", "technology", "policy"]
    assert [
        article["data-category"]
        for article in page.select(".digest-item")
    ] == ["crypto", "technology", "policy", "crypto"]
    assert page.select_one("#zh-2026-07-31-item-1")
    assert [row["data-story-id"] for row in page.select(".digest-item")] == ["market", "ai", "policy", "protocol"]
    assert "7月31日 00:30" in page.select_one(".source-line").get_text(" ", strip=True)
    assert "本期从 42 条候选中展示 4 条" in markup
    assert len(page.select('.story-share-button[data-story-share="card"]')) == 4
    assert not page.select('[data-story-share="x"]')
    assert not page.select('[data-story-share="image"]')
    controls = page.select_one(".digest-item-controls")
    assert controls.select_one(".score-badge")
    assert [
        button["data-story-share"]
        for button in controls.select(".story-share-button")
    ] == ["card"]
    assert (
        controls.select_one('[data-story-share="card"]')["aria-label"]
        == "生成并分享图片卡片"
    )
    assert controls.select_one('[data-story-share="card"]').get_text(
        strip=True
    ).endswith("分享")


def test_rendered_revisions_match_api_and_change_when_core_text_changes():
    from src.archive import build_records
    from src.api_output import build_edition_payload

    item = make_item("revision", "crypto-markets")
    item.metadata.pop("detailed_summary_zh")
    item.metadata.pop("detailed_summary_en")
    item.metadata["detailed_summary"] = "  shared fallback text  "
    markers = []
    for text in ("first version", "corrected version"):
        item.title = text
        records = build_records([item], date="2026-09-05", top_category_of=lambda _: "crypto")
        payload = build_edition_payload(records, date="2026-09-05", stats={})
        assert payload["content_revision_version"] == 1
        for language in ("zh", "en"):
            markup = render_web_feed([item], date="2026-09-05", total_fetched=1,
                                     language=language, display_timezone="Asia/Shanghai")
            card = BeautifulSoup(markup, "html.parser").select_one("article.digest-item")
            assert card["data-content-revision"] == payload["items"][0]["content_revision"][language]
        markers.append(payload["items"][0]["content_revision"]["zh"])
    assert markers[0] != markers[1]


def test_render_web_feed_escapes_text_and_rejects_unsafe_references() -> None:
    item = make_item("unsafe", "crypto-markets")
    item.title = '<script>alert("title")</script>'
    item.metadata.update(
        {
            "detailed_summary_en": '<img src=x onerror="alert(1)">',
            "background_en": '<iframe src="bad"></iframe>',
            "sources": [
                {
                    "title": '<svg onload="alert(1)">',
                    "url": "javascript:alert(1)",
                }
            ],
        }
    )

    markup = render_web_feed(
        [item],
        date="2026-07-31",
        total_fetched=1,
        language="en",
        display_timezone="UTC",
    )

    assert "<script>" not in markup
    assert "<img src=x" not in markup
    assert "<iframe" not in markup
    assert "<svg onload" not in markup
    assert 'href="javascript:' not in markup
    assert "&lt;script&gt;" in markup
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;" in markup


def test_story_share_controls_are_localized_in_english() -> None:
    markup = render_web_feed(
        [make_item("english", "ai-labs")],
        date="2026-07-31",
        total_fetched=1,
        language="en",
        display_timezone="UTC",
    )
    page = BeautifulSoup(markup, "html.parser")

    assert (
        page.select_one('[data-story-share="card"]')["aria-label"]
        == "Generate and share image card"
    )
    assert page.select_one('[data-story-share="card"]').get_text(
        strip=True
    ).endswith("Share")
    assert not page.select('[data-story-share="x"]')
    assert not page.select('[data-story-share="image"]')


def test_render_web_feed_empty_state_is_static() -> None:
    markup = render_web_feed(
        [],
        date="2026-07-31",
        total_fetched=0,
        language="zh",
        display_timezone="Asia/Shanghai",
    )

    assert "feed-rendered-static" in markup
    assert "今日暂无达到展示阈值的重要资讯" in markup
    assert "digest-item" not in markup






def test_story_summary_preserves_semantic_paragraphs() -> None:
    item = make_item("paragraphs", "crypto-markets")
    item.metadata["detailed_summary_zh"] = (
        "第一段说明发生了什么。\n\n"
        "第二段解释为什么重要。\n\n"
        "第三段补充限制和关键细节。"
    )

    markup = render_web_feed(
        [item],
        date="2026-07-31",
        total_fetched=1,
        language="zh",
        display_timezone="Asia/Shanghai",
    )
    page = BeautifulSoup(markup, "html.parser")

    assert [
        paragraph.get_text(strip=True)
        for paragraph in page.select(".story-summary-body > p")
    ] == [
        "第一段说明发生了什么。",
        "第二段解释为什么重要。",
        "第三段补充限制和关键细节。",
    ]


def test_story_summary_splits_legacy_one_line_content() -> None:
    item = make_item("legacy", "crypto-markets")
    item.metadata["detailed_summary_zh"] = (
        "监管机构在周一公布了覆盖主要交易平台的新规草案，并给出三个月反馈期。"
        "该草案提高了托管和信息披露要求。"
        "市场参与者需要重新评估合规成本和产品安排。"
        "规则目前仍处于征求意见阶段，尚未正式生效。"
    )

    markup = render_web_feed(
        [item],
        date="2026-07-31",
        total_fetched=1,
        language="zh",
        display_timezone="Asia/Shanghai",
    )
    page = BeautifulSoup(markup, "html.parser")
    paragraphs = page.select(".story-summary-body > p")

    assert len(paragraphs) >= 2
    assert "".join(p.get_text(strip=True) for p in paragraphs) == item.metadata[
        "detailed_summary_zh"
    ]










