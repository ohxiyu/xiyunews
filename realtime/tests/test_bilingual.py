"""Official-language versions, extractive summary/key points and Telegram formatting."""
# ruff: noqa: RUF001

import asyncio
import time

import pytest

from src.platform import exchanges
from src.platform.content import ContentCollector
from src.platform.delivery import format_message
from src.platform.exchanges import FEEDS, Exchanges
from src.platform.store import Store
from src.platform.text import language, summarize


def test_summary_is_lead_and_points_are_later_specifics():
    en = summarize(
        "Binance Will List HYPE",
        "Binance will list Hyperliquid (HYPE) at 2026-09-24 11:00 (UTC). "
        "HYPE is a seed tag token. Please read the risk warning. "
        "Withdrawals open on 2026-09-25 11:00 (UTC).",
        "en",
    )
    assert en == (
        "Binance will list Hyperliquid (HYPE) at 2026-09-24 11:00 (UTC). HYPE is a seed tag token.",
        "Withdrawals open on 2026-09-25 11:00 (UTC).",
    )
    zh = summarize(
        "币安将上市HYPE",
        "尊敬的用户：\n币安将于2026-09-24 11:00上线HYPE。HYPE为种子标签代币，波动较大。"
        "免责声明：不构成建议。提现将于2026-09-25 11:00开放。",
        "zh",
    )
    assert zh == (
        "币安将于2026-09-24 11:00上线HYPE。HYPE为种子标签代币，波动较大。",
        "提现将于2026-09-25 11:00开放。",
    )
    assert summarize("Only a title", "", "en") == ("", "")
    assert (language("币安"), language("만트라"), language("Bybit")) == ("zh", "ko", "en")


@pytest.mark.asyncio
async def test_feed_attaches_official_translation_by_article_id(monkeypatch):
    feed = next(f for f in FEEDS if f.source == "bybit")
    en = {
        "retCode": 0,
        "result": {
            "list": [
                {
                    "title": "Bybit to delist ABC",
                    "description": "ABC spot trading ends at 2026-10-01 08:00 UTC.",
                    "url": "https://announcements.bybit.com/en-US/article/delist-abc-art1a2b/",
                    "dateTimestamp": 1000,
                }
            ]
        },
    }
    zh = {
        "retCode": 0,
        "result": {
            "list": [
                {
                    "title": "Bybit 將下架 ABC",
                    "description": "ABC 現貨交易將於 2026-10-01 08:00 UTC 結束。",
                    "url": "https://announcements.bybit.com/zh-TW/article/delist-abc-art1a2b/",
                }
            ]
        },
    }
    accepted = []

    async def accept(source, rows):
        accepted.extend(rows)
        raise asyncio.CancelledError

    runner = Exchanges(accept, None, lambda *a: None)

    async def get(session, url):
        return zh if "zh-TW" in url else en

    monkeypatch.setattr(runner, "get", get)
    with pytest.raises(asyncio.CancelledError):
        await runner.feed(feed)
    assert accepted[0]["i18n"]["zh"]["title"] == "Bybit 將下架 ABC"
    assert accepted[0]["i18n"]["zh"]["url"].endswith("/zh-TW/article/delist-abc-art1a2b/")


def notice(source="bybit", sid="/a/", title="Bybit to delist ABC", body="", **extra):
    return dict(
        kind="announcement",
        source=source,
        source_id=sid,
        title=title,
        body=body,
        url="https://announcements.bybit.com/en-US/article/a/",
        category="delisting",
        published=time.time(),
        **extra,
    )


@pytest.mark.asyncio
async def test_chinese_first_push_then_edit_when_translation_arrives_late(tmp_path):
    store = Store(str(tmp_path / "db"))
    body = "ABC spot trading ends at 2026-10-01 08:00 UTC. Deposits are closed now."
    assert await store.add(notice(body=body), chat="c", notify=True)
    await ContentCollector(store).enrich(None, (await store.content_pending(0))[0])
    sent = await store.claim(set(), chinese_announcements=True)
    assert sent["lang"] == "en"
    text = format_message(sent)
    assert text.startswith("<b>Bybit · Bybit to delist ABC</b>") and "Source ↗" in text
    await store.finish(sent, "sent", message_id=11)
    assert await store.pending_edits(0) == []
    # The official Chinese listing appears on a later poll with the same content.
    later = notice(
        body=body, i18n={"zh": dict(title="Bybit 將下架 ABC", body="ABC 現貨交易結束。", url="u")}
    )
    assert not await store.add(later, chat="c", notify=True)
    edits = await store.pending_edits(0)
    assert [e["telegram_id"] for e in edits] == [11]
    edited = format_message(edits[0])
    assert "Bybit 將下架 ABC" in edited and "原文 ↗" in edited
    await store.mark_edit(edits[0]["id"], "zh")
    assert await store.pending_edits(0) == []
    row = (await store.listing(kind="announcement"))[0]
    assert set(row["i18n"]) == {"en", "zh"} and row["i18n"]["en"]["method"] == "original"
    await store.close()


@pytest.mark.asyncio
async def test_new_translation_on_insert_is_pushed_in_chinese_and_retired_hidden(tmp_path):
    store = Store(str(tmp_path / "db"))
    event = notice(i18n={"zh": dict(title="Bybit 将下架 ABC", body="", url="https://x/zh")})
    assert await store.add(event, chat="c", notify=True)
    await ContentCollector(store).enrich(None, (await store.content_pending(0))[0])
    sent = await store.claim(set(), chinese_announcements=True)
    assert sent["lang"] == "zh" and "<b>Bybit · Bybit 将下架 ABC</b>" in format_message(sent)
    await store.add(notice(source="htx", sid="1", title="HTX old"), chat="c", notify=False)
    pair = exchanges.pair_event("upbit", "KRW-NEW", "NEW", "KRW", "KRW-NEW")
    await store.add(pair, chat="c", notify=False)
    rows = await store.listing(kind="announcement")
    assert [r["source"] for r in rows] == ["upbit", "bybit"]
    assert rows[0]["i18n"]["en"]["title"] == "Upbit lists new pair NEW/KRW"
    await store.close()
