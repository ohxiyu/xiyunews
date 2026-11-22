import json
from xml.etree import ElementTree

import pytest
from bs4 import BeautifulSoup

from src.api_output import build_edition_payload
from src.archive import build_records
from src.core_site import render_core_feed
from src.current_reader import render_current
from src.x_verification import _article_fields
from test_core_site import story

DAY = "2026-11-23"
SHELL = """<!doctype html><html><head>
<title>xiyu.news</title><link rel="canonical" href="https://xiyu.news/2026/11/22/summary-zh">
</head><body><main><section class="daily-day" data-date="2026-11-22">
<article>上期正文</article></section></main></body></html>"""


def edition():
    items = [story(1), story(2)]
    items[0].metadata["title_zh"] = "验证中文标题 <与来源>"
    items[1].metadata["category"] = "technology"
    payload = build_edition_payload(
        build_records(items, date=DAY, top_category_of=lambda item: item.metadata.get("category", "crypto")),
        date=DAY, stats={"candidates": 30, "analyzed": 6, "displayed": 2, "high_priority": 0},
    )
    return render_core_feed(items, date=DAY), payload


def test_replaces_previous_edition_and_preserves_the_delivery_text():
    original, payload = edition()
    pages = render_current(original, payload, SHELL, SHELL)
    source_articles = BeautifulSoup(original, "html.parser").select("article.digest-item")
    expected = [_article_fields(article) for article in source_articles]

    for name in ("home", "page"):
        rendered = BeautifulSoup(pages[name], "html.parser")
        articles = rendered.select("section.daily-day article.digest-item")
        assert "上期正文" not in pages[name]
        assert rendered.select_one("section.daily-day")["data-date"] == DAY
        assert [_article_fields(article) for article in articles] == expected
        assert [a["data-content-revision"] for a in articles] == [
            row["content_revision"]["zh"] for row in payload["items"]
        ]
        assert len(rendered.select(".headline-list a")) == 2
        assert len(rendered.select(".category-filters button")) == 3
    assert 'href="https://xiyu.news/2026/11/23/summary-zh"' in pages["page"]
    rss_items = ElementTree.fromstring(pages["rss"]).findall(".//item")
    assert len(rss_items) == 1
    assert rss_items[0].findtext("title") == f"{DAY} 日报"


def test_fails_on_wrong_story_order_or_a_shell_with_no_slot():
    original, payload = edition()
    reversed_payload = json.loads(json.dumps(payload))
    reversed_payload["items"].reverse()
    with pytest.raises(ValueError, match="order"):
        render_current(original, reversed_payload, SHELL, SHELL)
    with pytest.raises(ValueError, match="slot"):
        render_current(original, payload, "<body></body>", SHELL)
