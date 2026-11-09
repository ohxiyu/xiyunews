"""Small escaping and Chinese text helpers for the daily reader."""
from __future__ import annotations
from datetime import timezone
import html
import re
from urllib.parse import quote,urlsplit
from zoneinfo import ZoneInfo
from .models import ContentItem
_URL_SAFE_CHARS = ":/?#[]@!$&'*,;=~%+"
_LABELS={'zh':{'crypto':'Crypto','technology':'AI 科技','policy':'政策','discussion':'原始讨论','references':'参考资料'}}


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)

def _summary_sentence_units(value: str, language: str) -> list[str]:
    """Split a legacy one-line summary without breaking abbreviations."""
    text = re.sub(r"\s+", " ", value).strip()
    if not text:
        return []
    matches = re.findall(r".*?(?:[。！？!?]+[”’」』】）]?|$)", text)
    return [part.strip() for part in matches if part.strip()]


def _summary_paragraphs(value: str, language: str) -> list[str]:
    """Return compact semantic paragraphs for current and legacy summaries."""
    text = str(value or "").strip()
    if not text:
        return []

    explicit = [
        re.sub(r"\s+", " ", block).strip()
        for block in re.split(r"(?:\r?\n\s*)+", text)
        if block.strip()
    ]
    if len(explicit) > 1:
        return explicit

    sentences = _summary_sentence_units(explicit[0], language)
    joiner = "" if language == "zh" else " "
    if len(sentences) < 3:
        return [joiner.join(sentences)] if sentences else []

    target = 130 if language == "zh" else 240
    lead_minimum = 28 if language == "zh" else 70
    paragraphs: list[str] = []
    remaining = sentences
    if len(sentences[0]) >= lead_minimum:
        paragraphs.append(sentences[0])
        remaining = sentences[1:]

    current: list[str] = []
    current_length = 0
    for sentence in remaining:
        separator_length = len(joiner) if current else 0
        projected = current_length + separator_length + len(sentence)
        if current and (projected > target or len(current) >= 3):
            paragraphs.append(joiner.join(current))
            current = []
            current_length = 0
        current.append(sentence)
        current_length += (len(joiner) if current_length else 0) + len(sentence)
    if current:
        paragraphs.append(joiner.join(current))
    return paragraphs

def _summary_html(value: str, language: str) -> str:
    paragraphs = _summary_paragraphs(value, language)
    return (
        '<div class="story-summary-body">'
        + "".join(f"<p>{_escape(paragraph)}</p>" for paragraph in paragraphs)
        + "</div>"
    )

def _safe_url(value: object) -> str | None:
    raw = str(value).strip()
    if not raw or any(ord(char) < 32 or ord(char) == 127 for char in raw):
        return None
    try:
        parsed = urlsplit(raw)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            return None
        parsed.port
    except (TypeError, ValueError):
        return None
    return html.escape(quote(raw, safe=_URL_SAFE_CHARS), quote=True)

def category_label(category: str, language: str) -> str:
    """One display vocabulary for feed, event, and entity pages."""
    return _LABELS.get(language, _LABELS["zh"]).get(category, category)

def _top_level_category(item: ContentItem) -> str:
    category = str(item.metadata.get("category") or "").strip().lower()
    if (
        category.startswith(("ai-", "tech-"))
        or category in {"ai", "technology", "tech-community"}
    ):
        return "technology"
    if (
        "regulation" in category
        or category.startswith(("macro-", "policy"))
        or category == "policy"
    ):
        return "policy"
    return "crypto"

def _localized_text(item: ContentItem, key: str, language: str) -> str:
    metadata = item.metadata
    return str(
        metadata.get(f"{key}_{language}")
        or metadata.get(key)
        or ""
    ).strip()

def _localized_title(item: ContentItem, language: str) -> str:
    return str(
        item.metadata.get(f"title_{language}")
        or item.title
    ).strip()

def _source_html(
    item: ContentItem,
    *,
    language: str,
    display_timezone: ZoneInfo,
) -> str:
    labels = _LABELS[language]
    metadata = item.metadata
    source_name = (
        metadata.get("feed_name")
        or (
            f"r/{metadata['subreddit']}"
            if metadata.get("subreddit")
            else None
        )
        or item.author
        or "unknown"
    )
    story_url = _safe_url(item.url)
    source_label = _escape(source_name)
    if story_url:
        source_label = (
            f'<a class="source-link" href="{story_url}" '
            'target="_blank" rel="noopener noreferrer">'
            f"{source_label}</a>"
        )

    published_at = item.published_at
    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)
    published_at = published_at.astimezone(display_timezone)
    published_label = f"{published_at:%m.%d %H:%M} CST"

    parts = [
        _escape(item.source_type.value),
        source_label,
        (
            f'<time datetime="{_escape(published_at.isoformat())}">'
            f"{_escape(published_label)}</time>"
        ),
    ]
    discussion_url = metadata.get("discussion_url")
    safe_discussion_url = _safe_url(discussion_url) if discussion_url else None
    if (
        safe_discussion_url
        and str(discussion_url) != str(item.url)
    ):
        parts.append(
            f'<a href="{safe_discussion_url}" target="_blank" '
            f'rel="noopener noreferrer">{labels["discussion"]}</a>'
        )
    return " · ".join(parts)

def _references_html(item: ContentItem, language: str) -> str:
    references = item.metadata.get("sources") or []
    if not references:
        return ""
    entries: list[str] = []
    for reference in references:
        title = _escape(reference.get("title") or reference.get("url") or "")
        url = _safe_url(reference.get("url") or "")
        if url:
            entries.append(
                f'<li><a href="{url}" target="_blank" '
                f'rel="noopener noreferrer">{title}</a></li>'
            )
        elif title:
            entries.append(f"<li>{title}</li>")
    if not entries:
        return ""
    return (
        f'<section><h3>{_LABELS[language]["references"]}</h3>'
        f'<ul>{"".join(entries)}</ul></section>'
    )


def render_web_feed(items,*,date,total_fetched=0,language='zh',display_timezone='Asia/Shanghai'):
    if language!='zh':raise ValueError('Only the Chinese daily edition is supported')
    from .core_site import render_core_feed
    return render_core_feed(list(items),date=date,display_timezone=display_timezone)
