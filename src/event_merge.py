"""Fold events that one real-world event was split into.

Retrieval and the per-pair classifier are deliberately conservative, so a
fast-moving story (an exchange hack covered by dozens of outlets) can end up
as many single-report events. This pass groups recent events that share a
named subject, asks the model which are the same root incident and which
reports describe the same stage, and folds each group into its oldest event.
Folded event URLs redirect to the survivor (``merged_event_ids``).
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Mapping, MutableMapping, Sequence

from .events import (
    EventUpdate,
    EventUpdateType,
    TrackedEvent,
    signature_for_event,
)

logger = logging.getLogger(__name__)

# Only recent events are regrouped; an old event is history, not a split.
MERGE_WINDOW = timedelta(days=14)
# Entries sent in one call; the most recently changed win.
MAX_GROUP = 30
MAX_CALLS = 3
REVIEWS_KEY = "merge_reviews"


@dataclass
class MergeStage:
    ids: list[str]
    update_type: EventUpdateType


@dataclass
class MergePlan:
    title_zh: str
    title_en: str
    stages: list[MergeStage] = field(default_factory=list)

    @property
    def ids(self) -> list[str]:
        return [event_id for stage in self.stages for event_id in stage.ids]


@dataclass
class MergeResult:
    groups_reviewed: int = 0
    events_folded: int = 0
    calls_failed: int = 0


def anchors_for(event: TrackedEvent) -> set[str]:
    """Named subjects the event is about: a title entity echoed in its tags."""
    signature = signature_for_event(event)
    return set(signature.entities) & set(signature.topics)


def merge_groups(
    events: Sequence[TrackedEvent],
    *,
    now: datetime,
    reviewed: Mapping[str, Sequence[str]] | None = None,
    window: timedelta = MERGE_WINDOW,
) -> list[tuple[str, list[TrackedEvent]]]:
    """Recent events sharing an anchor, only where something is new.

    A group is worth a call when it holds an event the previous review of
    that anchor did not see. The biggest news goes first: groups whose
    unseen events score highest, then those with the most unseen events.
    """
    reviewed = reviewed or {}
    recent = [
        event for event in events if now - event.last_material_change_at <= window
    ]
    by_anchor: dict[str, list[TrackedEvent]] = defaultdict(list)
    for event in recent:
        for anchor in anchors_for(event):
            by_anchor[anchor].append(event)
    ranked = []
    for anchor, members in by_anchor.items():
        if len(members) < 2:
            continue
        members = sorted(
            members, key=lambda e: e.last_material_change_at, reverse=True
        )[:MAX_GROUP]
        seen = set(reviewed.get(anchor, ()))
        unseen = [event for event in members if event.event_id not in seen]
        if unseen:
            top = max(_score(event) for event in unseen)
            ranked.append((top, len(unseen), anchor, members))
    ranked.sort(key=lambda row: (-row[0], -row[1], row[2]))
    return [(anchor, members) for _, _, anchor, members in ranked]


def _score(event: TrackedEvent) -> float:
    return max(
        (u.importance_score for u in event.updates if u.importance_score is not None),
        default=0.0,
    )


def _entry(event: TrackedEvent) -> dict:
    first = event.updates[0]
    latest = event.updates[-1]
    return {
        "id": event.event_id,
        "first_seen": event.first_seen_at.date().isoformat(),
        "title": event.title_en or event.title_zh,
        "first_report": (first.what_changed_en or first.what_changed_zh)[:280],
        "latest_state": (latest.current_state_en or latest.current_state_zh)[:200],
    }


def parse_merge_plan(payload: object, allowed: set[str]) -> list[MergePlan]:
    """Keep only well-formed events built from allowed, unrepeated IDs."""
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        return []
    used: set[str] = set()
    plans: list[MergePlan] = []
    for row in payload["events"]:
        if not isinstance(row, dict) or not isinstance(row.get("stages"), list):
            continue
        stages: list[MergeStage] = []
        claimed: set[str] = set()
        for index, stage in enumerate(row["stages"]):
            if not isinstance(stage, dict) or not isinstance(stage.get("ids"), list):
                continue
            ids = [
                str(value)
                for value in stage["ids"]
                if str(value) in allowed and str(value) not in used | claimed
            ]
            ids = list(dict.fromkeys(ids))
            if not ids:
                continue
            claimed.update(ids)
            try:
                update_type = EventUpdateType(str(stage.get("update_type") or ""))
            except ValueError:
                update_type = EventUpdateType.CONFIRMATION
            stages.append(MergeStage(ids=ids, update_type=update_type))
        if len(claimed) < 2:
            continue
        stages[0].update_type = EventUpdateType.INITIAL
        for stage in stages[1:]:
            if stage.update_type is EventUpdateType.INITIAL:
                stage.update_type = EventUpdateType.CONFIRMATION
        used.update(claimed)
        plans.append(
            MergePlan(
                title_zh=str(row.get("title_zh") or "").strip(),
                title_en=str(row.get("title_en") or "").strip(),
                stages=stages,
            )
        )
    return plans


def _unique(values) -> list:
    return list(dict.fromkeys(values))


def _fold_into(head: EventUpdate, others: Sequence[EventUpdate]) -> EventUpdate:
    """Attach other reports of the same stage to ``head`` as its sources."""
    sources = {source.url: source for source in head.sources}
    references = {reference.url: reference for reference in head.references}
    story_ids = list(head.story_ids)
    for update in others:
        story_ids.extend(update.story_ids)
        for source in update.sources:
            sources.setdefault(source.url, source)
        for reference in update.references:
            references.setdefault(reference.url, reference)
    scores = [u.importance_score for u in (head, *others) if u.importance_score is not None]
    return head.model_copy(
        update={
            "story_ids": _unique(story_ids),
            "sources": list(sources.values()),
            "references": list(references.values()),
            "importance_score": max(scores) if scores else None,
        },
        deep=True,
    )


def _title(plan: MergePlan, members: Sequence[TrackedEvent], language: str) -> str:
    from .event_pipeline import has_cjk
    from .services.x_delivery import unsupported_figures

    candidate = plan.title_zh if language == "zh" else plan.title_en
    if candidate and len(candidate) <= 80 and (language != "zh" or has_cjk(candidate)):
        evidence = [
            text
            for event in members
            for update in event.updates
            for text in (
                update.title_zh, update.title_en, update.what_changed_zh,
                update.what_changed_en, update.detailed_summary_zh,
                update.detailed_summary_en,
            )
            if text
        ]
        if not unsupported_figures(candidate, evidence):
            return candidate
    return ""


def fold_events(members: Sequence[TrackedEvent], plan: MergePlan) -> TrackedEvent:
    """One event from ``members``, keeping the oldest event's identity."""
    from .event_pipeline import _status_after_update, has_cjk
    from .events import EventStatus

    by_id = {event.event_id: event for event in members}
    survivor = min(members, key=lambda e: (e.first_seen_at, e.event_id))
    updates: list[EventUpdate] = []
    for stage in plan.stages:
        stage_events = sorted(
            (by_id[event_id] for event_id in stage.ids),
            key=lambda e: (e.first_seen_at, e.event_id),
        )
        primary, rest = stage_events[0], stage_events[1:]
        head = _fold_into(
            primary.updates[0],
            [update for event in rest for update in event.updates],
        )
        if head.update_type is EventUpdateType.INITIAL or stage is plan.stages[0]:
            head = head.model_copy(update={"update_type": stage.update_type})
        updates.extend([head, *primary.updates[1:]])
    updates = [
        update.model_copy(update={"event_id": survivor.event_id}, deep=True)
        for update in updates
    ]
    updates.sort(key=lambda u: (u.occurred_at, u.first_seen_at, u.update_id))
    # Only the earliest update opens the event.
    for index, update in enumerate(updates):
        if index and update.update_type is EventUpdateType.INITIAL:
            updates[index] = update.model_copy(
                update={"update_type": EventUpdateType.CONFIRMATION}
            )
        elif not index and update.update_type is not EventUpdateType.INITIAL:
            updates[index] = update.model_copy(
                update={"update_type": EventUpdateType.INITIAL}
            )
    status = EventStatus.MONITORING
    for update in updates:
        status = _status_after_update(status, update.update_type)
    latest = max(members, key=lambda e: (e.last_material_change_at, e.event_id))
    title_zh = _title(plan, members, "zh") or next(
        (e.title_zh for e in (survivor, *members) if has_cjk(e.title_zh)),
        survivor.title_zh,
    )
    title_en = _title(plan, members, "en") or survivor.title_en
    absorbed = [e for e in members if e.event_id != survivor.event_id]
    merged = survivor.model_dump()
    merged.update(
        {
            "status": status,
            "title_zh": title_zh,
            "title_en": title_en,
            "current_state_zh": latest.current_state_zh or survivor.current_state_zh,
            "current_state_en": latest.current_state_en or survivor.current_state_en,
            "entities": sorted({key for e in members for key in e.entities}),
            "identifiers": sorted({key for e in members for key in e.identifiers}),
            "topics": sorted({key for e in members for key in e.topics}),
            "first_seen_at": min(e.first_seen_at for e in members),
            "last_updated_at": max(e.last_updated_at for e in members),
            "last_material_change_at": max(
                e.last_material_change_at for e in members
            ),
            "confidence": min(e.confidence for e in members),
            "legacy_thread_ids": _unique(
                thread for e in (survivor, *absorbed) for thread in e.legacy_thread_ids
            ),
            "merged_event_ids": _unique(
                [
                    *survivor.merged_event_ids,
                    *(e.event_id for e in absorbed),
                    *(old for e in absorbed for old in e.merged_event_ids),
                ]
            ),
            "updates": [update.model_dump() for update in updates],
        }
    )
    return TrackedEvent.model_validate(merged)


