import pytest

from src.platform.content import ArticleParser, article_text, brief
from src.platform.store import Store


def test_article_isolation_and_brief():
    html = (
        '<nav>UNRELATED</nav><div class="index_richTextContent__x">'
        "<p>This is a general update. Please check regional availability.</p>"
        "<p>ABC/USDT trading will open at Sep 12, 2026 10:00 UTC.</p>"
        "<script>SECRET SCRIPT</script><p>Maximum leverage is 20x for this product.</p>"
        "</div><footer>FOOTER</footer>"
    )
    body = article_text(html)
    assert "UNRELATED" not in body and "SECRET" not in body and "FOOTER" not in body
    summary = brief(body)
    assert "10:00 UTC" in summary and "20x" in summary
    assert "general update" not in summary
    with pytest.raises(ValueError):
        article_text("<html>Challenge page</html>")
    assert ArticleParser().parts == []


@pytest.mark.asyncio
async def test_enrichment_preserves_delivery_and_retries(tmp_path):
    store = Store(str(tmp_path / "db"))
    event = dict(
        kind="announcement",
        source="okx",
        source_id="a",
        title="Announcement",
        body="",
        url="https://www.okx.com/help/a",
    )
    await store.add(event, chat="private", notify=False, baseline=True)
    original = (await store.listing())[0]
    await store.save_content(original["id"], "", "", "unavailable")
    assert await store.content_pending(0) == []
    assert await store.content_pending(10**12) == []  # Historical baseline is not retried
    await store.save_content(
        original["id"], "Actual official body.", "Actual official body.", "ready"
    )
    row = (await store.listing())[0]
    assert row["body"] == row["brief"] == "Actual official body."
    assert row["status"] == "baseline" and row["detected"] == original["detected"]
    assert len(await store.listing()) == 1 and "chat" not in row
    assert await store.content_pending(10**12) == []
    assert not await store.add(event, chat="private", notify=True)
    await store.close()


@pytest.mark.asyncio
async def test_latest_priority_and_chinese_delivery_gate(tmp_path):
    import time

    store = Store(str(tmp_path / "db"))
    base = dict(
        kind="announcement",
        source="okx",
        title="English",
        body="",
        url="https://www.okx.com/help/a",
    )
    await store.add(
        dict(base, source_id="old", published=time.time() - 90000), chat="a", notify=False
    )
    await store.add(dict(base, source_id="baseline"), chat="a", notify=False, baseline=True)
    await store.add(dict(base, source_id="new", published=time.time()), chat="a", notify=True)
    pending = await store.content_pending(time.time())
    assert [e["source_id"] for e in pending] == ["new"]
    assert await store.claim(set(), chinese_announcements=True) is None
    await store.save_content(
        pending[0]["id"], "中文正文", "中文简讯", "ready", title="中文标题", language="zh"
    )
    notice = await store.claim(set(), chinese_announcements=True)
    assert notice["title"] == "中文标题" and notice["body"] == "中文简讯"
    assert len(await store.listing(kind="announcement", activity=True)) == 3
    assert len(await store.listing(kind="announcement")) == 3
    await store.close()


def test_binance_public_identity_and_cms_text():
    import json

    from src.platform.announcements import parse_binance_public
    from src.platform.content import cms_text

    row = dict(code="a" * 32, title="币安上线 ABC", releaseDate=123000)
    payload = {"code": "000000", "data": {"catalogs": [{"articles": [row, row]}]}}
    events = parse_binance_public(payload)
    assert len(events) == 1 and events[0]["source_id"] == "cms:" + "a" * 32
    assert events[0]["published"] == 123
    tree = {
        "node": "root",
        "child": [
            {
                "node": "element",
                "tag": "p",
                "child": [{"node": "text", "text": "ABC &amp; DEF 上线"}],
            }
        ],
    }
    assert cms_text(json.dumps(tree)) == "ABC & DEF 上线"
    row["code"] = "../bad"
    with pytest.raises(ValueError):
        parse_binance_public(payload)


def test_chinese_brief_skips_disclaimer_paragraph():
    text = (
        "免责声明:本产品仅向符合资格的用户提供二级市场交易,不面向其他地区。\n"
        "币安将于2026年09月14日20:00新增BNCB作为合格抵押资产并开放杠杆交易。"
    )
    result = brief(text)
    assert "免责声明" not in result and "BNCB" in result


def stream_event(published, catalog=48, title="Binance Will List Hyperliquid (HYPE)"):
    import json

    from src.platform.announcements import parse_binance

    body = "<p>Binance will list HYPE and open trading for HYPE/USDT at 11:00 (UTC).</p>"
    return parse_binance(
        dict(
            type="DATA",
            topic="com_announcement_en",
            data=json.dumps(
                dict(catalogId=catalog, publishDate=published * 1000, title=title, body=body)
            ),
        )
    )


def website_event(published, catalog=48, code="b" * 32):
    from src.platform.announcements import parse_binance_public

    row = dict(code=code, title="币安将上市Hyperliquid (HYPE)", releaseDate=published * 1000)
    catalogs = [dict(catalogId=catalog, articles=[row])]
    return parse_binance_public({"code": "000000", "data": {"catalogs": catalogs}})[0]


@pytest.mark.asyncio
async def test_binance_stream_delivers_english_then_website_copy_upgrades_it(tmp_path):
    import time

    from src.platform.content import ContentCollector

    now = time.time()
    store = Store(str(tmp_path / "db"))
    stream = stream_event(now)
    assert await store.add(stream, chat="a", notify=True)
    collector = ContentCollector(store)
    await collector.enrich(None, (await store.content_pending(now))[0])
    notice = await store.claim(set(), chinese_announcements=True)
    assert notice["title"].startswith("Binance Will List") and "11:00 (UTC)" in notice["body"]
    await store.finish(notice, "sent")
    # The Chinese website copy of the same article is not notified again.
    assert not await store.add(website_event(now + 0.4), chat="a", notify=True)
    row = (await store.listing(kind="announcement"))[0]
    assert row["source_id"] == "cms:" + "b" * 32 and row["status"] == "sent"
    assert row["url"].endswith("/detail/" + "b" * 32)
    assert [e["id"] for e in await store.content_pending(now)] == [row["id"]]
    assert len(await store.listing(kind="announcement")) == 1
    assert await store.claim(set(), chinese_announcements=True) is None
    await store.close()


@pytest.mark.asyncio
async def test_binance_website_first_suppresses_stream_and_other_catalog_is_distinct(tmp_path):
    import time

    now = time.time()
    store = Store(str(tmp_path / "db"))
    assert await store.add(website_event(now), chat="a", notify=True)
    assert not await store.add(stream_event(now + 1), chat="a", notify=True)
    assert await store.add(
        stream_event(now, catalog=161, title="Delisting X"), chat="a", notify=True
    )
    assert await store.add(stream_event(now + 60, title="Another"), chat="a", notify=True)
    assert len(await store.listing(kind="announcement")) == 3
    await store.close()
