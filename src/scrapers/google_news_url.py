"""Best-effort resolution of Google News RSS redirect links.

Google News RSS entries link to ``news.google.com/rss/articles/<token>``
redirect pages instead of the publisher's article. Publishing those links
hurts readers (opaque URLs) and defeats cross-source URL deduplication,
because the same article fetched from the publisher's own feed never matches
the Google News redirect form.

For the common ``CBMi…`` token format, the token is a URL-safe base64
protobuf whose first field is the article URL, so it can be decoded locally
without any network round trip. Newer ``AU_yqL…`` tokens are opaque and
cannot be decoded offline; :func:`resolve_google_news_url_online` asks Google
for them (the same two requests the redirect page itself makes). Any failure
keeps the original link, so resolution can only improve an item.
"""

from __future__ import annotations

import base64
import json
import logging
import re
from urllib.parse import urlsplit

import httpx

logger = logging.getLogger(__name__)

_ARTICLE_PATH = re.compile(r"^/(?:rss/)?articles/([A-Za-z0-9_-]+)")

# Decoded CBMi… tokens start with these protobuf bytes: field 1 (varint) = 19,
# then field 4 (length-delimited string) holding the article URL.
_TOKEN_PREFIX = b"\x08\x13\x22"


def _read_varint(data: bytes, offset: int) -> tuple[int, int] | None:
    """Read one protobuf varint; returns (value, next_offset) or None."""
    value = 0
    shift = 0
    while offset < len(data) and shift <= 35:
        byte = data[offset]
        value |= (byte & 0x7F) << shift
        offset += 1
        if not byte & 0x80:
            return value, offset
        shift += 7
    return None


def resolve_google_news_url(url: str) -> str | None:
    """Return the publisher URL embedded in a Google News redirect link.

    Returns None when the link is not a decodable Google News article
    redirect, so callers can keep the original URL.
    """
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if (parsed.hostname or "").lower() != "news.google.com":
        return None
    match = _ARTICLE_PATH.match(parsed.path)
    if not match:
        return None

    token = match.group(1)
    try:
        raw = base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))
    except (ValueError, TypeError):
        return None
    if not raw.startswith(_TOKEN_PREFIX):
        return None

    varint = _read_varint(raw, len(_TOKEN_PREFIX))
    if varint is None:
        return None
    length, offset = varint
    if length <= 0 or offset + length > len(raw):
        return None
    try:
        candidate = raw[offset : offset + length].decode("utf-8")
    except UnicodeDecodeError:
        return None

    try:
        candidate_parts = urlsplit(candidate)
    except ValueError:
        return None
    if candidate_parts.scheme not in {"http", "https"}:
        return None
    host = (candidate_parts.hostname or "").lower()
    if not host or host == "news.google.com":
        return None
    return candidate


def canonicalize_entry_link(link: str) -> str:
    """Replace a Google News redirect link with the publisher URL if possible."""
    resolved = resolve_google_news_url(link)
    if resolved:
        logger.debug("Resolved Google News link %s -> %s", link, resolved)
        return resolved
    return link


_SIGNATURE = re.compile(r'data-n-a-sg="([^"]+)"')
_TIMESTAMP = re.compile(r'data-n-a-ts="(\d+)"')
_BATCH_URL = "https://news.google.com/_/DotsSplashUi/data/batchexecute"


def article_token(url: str) -> str | None:
    """The article token of a Google News redirect link, if it is one."""
    try:
        parsed = urlsplit(url)
    except ValueError:
        return None
    if (parsed.hostname or "").lower() != "news.google.com":
        return None
    match = _ARTICLE_PATH.match(parsed.path)
    return match.group(1) if match else None


def _publisher_url(candidate: object) -> str | None:
    if not isinstance(candidate, str):
        return None
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return None
    host = (parts.hostname or "").lower()
    if parts.scheme not in {"http", "https"} or not host:
        return None
    if host == "google.com" or host.endswith(".google.com"):
        return None
    return candidate


def _decoded_from_batch(body: str) -> str | None:
    """Pull the article URL out of a batchexecute response body."""
    text = body.lstrip()
    if text.startswith(")]}'"):
        text = text[4:]
    for chunk in (text.strip(), *text.splitlines()):
        chunk = chunk.strip()
        if not chunk.startswith("["):
            continue
        try:
            rows = json.loads(chunk)
        except ValueError:
            continue
        for row in rows if isinstance(rows, list) else ():
            if (
                isinstance(row, list)
                and len(row) > 2
                and row[0] == "wrb.fr"
                and isinstance(row[2], str)
            ):
                try:
                    payload = json.loads(row[2])
                except ValueError:
                    continue
                if isinstance(payload, list) and len(payload) > 1:
                    url = _publisher_url(payload[1])
                    if url:
                        return url
    return None


async def resolve_google_news_url_online(
    client: httpx.AsyncClient, url: str, *, timeout: float = 10.0
) -> str | None:
    """Resolve an opaque Google News link through Google's own endpoint.

    Returns None on any failure (network, 4xx/5xx, changed page format), so
    callers keep the original link.
    """
    local = resolve_google_news_url(url)
    if local:
        return local
    token = article_token(url)
    if not token:
        return None
    try:
        page_text = None
        for page in (
            f"https://news.google.com/articles/{token}",
            f"https://news.google.com/rss/articles/{token}",
        ):
            response = await client.get(page, timeout=timeout, follow_redirects=True)
            if response.status_code == 200:
                page_text = response.text
                break
        if page_text is None:
            return None
        signature = _SIGNATURE.search(page_text)
        timestamp = _TIMESTAMP.search(page_text)
        if not signature or not timestamp:
            return None
        request = json.dumps(
            [
                "garturlreq",
                [
                    ["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1,
                     None, None, None, None, None, 0, 1],
                    "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0,
                ],
                token,
                int(timestamp.group(1)),
                signature.group(1),
            ],
            separators=(",", ":"),
        )
        response = await client.post(
            _BATCH_URL,
            data={
                "f.req": json.dumps(
                    [[["Fbv4je", request, None, "generic"]]], separators=(",", ":")
                )
            },
            headers={
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
            },
            timeout=timeout,
        )
        if response.status_code != 200:
            return None
        return _decoded_from_batch(response.text)
    except (httpx.HTTPError, ValueError) as exc:
        logger.debug("Google News link not resolved: %s", type(exc).__name__)
        return None
