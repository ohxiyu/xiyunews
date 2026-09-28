"""Chinese event pages must not show English headlines, and only events
that actually developed should be indexed or advertised in the daily feed."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone

from src.ai.event_translation import translate_texts
from src.event_pipeline import (
    apply_zh_translations,
    backfill_event_briefs,
    is_tracked,
    untranslated_texts,
)
from src.events import (
    EventSource,
    EventStatus,
    EventType,
    EventUpdate,
    EventUpdateType,
    TrackedEvent,
)
from src.models import ContentItem, SourceType

NOW = datetime(2026, 9, 28, tzinfo=timezone.utc)


def update(n: int, text: str, *, kind=EventUpdateType.INITIAL, zh: str | None = None) -> EventUpdate:
    return EventUpdate(
        update_id=f"upd_node{n:02d}",
        event_id="evt_sample1",
        occurred_at=NOW + timedelta(hours=n),
        published_at=NOW + timedelta(hours=n),
        first_seen_at=NOW + timedelta(hours=n),
        update_type=kind,
        title_zh=zh or text,
        title_en=text,
        what_changed_zh=zh or text,
        what_changed_en=text,
        current_state_zh=zh or text,
        current_state_en=text,
        confidence=0.9,
        story_ids=[f"rss:s{n}"],
        sources=[EventSource(url=f"https://example.com/{n}", label="Src", source_type="rss")],
    )


def event(*updates: EventUpdate) -> TrackedEvent:
    first = updates[0]
    return TrackedEvent(
        event_id="evt_sample1",
        event_type=EventType.SECURITY_INCIDENT,
        status=EventStatus.DEVELOPING,
        category="crypto",
        title_zh=first.title_zh,
        title_en=first.title_en,
        current_state_zh=updates[-1].current_state_zh,
        current_state_en=updates[-1].current_state_en,
        first_seen_at=first.first_seen_at,
        last_updated_at=updates[-1].first_seen_at,
        last_material_change_at=updates[-1].first_seen_at,
        confidence=0.9,
        updates=list(updates),
    )


def translated_item(n: int) -> ContentItem:
    return ContentItem(
        id=f"rss:s{n}",
        source_type=SourceType.RSS,
        title="Exchange hacked for $40M",
        url=f"https://example.com/{n}",
        published_at=NOW,
        metadata={"title_zh": "交易所被盗 4000 万美元", "detailed_summary_zh": "某交易所被盗约 4000 万美元，已暂停提现。"},
    )


def test_backfill_replaces_english_placeholders_but_never_rewrites_chinese():
    ev = event(update(0, "Exchange hacked for $40M"), update(1, "Funds frozen", kind=EventUpdateType.RESPONSE, zh="资金已冻结"))
    [hydrated], _ = backfill_event_briefs([ev], items=[translated_item(0)])
    first, second = hydrated.updates
    assert first.title_zh == "交易所被盗 4000 万美元"
    assert first.current_state_zh.startswith("某交易所被盗")
    assert second.title_zh == "资金已冻结"
    assert hydrated.title_zh == "交易所被盗 4000 万美元"


def test_backfill_leaves_later_update_narrative_to_translation():
    ev = event(update(0, "A"), update(1, "Funds frozen", kind=EventUpdateType.RESPONSE))
    item = translated_item(1)
    [hydrated], _ = backfill_event_briefs([ev], items=[item])
    later = hydrated.updates[1]
    assert later.title_zh == "交易所被盗 4000 万美元"
    assert later.what_changed_zh == "Funds frozen"  # not a translation of this change


def test_only_tracked_events_are_queued_for_translation():
    single = event(update(0, "Lonely story"))
    tracked = event(update(0, "Hack reported"), update(1, "Funds frozen", kind=EventUpdateType.RESPONSE, zh="资金已冻结"))
    assert not is_tracked(single) and is_tracked(tracked)
    assert untranslated_texts([single, tracked]) == ["Hack reported"]


class Client:
    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = 0

    async def complete(self, **kwargs):
        self.calls += 1
        items = json.loads(kwargs["user"].split("\n\n", 1)[1])["items"]
        return json.dumps({"translations": [
            {"id": row["id"], "text": self.mapping.get(row["text"], row["text"])} for row in items
        ]})


def test_translation_is_validated_before_it_reaches_a_page():
    texts = ["Hack drains $40 million", "Exchange pauses withdrawals", "Still English"]
    client = Client({
        "Hack drains $40 million": "黑客盗走 4000 万美元",
        "Exchange pauses withdrawals": "交易所暂停提现，损失 9 亿美元",  # invented figure
    })
    result = asyncio.run(translate_texts(client, texts))
    assert result == {"Hack drains $40 million": "黑客盗走 4000 万美元"}

    tracked = event(update(0, "Hack drains $40 million"), update(1, "Exchange pauses withdrawals", kind=EventUpdateType.RESPONSE))
    [done], changed = apply_zh_translations([tracked], result)
    assert changed >= 3
    assert done.title_zh == "黑客盗走 4000 万美元"
    assert done.updates[1].title_zh == "Exchange pauses withdrawals"


def test_single_report_event_pages_are_not_indexed():
    from src.site_pages import render_event_page

    single = render_event_page(event(update(0, "Lonely story", zh="孤立报道")), "zh")
    tracked = render_event_page(
        event(update(0, "Hack", zh="被盗"), update(1, "Frozen", kind=EventUpdateType.RESPONSE, zh="冻结")), "zh"
    )
    assert "noindex: true" in single.split("---", 2)[1]
    assert "noindex" not in tracked.split("---", 2)[1]


def test_daily_pill_only_for_events_that_developed():
    from src.web_feed import _thread_html

    story = translated_item(0)
    story.metadata.update(event_id="evt_sample1", event_update_id="upd_node00")
    assert _thread_html(story, "zh") == ""
    story.metadata["event_updates"] = 1
    assert _thread_html(story, "zh") == ""
    story.metadata["event_updates"] = 3
    html = _thread_html(story, "zh")
    assert "持续追踪 · 3 次进展" in html and "/events/evt_sample1/#upd_node00" in html
