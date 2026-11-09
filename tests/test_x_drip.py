"""Chinese verified composition and weighted length; templates are retired."""
import asyncio
from datetime import datetime,timezone
from src.models import ContentItem,SourceType,XDeliveryConfig


def make_item(
    title: str,
    *,
    summary: str = "",
    impact: str = "",
    url: str = "https://example.com/story",
) -> ContentItem:
    metadata = {"title_zh": title}
    if summary:
        metadata["detailed_summary_zh"] = summary
    if impact:
        metadata["market_impact_zh"] = impact
    return ContentItem(
        id=title,
        source_type=SourceType.RSS,
        title=title,
        url=url,
        published_at=datetime(2026, 8, 9, tzinfo=timezone.utc),
        ai_score=9.0,
        metadata=metadata,
    )

def test_weighted_length_counts_cjk_as_two() -> None:
    from src.services.x_delivery import _weighted_length

    assert _weighted_length("abc") == 3
    assert _weighted_length("比特币") == 6
    assert _weighted_length("BTC 分叉") == 3 + 1 + 4

def test_weighted_length_collapses_urls_to_a_tco_token() -> None:
    from src.services.x_delivery import TCO_LENGTH, _weighted_length

    long_url = "https://example.com/" + "a" * 200
    assert _weighted_length(long_url) == TCO_LENGTH
    assert _weighted_length(f"甲 {long_url} 乙") == 2 + 1 + TCO_LENGTH + 1 + 2

class ComposingClient:
    def __init__(self, response) -> None:
        self.response = response
        self.calls: list[dict] = []

    async def complete(
        self, *, system: str, user: str, response_format: str = "json"
    ) -> str:
        self.calls.append(
            {"system": system, "user": user, "response_format": response_format}
        )
        if isinstance(self.response, Exception):
            raise self.response
        return self.response

async def _test_compose_uses_enriched_fields() -> None:
    from src.services.x_delivery import compose_story_post

    item = make_item("标题")
    item.metadata.update(
        {
            "detailed_summary_zh": "摘要内容确认了钱包软件安全更新，并公布了当前处理的完整状态。",
            "background_zh": "背景内容说明更新影响现有钱包用户，用户需要核对当前软件版本。",
            "market_impact_zh": "影响内容",
        }
    )
    client = ComposingClient('{"sentences":[0,1]}')
    text = await compose_story_post(client, item, language="zh", limit=400)
    assert text==item.metadata['detailed_summary_zh']+'\n\n'+item.metadata['background_zh']
    sent=client.calls[0]['user']
    assert '摘要内容' in sent and '背景内容' in sent and '影响内容' not in sent
    assert '不加链接' in client.calls[0]['system']

async def _test_compose_returns_none_on_failure_or_bad_output() -> None:
    from src.services.x_delivery import compose_story_post

    item = make_item("标题")
    assert (
        await compose_story_post(
            ComposingClient(RuntimeError("boom")), item, language="zh"
        )
        is None
    )
    assert (
        await compose_story_post(ComposingClient("太短。"), item, language="zh")
        is None
    )

def test_compose_uses_enriched_fields() -> None:
    asyncio.run(_test_compose_uses_enriched_fields())

def test_compose_returns_none_on_failure_or_bad_output() -> None:
    asyncio.run(_test_compose_returns_none_on_failure_or_bad_output())

async def _test_compose_never_shows_the_article_body() -> None:
    """Posts draw only on published fields; raw article text stays out."""
    from src.services.x_delivery import compose_story_post

    item = make_item("标题")
    item.content = "区块 961,632 触发自动执行条款，矿工信号率 2.6%。" * 40
    item.metadata["detailed_summary_zh"] = "摘要内容确认钱包软件已经更新，并公布当前处理状态。用户需要核对版本，按照公告中的说明完成安全更新。"
    client = ComposingClient('{"sentences":[0,1]}')
    await compose_story_post(client, item, language="zh", limit=400)
    sent = client.calls[0]["user"]
    assert "区块 961,632" not in sent
    assert "原文" not in sent
    assert "摘要内容" in sent
    system = client.calls[0]["system"]
    assert '完整原句' in system and '不改写任何字' in system
    assert '280' in system

def test_compose_never_shows_the_article_body() -> None:
    asyncio.run(_test_compose_never_shows_the_article_body())

def test_x_delivery_defaults_to_the_compact_limit() -> None:
    assert XDeliveryConfig().max_post_chars == 280
