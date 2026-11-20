"""Publish one compact daily edition to a Telegram channel."""

from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Iterable
from urllib.parse import urlsplit

import httpx
from rich.console import Console

from ..models import ContentItem, TelegramDeliveryConfig


class TelegramDeliveryStatus(str, Enum):
    """Outcome of one Telegram delivery attempt."""

    SUCCESS = "success"
    SKIPPED = "skipped"
    FAILURE = "failure"


@dataclass(frozen=True)
class TelegramDeliveryResult:
    """Sanitized delivery result safe for logs and public run reports."""

    status: TelegramDeliveryStatus
    detail: str = ""
    message_length: int = 0
    message_id: int | None = None


_MARKDOWN_LINK = re.compile(r"\[([^]]+)]\([^)]*\)")
_HTML_TAG = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")
_CHANNEL_USERNAME = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,63}$")
_BRIEF_HARD_LIMIT = 420


def _plain_text(value: object) -> str:
    """Flatten stored Markdown/HTML into a compact Telegram-safe sentence."""
    text = _MARKDOWN_LINK.sub(r"\1", str(value or ""))
    text = _HTML_TAG.sub(" ", text)
    text = text.replace("**", "").replace("__", "").replace("`", "")
    return _WHITESPACE.sub(" ", text).strip()


