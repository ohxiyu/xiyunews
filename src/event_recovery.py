"""Repair exact published links from saved text, never reclassify an event."""
from __future__ import annotations

import copy
import hashlib
from typing import Iterable, Sequence

from .event_pipeline import (
    EVENT_CATALOG_PATH, _new_event, _stable_event_id, _stable_update_id,
    known_story_assignments, load_event_catalog, save_event_catalog, story_evidence,
)
from .events import EventUpdateType, TrackedEvent
from .models import ContentItem
from .publication_state import StateConflict, canonical


def recover_published_links(
    metadata: dict, events: Sequence[TrackedEvent], items: Iterable[ContentItem], *, edition: str,
) -> tuple[dict, list[TrackedEvent], int]:
    """Use the saved edition's exact membership, not a new semantic decision.

    Lost lifecycle classifications cannot be inferred from a public link.
    Reconstructed nodes use a conservative confirmation label, keep the saved
    wording and parent status/state, and record this limitation in the catalog.
    Unknown IDs, changed membership and ambiguous updates stop the whole batch.
    Inputs are untouched; the caller saves only a fully validated result.
    """
    result = {e.event_id: e.model_copy(deep=True) for e in events}
    assignments = known_story_assignments(list(result.values()))
    audit = copy.deepcopy(metadata)
    recovered = 0
    for item in items:
        event_id = str(item.metadata.get("event_id") or "")
        update_id = str(item.metadata.get("event_update_id") or "")
        if not event_id and not update_id:
            continue
        if not event_id or not update_id:
            raise StateConflict("incomplete published event reference: " + item.id)
        expected = (event_id, update_id)
        if item.id in assignments:
            if assignments[item.id] != expected:
                current_id, current_update = assignments[item.id]
                if current_update != update_id or event_id not in result[current_id].merged_event_ids:
                    raise StateConflict("published story already belongs to a different event: " + item.id)
                # A later legitimate merge keeps the exact node and redirects
                # the published old URL. It is not missing or reassigned.
            continue
        if not item.metadata.get("detailed_summary_zh") and not item.metadata.get("detailed_summary_en"):
            raise StateConflict("published recovery requires saved full text: " + item.id)
        initial_id = _stable_event_id(item.id)
        initial_update = _stable_update_id(initial_id, item.id)
        if update_id not in {initial_update, _stable_update_id(event_id, item.id)}:
            raise StateConflict("published update is not a provable stable ID: " + item.id)
        seed = _new_event(item, story_evidence(item))
        parent = result.get(event_id)
        classification = "initial_from_stable_identity"
        if parent is None:
            if event_id != initial_id or update_id != initial_update:
                raise StateConflict("cannot reconstruct an unknown parent event: " + item.id)
            result[event_id] = seed
        else:
            # A missing source in an existing node may be a duplicate report;
            # without its exact decision it must not be silently reconstructed.
            if any(u.update_id == update_id for u in parent.updates):
                raise StateConflict("published node exists with different source membership: " + item.id)
            update = seed.updates[0].model_copy(update={
                "event_id": event_id, "update_id": update_id,
                "update_type": EventUpdateType.CONFIRMATION,
                "confidence": 0.0,  # Original semantic confidence is unavailable.
            })
            changes = {
                "updates": sorted([*parent.updates, update], key=lambda u: (u.occurred_at, u.first_seen_at, u.update_id)),
                "last_updated_at": max(parent.last_updated_at, update.first_seen_at),
                "last_material_change_at": max(parent.last_material_change_at, update.first_seen_at),
            }
            if initial_id != event_id and update_id == initial_update:
                # Folding retains the initial node ID. The saved link proves
                # membership, but not the lost merge plan's lifecycle label.
                if initial_id in result or any(initial_id in e.merged_event_ids and e.event_id != event_id for e in result.values()):
                    raise StateConflict("folded identity conflicts with another event: " + item.id)
                changes["merged_event_ids"] = list(dict.fromkeys([*parent.merged_event_ids, initial_id]))
            result[event_id] = parent.model_copy(update=changes, deep=True)
            classification = "unavailable_confirmation_only_parent_state_preserved"
        audit.setdefault("published_link_recoveries", {})[item.id] = {
            "edition": edition, "event_id": event_id, "update_id": update_id,
            "classification": classification, "source": "saved_daily_edition",
            "public_item_sha256": hashlib.sha256(canonical(item.model_dump(mode="json")).encode()).hexdigest(),
        }
        assignments[item.id] = expected
        recovered += 1
    validated = [TrackedEvent.model_validate(e.model_dump()) for e in result.values()]
    if known_story_assignments(validated) != assignments:
        raise StateConflict("recovery changed unrelated event membership")
    return audit, validated, recovered


def recover_catalog_links(items: Sequence[ContentItem], *, edition: str) -> int:
    if not any(i.metadata.get("event_id") or i.metadata.get("event_update_id") for i in items):
        return 0
    metadata, events = load_event_catalog(EVENT_CATALOG_PATH)
    metadata, events, changed = recover_published_links(metadata, events, items, edition=edition)
    if changed:
        save_event_catalog(metadata, events, EVENT_CATALOG_PATH)
    return changed
