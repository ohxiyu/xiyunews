"""One real-world event split into many entries must end up as one timeline."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.event_merge import (
    REVIEWS_KEY,
    apply_plans,
    merge_groups,
    merge_split_events,
    parse_merge_plan,
)
from src.event_pipeline import material_update_count, update_events
from src.events import (
    EventRelation,
    EventRelationDecision,
    EventSource,
    EventStatus,
    EventType,
    EventUpdate,
    EventUpdateType,
    TrackedEvent,
)
from src.models import ContentItem, SourceType
from src.site_pages import publish_event_compatibility_pages

NOW = datetime(2026, 9, 28, 12, tzinfo=timezone.utc)


def make_event(
    name: str,
    hours: int,
    text: str,
    *,
    updates: int = 1,
    title_zh: str = "",
    entities=("bitget",),
    topics=("bitget", "exchange-hack"),
    score: float = 9.0,
) -> TrackedEvent:
    event_id = f"evt_{name}"
    rows = []
    for index in range(updates):
        at = NOW - timedelta(hours=hours) + timedelta(minutes=index)
        rows.append(
            EventUpdate(
                update_id=f"upd_{name}_{index:02d}",
                event_id=event_id,
                occurred_at=at,
                published_at=at,
                first_seen_at=at,
                update_type=EventUpdateType.INITIAL if index == 0 else EventUpdateType.ESCALATION,
                title_zh=title_zh,
                title_en=text,
                what_changed_zh=title_zh or text,
                what_changed_en=f"{text} ({index})",
                current_state_zh=title_zh or text,
                current_state_en=text,
                importance_score=score,
                confidence=0.95,
                story_ids=[f"rss:{name}{index}"],
                sources=[
                    EventSource(
                        url=f"https://example.com/{name}/{index}",
                        label=name,
                        source_type="rss",
                    )
                ],
            )
        )
    return TrackedEvent(
        event_id=event_id,
        event_type=EventType.SECURITY_INCIDENT,
        status=EventStatus.DEVELOPING,
        category="crypto",
        title_zh=title_zh,
        title_en=text,
        current_state_zh=title_zh,
        current_state_en=text,
        entities=list(entities),
        topics=list(topics),
        first_seen_at=rows[0].first_seen_at,
        last_updated_at=rows[-1].first_seen_at,
        last_material_change_at=rows[-1].first_seen_at,
        confidence=0.95,
        updates=rows,
    )


def split_hack() -> list[TrackedEvent]:
    return [
        make_event("breach01", 72, "Bitget pauses withdrawals after $351M hot wallet breach", title_zh="Bitget 热钱包被盗，暂停提现"),
        make_event("breach02", 70, "Bitget confirms $351M security breach"),
        make_event("attrib01", 48, "Bitget CEO links $388M hack to North Korea", updates=2),
        make_event("reopen01", 20, "Bitget reopens bitcoin withdrawals after breach"),
        make_event("listing1", 10, "Bitget lists a new token", topics=("bitget", "exchange-listings")),
    ]


PLAN = {
    "events": [
        {
            "title_zh": "Bitget 热钱包被盗约 5 亿美元",
            "title_en": "Bitget hot wallet hack",
            "stages": [
                {"ids": ["evt_breach01", "evt_breach02"], "update_type": "initial"},
                {"ids": ["evt_attrib01"], "update_type": "escalation"},
                {"ids": ["evt_reopen01"], "update_type": "remediation"},
            ],
        }
    ]
}


def test_plan_parsing_drops_unknown_repeated_and_lone_ids() -> None:
    allowed = {"evt_breach01", "evt_breach02", "evt_attrib01"}
    plans = parse_merge_plan(
        {
            "events": [
                {
                    "title_zh": "甲",
                    "stages": [
                        {"ids": ["evt_breach01", "evt_unknown1"], "update_type": "escalation"},
                        {"ids": ["evt_breach02", "evt_breach01"], "update_type": "bogus"},
                    ],
                },
                # Reuses an ID already placed and leaves one entry: dropped.
                {"stages": [{"ids": ["evt_breach02", "evt_attrib01"]}]},
            ]
        },
        allowed,
    )
    assert len(plans) == 1
    assert plans[0].ids == ["evt_breach01", "evt_breach02"]
    assert plans[0].stages[0].update_type is EventUpdateType.INITIAL
    assert plans[0].stages[1].update_type is EventUpdateType.CONFIRMATION
    assert parse_merge_plan("not json", allowed) == []


def test_fold_keeps_one_node_per_stage_and_every_source() -> None:
    events = split_hack()
    plans = parse_merge_plan(PLAN, {e.event_id for e in events})
    merged, folded = apply_plans(events, plans)

    assert folded == 3
    assert len(merged) == 2  # the hack and the unrelated listing
    hack = next(e for e in merged if e.merged_event_ids)
    assert hack.event_id == "evt_breach01"  # oldest keeps its URL
    assert sorted(hack.merged_event_ids) == ["evt_attrib01", "evt_breach02", "evt_reopen01"]
    # breach01+breach02 fold into one node; attrib keeps its 2 updates; reopen 1.
    assert len(hack.updates) == 4
    assert [u.update_type for u in hack.updates] == [
        EventUpdateType.INITIAL,
        EventUpdateType.ESCALATION,
        EventUpdateType.ESCALATION,
        EventUpdateType.REMEDIATION,
    ]
    assert {s.url for s in hack.updates[0].sources} == {
        "https://example.com/breach01/0",
        "https://example.com/breach02/0",
    }
    assert set(hack.updates[0].story_ids) == {"rss:breach010", "rss:breach020"}
    assert all(u.event_id == hack.event_id for u in hack.updates)
    assert hack.last_material_change_at == events[3].last_material_change_at
    # Status follows the latest stage, as for a live update (remediation).
    assert hack.status is EventStatus.MONITORING
    # The headline invents "5 亿", which no entry states: keep a real title.
    assert hack.title_zh == "Bitget 热钱包被盗，暂停提现"
    assert hack.title_en == "Bitget hot wallet hack"
    assert material_update_count(hack) == 4


def test_merge_pass_is_bounded_recorded_and_not_repeated() -> None:
    events = split_hack()
    calls: list[str] = []

    class Client:
        async def complete(self, *, system, user, response_format="json", **_):
            calls.append(user)
            return json.dumps(PLAN)

    metadata: dict = {}
    merged, result = asyncio.run(
        merge_split_events(events, Client(), metadata, now=NOW, max_calls=1)
    )
    assert len(calls) == 1 and '"bitget"' in calls[0]
    assert result.groups_reviewed == 1 and result.events_folded == 3
    assert len(merged) == 2
    assert set(metadata[REVIEWS_KEY]["bitget"]) == {"evt_breach01", "evt_listing1"}

    # Nothing new since the review: no further call.
    assert merge_groups(merged, now=NOW, reviewed=metadata[REVIEWS_KEY]) == []
    again, second = asyncio.run(merge_split_events(merged, Client(), metadata, now=NOW))
    assert len(calls) == 1 and second.groups_reviewed == 0


def test_merge_failure_leaves_the_catalog_unchanged() -> None:
    events = split_hack()

    class Broken:
        async def complete(self, **_):
            raise RuntimeError("provider down")

    metadata: dict = {}
    merged, result = asyncio.run(merge_split_events(events, Broken(), metadata, now=NOW))
    assert [e.event_id for e in merged] == [e.event_id for e in events]
    assert result.calls_failed == 1 and result.events_folded == 0
    assert "bitget" not in metadata[REVIEWS_KEY]


def test_old_events_are_not_regrouped() -> None:
    old = [
        make_event("oldhack1", 24 * 40, "Old exchange hack"),
        make_event("oldhack2", 24 * 39, "Old exchange hack follow-up"),
    ]
    assert merge_groups(old, now=NOW) == []


def test_story_matching_several_events_joins_the_main_one() -> None:
    main = make_event("attrib01", 48, "Bitget CEO links hack to North Korea", updates=2)
    fragment = make_event("breach02", 70, "Bitget confirms security breach")
    story = ContentItem(
        id="rss:new-story",
        source_type=SourceType.RSS,
        title="Bitget hacker launders stolen bitcoin",
        content="The source report confirms the hacker began laundering the stolen Bitget funds, with transaction evidence. " * 5,
        url="https://example.com/new-story",
        published_at=NOW,
        fetched_at=NOW + timedelta(minutes=5),
        metadata={"title_zh": "Bitget 黑客清洗被盗比特币", "detailed_summary_en": "The Bitget hacker moved funds."},
        ai_score=9.0,
        ai_summary="The Bitget hacker moved funds.",
        ai_tags=["Bitget", "exchange-hack"],
    )

    async def classify(client, event, evidence):  # type: ignore[no-untyped-def]
        return EventRelationDecision(
            candidate_event_id=event.event_id,
            relation=EventRelation.SAME_EVENT_UPDATE,
            confidence=0.95 if event.event_id == "evt_breach02" else 0.94,
            update_type=EventUpdateType.ESCALATION,
            material_change=True,
            what_changed_en="The hacker began laundering funds.",
            current_state_en="Funds are being laundered.",
            rationale="Same hack.",
        )

    events, result = asyncio.run(
        update_events([story], [fragment, main], client=object(), classifier=classify)  # type: ignore[arg-type]
    )
    assert result.new_events == 0
    assert story.metadata["event_id"] == "evt_attrib01"


def test_folded_event_urls_redirect_to_the_survivor(tmp_path: Path) -> None:
    events = split_hack()
    merged, _ = apply_plans(events, parse_merge_plan(PLAN, {e.event_id for e in events}))
    counts = publish_event_compatibility_pages(
        merged,
        {"legacy-thread": "evt_attrib01"},  # an old map target that was folded
        {},
        ["zh", "en"],
        events_root=tmp_path / "events",
        threads_root=tmp_path / "threads",
        thread_index_path=tmp_path / "_data" / "threads.json",
    )
    assert counts["merged"] == 6
    page = (tmp_path / "events" / "evt_breach02.html").read_text(encoding="utf-8")
    assert "permalink: /events/evt_breach02/" in page
    assert "redirect_to: /events/evt_breach01/" in page
    assert "noindex: true" in page
    legacy = (tmp_path / "threads" / "legacy-thread.html").read_text(encoding="utf-8")
    assert "/events/evt_breach01/" in legacy
