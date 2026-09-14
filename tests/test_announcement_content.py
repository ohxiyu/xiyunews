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
    assert len(await store.listing(kind="announcement", activity=True)) == 1
    assert len(await store.listing(kind="announcement")) == 3
    await store.close()
