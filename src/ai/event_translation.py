"""Translate the English text still shown on Chinese event pages."""

from __future__ import annotations

import json
import logging
from typing import Sequence

from .prompts import EVENT_TRANSLATION_SYSTEM, EVENT_TRANSLATION_USER
from .utils import parse_json_response

logger = logging.getLogger(__name__)

# One call stays well inside the stage's output budget.
BATCH_CHARS = 3000
BATCH_ITEMS = 12


def _batches(texts: Sequence[str]) -> list[list[str]]:
    batches: list[list[str]] = []
    current: list[str] = []
    size = 0
    for text in texts:
        if current and (size + len(text) > BATCH_CHARS or len(current) >= BATCH_ITEMS):
            batches.append(current)
            current, size = [], 0
        current.append(text)
        size += len(text)
    if current:
        batches.append(current)
    return batches


def _acceptable(source: str, translated: str) -> bool:
    from ..event_pipeline import has_cjk
    from ..services.x_delivery import unsupported_figures

    if not has_cjk(translated) or len(translated) > 2 * len(source) + 40:
        return False
    # A translation may convert units but must not introduce a figure.
    return not unsupported_figures(translated, [source])


async def translate_texts(
    client, texts: Sequence[str], *, max_calls: int = 4
) -> dict[str, str]:
    """Best effort: returns only translations that passed validation."""
    result: dict[str, str] = {}
    for batch in _batches(texts)[:max_calls]:
        ids = {f"t{index}": text for index, text in enumerate(batch)}
        payload = json.dumps(
            {"items": [{"id": key, "text": text} for key, text in ids.items()]},
            ensure_ascii=False,
        )
        try:
            response = await client.complete(
                system=EVENT_TRANSLATION_SYSTEM,
                user=EVENT_TRANSLATION_USER.format(payload=payload),
                response_format="json",
            )
            parsed = parse_json_response(response)
        except Exception as exc:  # noqa: BLE001 - keep the English text
            logger.warning("Event translation batch failed: %s", type(exc).__name__)
            continue
        rows = parsed.get("translations") if isinstance(parsed, dict) else None
        for row in rows if isinstance(rows, list) else []:
            if not isinstance(row, dict):
                continue
            source = ids.get(str(row.get("id")))
            translated = " ".join(str(row.get("text") or "").split())
            if source and _acceptable(source, translated):
                result[source] = translated
    return result
