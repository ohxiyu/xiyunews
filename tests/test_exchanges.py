"""Exchange announcement parsers, new-pair detection and delivery gating (payloads as observed)."""

import asyncio
import hashlib
import json

import pytest

from src.platform import exchanges
from src.platform.content import ContentCollector
from src.platform.exchanges import (
    Exchanges,
    Markets,
    parse_bitget,
    parse_bithumb,
    parse_bybit,
    parse_htx,
    parse_kucoin,
)
from src.platform.store import Store


def test_announcement_parsers_identity_time_and_category():
    bybit = parse_bybit(
        {
            "retCode": 0,
            "result": {
                "list": [
                    {
                        "title": "USDC Token Splash— Grab a share of the 100000 USDC prize pool",
                        "description": "Join our event",
                        "type": {"key": "new_crypto"},
                        "url": "https://announcements.bybit.com/en-US/article/usdc-splash-art1/",
                        "dateTimestamp": 1790229062000,
                        "publishTime": 1790249232000,
                    },
                    {
                        "title": "Bybit to Support Injective (INJ) Network Upgrade",
                        "type": {"key": "maintenance_updates"},
                        "url": "https://announcements.bybit.com/en-US/article/inj-art2/",
                        "dateTimestamp": 1790260000000,
                    },
                ]
            },
        }
    )
    assert bybit[0]["published"] == 1790249232 and bybit[0]["category"] == "promotion"
    assert bybit[0]["source_id"] == "/en-US/article/usdc-splash-art1/"
    assert bybit[1]["category"] == "maintenance"
    bitget = parse_bitget(
        {
            "code": "00000",
            "data": [
                {
                    "annId": "1256",
                    "annTitle": "Bitget announcement on suspending INJ deposit services",
                    "annType": "maintenance_system_updates",
                    "annUrl": "https://www.bitget.com/en/support/articles/1256",
                    "cTime": "1790261840052",
                }
            ],
        }
    )
    assert bitget[0]["source_id"] == "1256" and bitget[0]["category"] == "security"
    kucoin = parse_kucoin(
        {
            "code": "200000",
            "data": {
                "items": [
                    {
                        "annId": 337590,
                        "annTitle": "KuCoin Futures Will Adjust the Maximum Leverage",
                        "annType": ["latest-announcements", "futures-announcements"],
                        "annDesc": "KuCoin Futures Will Adjust the Maximum Leverage",
                        "annUrl": "https://www.kucoin.com/announcement/en-adjust",
                        "cTime": 1790240040000,
                    }
                ]
            },
        }
    )
    assert kucoin[0]["body"] == "" and kucoin[0]["published"] == 1790240040
    htx = parse_htx(
        {"code": 200, "data": {"list": [{"id": 65, "title": "HTX Launches X", "showTime": 1000}]}}
    )
    assert htx[0]["url"] == "https://www.htx.com/support/en-us/detail/65"
    bithumb = parse_bithumb(
        [
            {
                "categories": ["입출금"],
                "title": "만트라(MANTRA) 출금 일시 중지 안내",
                "pc_url": "https://feed.bithumb.com/notice/1655033",
                "published_at": "2026-09-24 23:06:29",
            }
        ]
    )
    assert bithumb[0]["published"] == 1790258789 and bithumb[0]["category"] == "maintenance"
    with pytest.raises(ValueError):
        parse_bybit({"retCode": 10001})
    with pytest.raises(ValueError):
        parse_htx(
            {"code": 200, "data": {"list": [{"id": 1, "title": "x", "showTime": 1}]}}
            | {"code": 502}
        )


@pytest.mark.asyncio
async def test_new_pairs_after_baseline_only_and_quiet_flag(monkeypatch):
    pages = [
        [{"market": f"KRW-C{i}"} for i in range(30)],
        [{"market": f"KRW-C{i}"} for i in range(30)] + [{"market": "KRW-NEW"}],
        [{"market": f"KRW-C{i}"} for i in range(29)] + [{"market": "KRW-NEW"}],
    ]
    accepted, emitted, states = [], [], []

    async def accept(source, rows):
        accepted.append((source, len(rows)))

    async def emit(event, baseline):
        emitted.append(event)

    feed = Exchanges(accept, emit, lambda *a: states.append(a[1]))

    async def get(session, url):
        if not pages:
            raise asyncio.CancelledError
        return pages.pop(0)

    monkeypatch.setattr(feed, "get", get)
    monkeypatch.setattr(
        asyncio, "sleep", lambda *_: asyncio.sleep.__wrapped__(0) if False else _noop()
    )
    spec = Markets("upbit", "u", exchanges.markets_upbit, 0, False)
    with pytest.raises(asyncio.CancelledError):
        await feed.markets(spec)
    assert accepted == [("upbit_markets", 30)]
    assert [e["title"] for e in emitted] == ["Upbit 新增交易对 NEW/KRW"]
    assert emitted[0]["url"] == "https://upbit.com/exchange?code=CRIX.UPBIT.KRW-NEW"
    assert emitted[0]["category"] == "listing" and not emitted[0]["quiet"]
    assert exchanges.pair_event("gate", "A_USDT", "A", "USDT", "A_USDT", quiet=True)["quiet"]
    assert exchanges.split_symbol("PENDLEUSDC") == ("PENDLE", "USDC")


async def _noop():
    return None


@pytest.mark.asyncio
async def test_category_change_is_not_a_revision_and_exchange_text_is_deliverable(tmp_path):
    store = Store(str(tmp_path / "db"))
    event = dict(
        kind="announcement",
        source="bybit",
        source_id="/a/",
        title="Bybit to delist ABC",
        body="",
        url="https://announcements.bybit.com/a/",
        category="other",
    )
    # A row recorded by the previous version, whose digest included the category.
    legacy = hashlib.sha256(
        json.dumps([event["title"], "", event["url"], "other"], ensure_ascii=False).encode()
    ).hexdigest()
    store.db.execute("INSERT INTO seen VALUES (?,?,?)", ("bybit", "/a/", legacy))
    assert not await store.add(dict(event, category="delisting"), chat="c", notify=True)
    assert await store.add(dict(event, source_id="/b/"), chat="c", notify=True)
    await ContentCollector(store).enrich(None, (await store.content_pending(0))[0])
    notice = await store.claim(set(), chinese_announcements=True)
    assert notice["title"] == "Bybit to delist ABC" and notice["body"] == ""
    korean = dict(
        event,
        source="bithumb",
        source_id="/n/1",
        title="만트라(MANTRA) 출금 일시 중지 안내",
        url="https://feed.bithumb.com/notice/1",
    )
    assert await store.add(korean, chat="c", notify=True)
    pending = [e for e in await store.content_pending(0) if e["source"] == "bithumb"]
    await ContentCollector(store).enrich(None, pending[0])
    row = next(r for r in await store.listing(kind="announcement") if r["source"] == "bithumb")
    assert row["content_language"] == "ko" and row["content_state"] == "ready"
    await store.close()
