"""Domain allow/block lists for aggregator sources (Google News, GDELT).

Aggregators surface whatever mentions the query, including press-release
mills and general sites that only name-drop crypto. Those items never make
the edition but still consume prefilter and analysis slots, so they are
dropped at collection time.
"""

from __future__ import annotations

from typing import Iterable
from urllib.parse import urlsplit


def host_of(value: object) -> str:
    """Lower-case host of a URL or bare domain, without a leading ``www.``."""
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if "//" not in text:
        text = "//" + text
    try:
        host = urlsplit(text).hostname or ""
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _matches(host: str, domains: Iterable[str]) -> bool:
    for domain in domains:
        domain = host_of(domain)
        if domain and (host == domain or host.endswith("." + domain)):
            return True
    return False


def domain_allowed(
    value: object,
    *,
    blocked: Iterable[str] = (),
    allowed: Iterable[str] = (),
) -> bool:
    """Whether an item from this URL/domain should be kept.

    A non-empty allow list keeps only matching domains (and drops items whose
    domain is unknown). The block list always wins.
    """
    host = host_of(value)
    allowed = list(allowed)
    if allowed and (not host or not _matches(host, allowed)):
        return False
    return not (host and _matches(host, blocked))