def apply_plans(
    events: Sequence[TrackedEvent], plans: Sequence[MergePlan]
) -> tuple[list[TrackedEvent], int]:
    """Replace each planned group with its folded event."""
    by_id = {event.event_id: event for event in events}
    removed: set[str] = set()
    folded_events: list[TrackedEvent] = []
    folded = 0
    for plan in plans:
        ids = [event_id for event_id in plan.ids if event_id in by_id and event_id not in removed]
        if len(ids) < 2 or len(ids) != len(plan.ids):
            continue
        try:
            merged = fold_events([by_id[event_id] for event_id in ids], plan)
        except ValueError as exc:  # An invalid fold keeps the originals.
            logger.warning("Event merge skipped: %s", exc)
            continue
        removed.update(ids)
        folded_events.append(merged)
        folded += len(ids) - 1
    kept = [event for event in events if event.event_id not in removed]
    return kept + folded_events, folded


async def request_plans(
    client, anchor: str, members: Sequence[TrackedEvent]
) -> list[MergePlan]:
    from .ai.prompts import EVENT_MERGE_SYSTEM, EVENT_MERGE_USER
    from .ai.utils import parse_json_response

    entries = json.dumps([_entry(e) for e in members], ensure_ascii=False, indent=1)
    response = await client.complete(
        system=EVENT_MERGE_SYSTEM,
        user=EVENT_MERGE_USER.format(anchor=anchor, entries=entries),
        response_format="json",
    )
    return parse_merge_plan(
        parse_json_response(response), {e.event_id for e in members}
    )


