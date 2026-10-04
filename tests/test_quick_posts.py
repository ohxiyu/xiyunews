from copy import deepcopy
from datetime import date
import json
from pathlib import Path

from src.quick_posts import public_posts, render_posts, publish
from src.editorial_changes import affects_today

DAY = date(2026, 9, 10)
ROW = {"type": "quick_post", "id": "12345678-1234-1234-1234-123456789abc",
       "body": "第一段。\n\n第二段 🚀", "date": "2026-09-10", "enabled": True,
       "updated_at": "2026-09-10T01:00:00Z", "note": "private", "request_hash": "private"}


def test_public_field_allowlist_and_no_fake_title_or_score():
    rows = public_posts({"items": [ROW]}, DAY)
    assert rows[0]["body"] == ROW["body"]
    assert not set(rows[0]) & {"note", "request_hash", "title", "score", "enabled"}
    assert rows[0]["url"] == ""


def test_drafts_future_old_invalid_and_duplicates_are_excluded():
    rows = [ROW, ROW, {**ROW, "id": "b" * 36, "enabled": False},
            {**ROW, "id": "c" * 36, "date": "2026-09-11"},
            {**ROW, "id": "d" * 36, "date": "2026-09-08"},
            {**ROW, "id": "e" * 36, "date": "bad"}]
    assert len(public_posts({"items": rows}, DAY)) == 1


def test_dates_and_pin_order():
    rows = [ROW, {**ROW, "id": "b" * 36, "date": "2026-09-09", "pin": True},
            {**ROW, "id": "c" * 36, "pin": True}]
    result = public_posts({"items": rows}, DAY)
    assert [row["id"] for row in result] == ["c" * 36, ROW["id"], "b" * 36]


def test_markup_urls_and_liquid_are_not_executed():
    row = {**ROW, "body": '<script>alert(1)</script>\n\n{{ secret }}', "url": "javascript:alert(1)",
           "image": '/assets/uploads/../../private'}
    result = public_posts({"items": [row]}, DAY)
    rendered = render_posts(result)
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "<p>{{ secret }}</p>" in rendered
    assert "<img" not in rendered and "javascript:" not in rendered
    assert rendered.count("<p>") == 2


def test_render_image_source_and_badges():
    row = {**ROW, "image": "/assets/uploads/quick-" + "a" * 64 + ".png",
           "url": "https://example.com/?x=1&y=2", "pin": True, "breaking": True}
    rendered = render_posts(public_posts({"items": [row]}, DAY))
    assert "Breaking" in rendered and "PIN" in rendered
    assert 'loading="lazy"' in rendered and "&amp;y=2" in rendered


def test_quick_only_edits_do_not_trigger_ai_rebuild():
    before = {"items": [{"type": "suppress", "url": "https://example.com", "date": str(DAY)}]}
    after = deepcopy(before)
    after["items"].append(ROW)
    assert not affects_today(before, after, DAY)


def test_publish_matches_html_and_json(tmp_path):
    source = tmp_path / "editorial.json"
    source.write_text(json.dumps({"items": [ROW]}))
    publish(source, tmp_path / "docs", DAY)
    data = json.loads((tmp_path / "docs/api/quick-posts.json").read_text())
    html = json.loads((tmp_path / "docs/_data/quick_posts.json").read_text())["html"]
    assert data["items"][0]["id"] in html
    assert "private" not in html
    assert data["date"] == str(DAY)


def test_all_publication_workflows_regenerate_stream():
    root = Path(__file__).parents[1]
    for name in ["daily-summary", "feed-collection", "deploy-docs", "weekly-review", "event-archive-migration"]:
        text = (root / f".github/workflows/{name}.yml").read_text()
        assert "uv run python -m src.quick_posts" in text
    page = (root / "docs/_includes/feed-home.html").read_text()
    assert 'data-quick-post-status' in page
    assert "site.data.quick_posts.html" not in page


def batch():
    return {**ROW, "type": "quick_batch", "raw": "第一条。\n---\n第二条。",
            "pin": False, "breaking": False, "anchor_id": "story-42",
            "generation": {"model": "private"}, "image": "",
            "items": [{"id": char * 36, "title": "新闻 " + char, "body": "正文\n\n第二段",
                       "background": "背景", "market_impact": "可能影响", "category": "crypto-markets",
                       "tags": ["crypto"], "sources": [{"title": "材料", "url": "https://example.com/" + char}]}
                      for char in ("a", "b")]}


def test_batch_is_contiguous_and_never_enters_ranked_editorial():
    group = batch()
    result = public_posts({"items": [group, {**ROW, "id": "f" * 36}]}, DAY)
    assert [row["id"] for row in result] == ["f" * 36, "a" * 36, "b" * 36]
    assert [row["batch_index"] for row in result[1:]] == [0, 1]
    assert result[1]["anchor_id"] == "story-42"
    assert not set(result[1]) & {"raw", "generation", "request_hash", "note", "score"}
    assert not affects_today({"items": []}, {"items": [group]}, DAY)
    edited = deepcopy(group)
    edited["items"][0]["body"] = "修改正文"
    assert not affects_today({"items": [group]}, {"items": [edited]}, DAY)
    rendered = render_posts(result)
    assert "<h2>新闻 a</h2>" in rendered and "市场影响" in rendered and "#crypto" in rendered
    assert "private" not in rendered


def test_invalid_or_disabled_group_is_not_partially_published():
    for mutate in (
        lambda row: row.update(enabled=False),
        lambda row: row.update(date="2026-09-11"),
        lambda row: row.update(anchor_id="<script>"),
        lambda row: row["items"][1].update(title=""),
        lambda row: row["items"][1].update(id="a" * 36),
        lambda row: row["items"][0]["sources"][0].update(url="javascript:bad"),
        lambda row: row["items"][0].update(tags=["x" * 51]),
    ):
        group = batch()
        mutate(group)
        assert public_posts({"items": [group]}, DAY) == []


def test_batch_escapes_all_generated_fields():
    group = batch()
    group["items"][0].update(title="<script>bad</script>", background="<img onerror=x>", tags=["<tag>"])
    rendered = render_posts(public_posts({"items": [group]}, DAY))
    assert "<script>" not in rendered and "<img onerror" not in rendered
    assert "&lt;tag&gt;" in rendered
