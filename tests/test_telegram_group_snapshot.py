"""Offline preparation checks; no Telegram/AI/network calls."""
import pytest

from src.services.telegram_group_snapshot import build_snapshot, pack


def edition(count=14):
    return {"date": "2026-10-12", "overview": {"zh": "已发布的今日脉络。"},
        "items": [{"rank": n, "title": {"zh": f"新闻 & {n}"},
            "summary": {"zh": "已报道的首句。后续正文。"}} for n in range(1, count+1)]}


def event():
    return {"event_id": "evt_test01", "title_zh": "公司 <事件>", "status": "developing",
        "status_zh": "进展中", "summary_zh": "已报道的状态。", "background_zh": "事件背景。",
        "latest_at": "2026-10-12T08:00:00+08:00", "timeline": [{"update_id": "upd_test01",
        "date": "2026-10-12", "type_zh": "确认", "text_zh": "新事实。补充说明。",
        "sources": [{"url": "javascript:bad", "label": "不安全链接"},
            {"url": "https://example.com/evidence", "label": "原始来源"}]}]}


def test_reuses_all_published_titles_with_stable_date_links_and_three_briefs():
    data = build_snapshot(edition(), {"focus": []}, "a"*40)
    message = "\n".join(data["feed_parts"])
    assert "新闻 &amp; 14" in message
    assert message.count("已报道的首句。") == 3
    assert "后续正文" not in message
    assert "/2026/10/12/summary-zh#zh-2026-10-12-item-14" in message
    assert all(len(part) <= 3600 for part in data["feed_parts"])


def test_snapshot_retains_non_focus_closed_events_for_later_wrap_up():
    row = event()
    other = {**row, "event_id": "evt_closed01", "status": "closed"}
    data = build_snapshot(edition(), {"focus": [row], "threads": [row], "completed": [other]}, "a"*40)
    assert len(data["events"]) == 2
    assert data["events"][0]["updates"][0]["sources"] == [{"url": "https://example.com/evidence", "label": "原始来源"}]
    assert data["events"][0]["focus"] is True
    assert data["events"][1]["focus"] is False


def test_pack_splits_at_complete_entry_boundaries():
    entries = [f"<b>{n}</b>" + "内容"*80 for n in range(10)]
    parts = pack(entries, "标题", "结尾", 400)
    assert len(parts) > 1
    assert all(len(part) <= 400 for part in parts)
    for entry in entries:
        assert sum(entry in part for part in parts) == 1
    with pytest.raises(ValueError):
        pack(["内容"*300], "标题", "结尾", 400)


@pytest.mark.parametrize("date,artifact", [("invalid", "a"*40), ("2026-10-12", "main")])
def test_invalid_snapshot_stops(date, artifact):
    source = edition()
    source["date"] = date
    with pytest.raises(ValueError):
        build_snapshot(source, {}, artifact)