async def merge_split_events(
    events: Sequence[TrackedEvent],
    client,
    metadata: MutableMapping[str, object],
    *,
    now: datetime,
    max_calls: int = MAX_CALLS,
) -> tuple[list[TrackedEvent], MergeResult]:
    """Bounded best-effort pass; any failure leaves the catalog unchanged."""
    result = MergeResult()
    reviews = dict(metadata.get(REVIEWS_KEY) or {})
    working = list(events)
    for anchor, members in merge_groups(working, now=now, reviewed=reviews)[:max_calls]:
        # An earlier fold this run may have absorbed some members.
        alive = {event.event_id for event in working}
        members = [event for event in members if event.event_id in alive]
        if len(members) < 2:
            continue
        try:
            plans = await request_plans(client, anchor, members)
        except Exception as exc:  # noqa: BLE001 - merging is best effort
            logger.warning("Event merge review failed for %s: %s", anchor, exc)
            result.calls_failed += 1
            continue
        working, folded = apply_plans(working, plans)
        result.groups_reviewed += 1
        result.events_folded += folded
        alive = {event.event_id for event in working}
        reviews[anchor] = sorted(e.event_id for e in members if e.event_id in alive)
    # Forget anchors whose events have all left the window.
    live = {anchor for event in working for anchor in anchors_for(event)}
    metadata[REVIEWS_KEY] = {k: v for k, v in sorted(reviews.items()) if k in live}
    return working, result


def merged_aliases(events: Sequence[TrackedEvent]) -> dict[str, str]:
    """Old event ID → the event that now carries its history."""
    return {
        old: event.event_id for event in events for old in event.merged_event_ids
    }
