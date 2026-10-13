"""AI boundary for deciding how a new story relates to an event candidate."""

from __future__ import annotations

import json
import hashlib

from pydantic import ValidationError

from ..events import EventRelation, EventRelationDecision, StoryEvidence, TrackedEvent
from .client import AIClient
from .prompts import EVENT_RELATION_SYSTEM, EVENT_RELATION_USER
from .utils import parse_json_response
from .result_cache import AnalysisResultCache


class EventRelationError(ValueError):
    """Raised when a semantic event decision is missing or invalid."""


def compact_context(value):
    """Remove only exact duplicate translations, never omit distinct facts."""
    if isinstance(value, list):
        return [compact_context(row) for row in value]
    if not isinstance(value, dict):
        return value
    result = {key: compact_context(row) for key, row in value.items()}
    for key in list(result):
        if key.endswith("_en") and result.get(key) and result.get(key[:-3] + "_zh") == result[key]:
            result.pop(key)
    return result


def relation_user(event: TrackedEvent, story: StoryEvidence) -> str:
    return EVENT_RELATION_USER.format(
        event=json.dumps(compact_context(_event_context(event)), ensure_ascii=False, separators=(",", ":")),
        story=json.dumps(compact_context(_story_context(story)), ensure_ascii=False, separators=(",", ":")),
    )


def relation_cache_input(event: TrackedEvent, story: StoryEvidence, user: str) -> str:
    # Full evidence/catalog revision also invalidates changes omitted from the
    # bounded model context (e.g. earlier history, new source references).
    revision = hashlib.sha256(json.dumps([event.model_dump(mode="json"), story.model_dump(mode="json")],
        sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return revision + "\n" + user


def _event_context(event: TrackedEvent) -> dict:
    recent_updates = event.updates[-5:]
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "status": event.status.value,
        "title_zh": event.title_zh,
        "title_en": event.title_en,
        "current_state_zh": event.current_state_zh,
        "current_state_en": event.current_state_en,
        "entities": event.entities,
        "identifiers": event.identifiers,
        "recent_updates": [
            {
                "update_id": update.update_id,
                "occurred_at": update.occurred_at.isoformat(),
                "update_type": update.update_type.value,
                "what_changed_zh": update.what_changed_zh,
                "what_changed_en": update.what_changed_en,
            }
            for update in recent_updates
        ],
    }


def _story_context(story: StoryEvidence) -> dict:
    return {
        "story_id": story.story_id,
        "url": story.url,
        "published_at": story.published_at.isoformat(),
        "title_zh": story.title_zh,
        "title_en": story.title_en,
        "summary_zh": story.summary_zh,
        "summary_en": story.summary_en,
        "tags": story.tags,
        "source_label": story.source_label,
        "source_excerpt": story.source_excerpt,
        "evidence_quality": story.evidence_quality,
        "entities": story.entities,
        "identifiers": story.identifiers,
    }


def parse_event_relation(response: str, *, event_id: str) -> EventRelationDecision:
    payload = parse_json_response(response)
    if not isinstance(payload, dict):
        raise EventRelationError("event relation response was not a JSON object")
    try:
        decision = EventRelationDecision.model_validate(payload)
    except ValidationError as exc:
        raise EventRelationError("event relation response failed validation") from exc
    if decision.candidate_event_id != event_id:
        raise EventRelationError("event relation response changed the candidate ID")
    return decision


async def classify_event_relation(
    client: AIClient,
    *,
    event: TrackedEvent,
    story: StoryEvidence,
    cache: AnalysisResultCache | None = None,
) -> EventRelationDecision:
    """Classify one prefiltered pair with a strict, auditable JSON contract."""
    user = relation_user(event, story)
    cache_input = relation_cache_input(event, story, user)
    def validate(payload: str) -> EventRelationDecision:
        decision = parse_event_relation(payload, event_id=event.event_id)
        if decision.relation is EventRelation.SAME_EVENT_UPDATE and story.evidence_quality == "headline_only":
            raise EventRelationError("headline-only evidence cannot confirm a material change")
        return decision
    if cache is not None:
        value = cache.get_relation(EVENT_RELATION_SYSTEM, cache_input)
        if value is not None:
            try:
                return validate(json.dumps(value, ensure_ascii=False))
            except (EventRelationError, ValueError):
                cache.discard_relation(EVENT_RELATION_SYSTEM, cache_input)
    response = await client.complete(
        system=EVENT_RELATION_SYSTEM,
        user=user,
        temperature=0.0,
        max_tokens=4096,
        response_format="json",
    )
    decision = validate(response)
    if cache is not None:
        cache.store_relation(EVENT_RELATION_SYSTEM, cache_input, decision.model_dump(mode="json"))
        # Preserve paid, validated work even if a later candidate fails.
        cache.save(export_json=False)
    return decision