def _shorten(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[: max(1, limit - 1)].rstrip() + "…"


def _first_complete_sentence(value: object, language: str) -> str:
    """Return one complete lead sentence, with a bounded malformed fallback."""
    text = _plain_text(value)
    if not text:
        return ''
    match = re.match('.*?[。！？!?]+[”’」』】）]?', text)
    sentence = match.group(0).strip() if match else text
    if len(sentence) <= _BRIEF_HARD_LIMIT:
        return sentence
    prefix = sentence[:_BRIEF_HARD_LIMIT]
    boundary = max((prefix.rfind(mark) for mark in '，；：,;:'))
    if boundary >= _BRIEF_HARD_LIMIT // 2:
        return prefix[:boundary + 1].rstrip() + '…'
    return _shorten(sentence, _BRIEF_HARD_LIMIT)


def _normalize_chat_id(value: str) -> str:
    """Accept Bot API IDs, usernames, and common public-channel URLs."""
    raw = str(value or "").strip().strip('"\'')
    if not raw:
        return ""
    candidate = raw
    if not raw.startswith(("http://", "https://")) and raw.lower().startswith(
        ("t.me/", "telegram.me/")
    ):
        candidate = "https://" + raw
    if candidate.startswith(("http://", "https://")):
        parsed = urlsplit(candidate)
        if parsed.netloc.lower() in {
            "t.me",
            "www.t.me",
            "telegram.me",
            "www.telegram.me",
        }:
            parts = [part for part in parsed.path.split("/") if part]
            if parts and parts[0] == "s":
                parts = parts[1:]
            if parts and _CHANNEL_USERNAME.fullmatch(parts[0]):
                return "@" + parts[0]
    if raw.startswith("@") and _CHANNEL_USERNAME.fullmatch(raw[1:]):
        return raw
    if _CHANNEL_USERNAME.fullmatch(raw):
        return "@" + raw
    return raw


def _safe_http_url(value: object) -> str | None:
    raw = str(value or "").strip()
    parsed = urlsplit(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return raw


def _redact(value: str, *sensitive_values: str) -> str:
    redacted = value
    for sensitive in sensitive_values:
        if sensitive:
            redacted = redacted.replace(sensitive, "<redacted>")
    return redacted


class TelegramEditionPublisher:
    """Render and send a single HTML-formatted Telegram channel message."""

    def __init__(
        self,
        config: TelegramDeliveryConfig,
        *,
        console: Console | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.config = config
        self.console = console or Console()
        self.transport = transport

    def _credentials(self) -> tuple[str, str]:
        token = os.getenv(self.config.bot_token_env, "").strip()
        channel_id = _normalize_chat_id(
            os.getenv(self.config.channel_id_env, "")
        )
        return token, channel_id

    def build_message(self, items: Iterable[ContentItem], *, date: str, total_candidates: int, language: str) -> str:
        """Build one bounded message without cutting through HTML entities."""
        if language != 'zh':
            raise ValueError('Only Chinese daily distribution is supported')
        selected = list(items)
        is_zh = True
        title = f'稀有News 日报 · {date}'
        overview = f'今日 {len(selected)} 条重点资讯'
        header = f'<b>{html.escape(title)}</b>\n{html.escape(overview)}'
        site_url = self.config.site_url.rstrip('/') + '/'
        footer = f'\n\n<a href="{html.escape(site_url, quote=True)}">阅读完整日报 →</a>\n<a href="https://x.com/ohxiyu">关注 @ohxiyu</a>'
        empty = '\n\n今日暂无达到展示阈值的重要资讯。'
        if not selected:
            return header + empty + footer
        entries: list[dict[str, str]] = []
        visible = selected[:self.config.max_items]
        omitted = len(selected) - len(visible)
        for index, item in enumerate(visible, start=1):
            localized_title = item.metadata.get(f'title_{language}') or item.title
            item_title = _shorten(_plain_text(localized_title), 120)
            item_url = _safe_http_url(item.url)
            escaped_title = html.escape(item_title)
            title_markup = f'<a href="{html.escape(item_url, quote=True)}">{escaped_title}</a>' if item_url else escaped_title
            score = f'{item.ai_score:g}' if item.ai_score is not None else '—'
            headline = f'<b>{index:02d}</b> {title_markup} · <code>{score}</code>'
            brief_value = item.metadata.get(f'detailed_summary_{language}') or item.metadata.get('detailed_summary') or item.ai_summary or ''
            brief = _first_complete_sentence(brief_value, language) if index <= self.config.featured_items else ''
            entries.append({'headline': headline, 'brief': brief})

        def compose() -> str:
            featured = [entry['headline'] + '\n' + html.escape(entry['brief']) for entry in entries if entry['brief']]
            compact = [entry['headline'] for entry in entries if not entry['brief']]
            sections = [header]
            sections.extend(featured)
            if compact:
                more_label = '更多'
                sections.append(f'<b>{more_label}</b>\n' + '\n'.join(compact))
            if omitted:
                omission = f'另有 {omitted} 条，请在网站查看。'
                sections.append(f'<i>{omission}</i>')
            return '\n\n'.join(sections) + footer
        message = compose()
        while len(message) > self.config.max_message_chars and len(entries) > self.config.featured_items:
            entries.pop()
            omitted += 1
            message = compose()
        for entry in reversed(entries):
            if len(message) <= self.config.max_message_chars:
                break
            if entry['brief']:
                entry['brief'] = ''
                message = compose()
        while len(message) > self.config.max_message_chars and entries:
            entries.pop()
            omitted += 1
            message = compose()
        return message

    async def send_daily_edition(
        self,
        items: Iterable[ContentItem],
        *,
        date: str,
        total_candidates: int,
        language: str,
    ) -> TelegramDeliveryResult:
        """Send one edition or safely report why it was skipped/failed."""
        if not self.config.enabled or language not in self.config.languages:
            return TelegramDeliveryResult(TelegramDeliveryStatus.SKIPPED)

        token, channel_id = self._credentials()
        if not token or not channel_id:
            missing = []
            if not token:
                missing.append(self.config.bot_token_env)
            if not channel_id:
                missing.append(self.config.channel_id_env)
            return TelegramDeliveryResult(
                TelegramDeliveryStatus.SKIPPED,
                "Missing environment variable(s): " + ", ".join(missing),
            )

        message = self.build_message(
            items,
            date=date,
            total_candidates=total_candidates,
            language=language,
        )
        return await self.send_html(message, label="daily edition")

    async def send_html(self, message: str, *, label: str = "message") -> TelegramDeliveryResult:
        """Send one already-built HTML message with the same gating and redaction."""
        if not self.config.enabled:
            return TelegramDeliveryResult(TelegramDeliveryStatus.SKIPPED)
        token, channel_id = self._credentials()
        if not token or not channel_id:
            return TelegramDeliveryResult(
                TelegramDeliveryStatus.SKIPPED,
                "Missing Telegram bot token or channel id",
            )
        endpoint = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": channel_id,
            "text": message,
            "parse_mode": "HTML",
            "link_preview_options": {"is_disabled": True},
        }
        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                transport=self.transport,
            ) as client:
                response = await client.post(endpoint, json=payload)
            data = response.json()
            if not isinstance(data, dict):
                return TelegramDeliveryResult(
                    TelegramDeliveryStatus.FAILURE,
                    f"Telegram returned an invalid response (HTTP {response.status_code})",
                    message_length=len(message),
                )
            if response.is_success and data.get("ok") is True:
                result = data.get("result")
                message_id = result.get("message_id") if isinstance(result, dict) else None
                self.console.print(f"[green]✈️ Telegram {label} sent.[/green]")
                return TelegramDeliveryResult(
                    TelegramDeliveryStatus.SUCCESS,
                    message_length=len(message),
                    message_id=message_id if type(message_id) is int and message_id > 0 else None,
                )
            error_code = data.get("error_code", response.status_code)
            description = _redact(
                _shorten(_plain_text(data.get("description", "")), 160),
                token,
                channel_id,
            )
            if "chat not found" in description.lower():
                description = (
                    "chat not found; set TELEGRAM_CHANNEL_ID to @channelname "
                    "or the -100… numeric ID, and confirm the bot is a channel admin"
                )
            return TelegramDeliveryResult(
                TelegramDeliveryStatus.FAILURE,
                f"Telegram API error {error_code}: {description or 'request rejected'}",
                message_length=len(message),
            )
        except (httpx.HTTPError, ValueError) as exc:
            return TelegramDeliveryResult(
                TelegramDeliveryStatus.FAILURE,
                f"Telegram request failed: {type(exc).__name__}",
                message_length=len(message),
            )
        except Exception as exc:
            return TelegramDeliveryResult(
                TelegramDeliveryStatus.FAILURE,
                f"Telegram request failed unexpectedly: {type(exc).__name__}",
                message_length=len(message),
            )
