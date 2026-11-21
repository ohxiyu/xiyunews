"""Reader curation is bounded, reversible and does not invent developments."""
import json
from datetime import timedelta

from src.events import EventStatus, EventUpdateType
from src.site_pages import _timeline, build_event_index_data
from src.tracking_republish import republish_tracking
from test_api_output_and_pages import make_event


def ongoing(event_id, category="crypto", score=8.0):
    event = make_event(event_id)
    event.status = EventStatus.DEVELOPING
    event.category = category
    for update in event.updates:
        update.importance_score = score
    return event


def test_focus_limits_six_prioritizes_crypto_and_keeps_all_other_history():
    events = [ongoing(f"evt_crypto{i:02}", score=7.5) for i in range(8)]
    events += [ongoing(f"evt_tech{i:02}", "technology", 8.5) for i in range(8)]
    payload = build_event_index_data(events, now=events[0].last_updated_at, focus_policy={})
    assert len(payload["focus"]) == 6
    assert sum(row["category"] == "crypto" for row in payload["focus"]) >= 3
    assert len(payload["other"]) + len(payload["focus"]) == 16
    assert payload["ranking"] == payload["focus"]
    assert payload["featured"] == payload["focus"][:3]
    assert all(len(row["timeline"]) <= 10 for row in payload["focus"])


def test_completed_low_confidence_minor_and_review_excluded_do_not_fill_slots():
    good = ongoing("evt_good01")
    completed = ongoing("evt_complete01")
    completed.status = EventStatus.CLOSED
    uncertain = ongoing("evt_uncertain01")
    uncertain.updates[-1].confidence = 0.75
    minor = ongoing("evt_minor01", score=6.5)
    excluded = ongoing("evt_excluded01")
    payload = build_event_index_data([good, completed, uncertain, minor, excluded],
        now=good.last_updated_at, focus_policy={"events": {excluded.event_id: {"exclude": True}}})
    assert [row["event_id"] for row in payload["focus"]] == [good.event_id]
    assert len(payload["threads"]) == 5  # retained catalog-derived recent rows
    assert payload["completed"][0]["event_id"] == completed.event_id


def test_pending_deadline_keeps_quiet_candidate_until_expiry_without_new_node():
    event = ongoing("evt_deadline01")
    now = event.last_updated_at + timedelta(days=12)
    policy = {"events": {event.event_id: {"watch_until": (now + timedelta(days=2)).date().isoformat(),
        "watch_zh": "已报道的期限", "source_url": event.updates[-1].sources[0].url}}}
    payload = build_event_index_data([event], now=now, focus_policy=policy)
    assert payload["focus"][0]["watch_zh"] == "已报道的期限"
    assert payload["focus"][0]["latest_at"] == event.last_updated_at.isoformat()
    assert len(payload["focus"][0]["timeline"]) == 2
    assert payload["dormant"] == []  # not duplicated in two sections
    expired = build_event_index_data([event], now=now + timedelta(days=3), focus_policy=policy)
    assert expired["focus"] == []
    policy["events"][event.event_id]["source_url"] = "javascript:alert(1)"
    assert build_event_index_data([event], now=now, focus_policy=policy)["focus"] == []


def test_background_uses_recent_context_and_does_not_turn_impact_into_discussion():
    event = ongoing("evt_context01")
    event.updates[0].background_zh = "早期不相关背景"
    event.updates[-1].background_zh = "当前事件背景"
    for update in event.updates:
        update.community_discussion_zh = update.community_discussion_en = ""
    row = build_event_index_data([event], now=event.last_updated_at, focus_policy={})["focus"][0]
    assert row["background_zh"] == "当前事件背景"
    assert row["discussion_zh"] == row["discussion_en"] == ""
    assert row["market_impact_zh"] == "最新市场影响"
    assert row["reference_links"][0]["url"] == event.updates[-1].references[0].url


def test_display_dedup_preserves_numbers_corrections_ids_and_occurrence_dates():
    event = ongoing("evt_dedup01")
    original, newer = event.updates
    newer.what_changed_zh = original.what_changed_zh
    newer.what_changed_en = original.what_changed_en
    assert len(_timeline(event.updates)) == 1
    newer.what_changed_en += " Cost changed to 1.2 USD."
    assert len(_timeline(event.updates)) == 2
    newer.what_changed_en = original.what_changed_en
    newer.update_type = EventUpdateType.CORRECTION
    assert len(_timeline(event.updates)) == 2
    newer.first_seen_at += timedelta(days=5)
    rows = _timeline(event.updates)
    assert rows[0]["date"] == newer.occurred_at.date().isoformat()
    assert rows[0]["update_id"] == newer.update_id
    assert len(event.updates) == 2


def test_republish_refreshes_reader_pages_without_catalog_api_or_redirect_changes(tmp_path):
    event = ongoing("evt_republish01")
    data = tmp_path / "_data"
    data.mkdir()
    catalog = data / "events.json"
    catalog.write_text(json.dumps({"schema_version": 1, "events": [event.model_dump(mode="json")]}))
    before = catalog.read_bytes()
    event_dir = tmp_path / "events"
    event_dir.mkdir()
    alias = event_dir / "evt_legacy01.html"
    alias.write_text("keep merged redirect")
    api = tmp_path / "api" / "events.json"
    api.parent.mkdir()
    api.write_text("keep API evidence")
    path = republish_tracking(tmp_path, now=event.last_updated_at)
    assert catalog.read_bytes() == before
    assert json.loads(path.read_text())["focus"][0]["event_id"] == event.event_id
    assert sorted(p.name for p in data.iterdir()) == ["events.json", "threads.json"]
    for prefix in ("", "en-"):
        page = (event_dir / f"{prefix}{event.event_id}.html").read_text()
        assert page.index('id="upd_example2"') < page.index('id="upd_example1"')
    assert alias.read_text() == "keep merged redirect"
    assert api.read_text() == "keep API evidence"


def test_reader_timeline_keeps_ten_newest_distinct_updates_and_full_detail_history():
    from src.site_pages import render_event_page

    event = make_event("evt_dense01", updates=12)
    event.status = EventStatus.DEVELOPING
    before = event.model_dump(mode="json")
    payload = build_event_index_data([event], now=event.last_material_change_at)
    timeline = payload["focus"][0]["timeline"]
    assert [row["update_id"] for row in timeline] == [f"upd_example{i}" for i in range(12, 2, -1)]
    page = render_event_page(event, "zh")
    assert page.count('class="event-update event-stream-item') == 12
    assert page.index('id="upd_example12"') < page.index('id="upd_example1"')
    assert event.model_dump(mode="json") == before


def test_focus_is_recent_first_without_promoting_minor_stories_into_home_spotlight():
    major = ongoing("evt_major01", score=9.5)
    major.updates.append(major.updates[-1].model_copy(update={
        "update_id": "upd_third01", "occurred_at": major.last_material_change_at + timedelta(hours=1),
        "what_changed_en": "A third material development", "what_changed_zh": "第三次实质变化"}))
    major.last_material_change_at = major.updates[-1].occurred_at
    newer = ongoing("evt_recent01", score=7.5)
    newer.last_material_change_at = major.last_material_change_at + timedelta(hours=2)
    payload = build_event_index_data([major, newer], now=newer.last_material_change_at)
    assert [r["event_id"] for r in payload["focus"]] == [newer.event_id, major.event_id]
    assert payload["spotlight"]["event_id"] == major.event_id
