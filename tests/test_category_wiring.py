"""Tests that category from source config flows into item metadata for all scrapers."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from bs4 import BeautifulSoup

from src.models import GitHubSourceConfig,HackerNewsConfig,TelegramChannelConfig,TelegramConfig
from src.scrapers.github import GitHubScraper
from src.scrapers.hackernews import HackerNewsScraper
from src.scrapers.telegram import TelegramScraper

_SINCE = datetime(2020, 1, 1, tzinfo=timezone.utc)
_NOW = datetime(2025, 1, 1, 12, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# HackerNews
# ---------------------------------------------------------------------------


def test_hackernews_category_in_metadata():
    cfg = HackerNewsConfig(category="tech")
    scraper = HackerNewsScraper(cfg, AsyncMock())
    story = {
        "id": 1,
        "title": "A story",
        "url": "https://example.com",
        "by": "user",
        "time": int(_NOW.timestamp()),
        "score": 200,
        "type": "story",
        "descendants": 10,
    }
    item = scraper._parse_story(story, [])
    assert item.metadata["category"] == "tech"


def test_hackernews_category_none_when_unset():
    cfg = HackerNewsConfig()
    scraper = HackerNewsScraper(cfg, AsyncMock())
    story = {
        "id": 2,
        "title": "Another story",
        "url": "https://example.com/2",
        "by": "user",
        "time": int(_NOW.timestamp()),
        "score": 150,
        "type": "story",
        "descendants": 0,
    }
    item = scraper._parse_story(story, [])
    assert item.metadata["category"] is None


# ---------------------------------------------------------------------------
# GitHub
# ---------------------------------------------------------------------------


def _github_event(event_type: str = "PushEvent") -> dict:
    return {
        "id": "42",
        "type": event_type,
        "created_at": _NOW.isoformat().replace("+00:00", "Z"),
        "actor": {"login": "alice"},
        "repo": {"name": "alice/repo"},
        "payload": {"commits": [{"message": "init"}]},
    }


def test_github_parse_event_category_in_metadata():
    source = GitHubSourceConfig(type="user_events", username="alice", category="oss")
    scraper = GitHubScraper([source], AsyncMock())
    item = scraper._parse_event(_github_event(), source)
    assert item is not None
    assert item.metadata["category"] == "oss"


def test_github_parse_event_category_none_when_unset():
    source = GitHubSourceConfig(type="user_events", username="alice")
    scraper = GitHubScraper([source], AsyncMock())
    item = scraper._parse_event(_github_event(), source)
    assert item is not None
    assert item.metadata["category"] is None


# ---------------------------------------------------------------------------
# Reddit
# ---------------------------------------------------------------------------














# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

_TELEGRAM_MSG_HTML = """
<div class="tgme_widget_message" data-post="channel/1">
  <div class="tgme_widget_message_text js-message_text">Hello world</div>
  <time datetime="2025-01-01T12:00:00+00:00">12:00</time>
</div>
"""


def _tg_msg_el():
    return BeautifulSoup(_TELEGRAM_MSG_HTML, "html.parser").select_one(
        "div.tgme_widget_message"
    )


def test_telegram_parse_message_category_in_metadata():
    cfg = TelegramChannelConfig(channel="channel", category="news")
    scraper = TelegramScraper(TelegramConfig(), AsyncMock())
    item = scraper._parse_message(_tg_msg_el(), cfg, _SINCE)
    assert item is not None
    assert item.metadata["category"] == "news"


def test_telegram_parse_message_category_none_when_unset():
    cfg = TelegramChannelConfig(channel="channel")
    scraper = TelegramScraper(TelegramConfig(), AsyncMock())
    item = scraper._parse_message(_tg_msg_el(), cfg, _SINCE)
    assert item is not None
    assert item.metadata["category"] is None


def test_telegram_parse_channel_html_passes_category():
    cfg = TelegramChannelConfig(channel="channel", fetch_limit=10, category="ai-news")
    scraper = TelegramScraper(TelegramConfig(), AsyncMock())
    items = scraper._parse_channel_html(_TELEGRAM_MSG_HTML, cfg, _SINCE)
    assert len(items) == 1
    assert items[0].metadata["category"] == "ai-news"


# ---------------------------------------------------------------------------
# OSSInsight
# ---------------------------------------------------------------------------






# ---------------------------------------------------------------------------
# Twitter (Apify)
# ---------------------------------------------------------------------------
