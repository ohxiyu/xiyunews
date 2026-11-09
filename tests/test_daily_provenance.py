"""Downstream delivery must see the same public source identity after persistence."""
from datetime import datetime,timezone
from pathlib import Path
import pytest
from src.models import Config,ContentItem,SourceType
from src.daily_feed import DailyFeedState,save_daily_feed_state,load_published_daily_feed_state
from src.source_quality import direct_tier


def roundtrip(item,path):
    now=datetime(2026,11,9,0,tzinfo=timezone.utc)
    state=DailyFeedState(date='2026-11-09',timezone='Asia/Shanghai',updated_at=now,items=[item])
    save_daily_feed_state(state,path=path)
    return load_published_daily_feed_state(state.date,state.timezone,path=path).items[0]


@pytest.mark.parametrize('kind,metadata,url',[
    (SourceType.TELEGRAM,{'channel':'binance_announcements'},'https://www.binance.com/en/support/announcement/test'),
    (SourceType.GITHUB,{'repo':'bitcoin/bitcoin'},'https://github.com/bitcoin/bitcoin/releases/tag/fixture'),
])
def test_public_primary_identity_survives_saved_selection(tmp_path,kind,metadata,url):
    cfg=Config.model_validate_json(Path('data/config.github.json').read_text())
    item=ContentItem(id='fixture',source_type=kind,title='公开安全更新',url=url,published_at=datetime(2026,11,8,tzinfo=timezone.utc),content='Fetched body must not be persisted',ai_score=9,ai_summary='公开安全修复摘要。',metadata=metadata)
    assert direct_tier(item,cfg)=='primary'
    saved=roundtrip(item,tmp_path/'state.json')
    assert direct_tier(saved,cfg)=='primary' and saved.content is None
    assert saved.metadata==metadata


def test_discovery_flag_survives_but_queries_and_signed_publisher_urls_do_not(tmp_path):
    cfg=Config.model_validate_json(Path('data/config.github.json').read_text())
    item=ContentItem(id='fixture',source_type=SourceType.RSS,title='公开报道',url='https://www.theverge.com/news/test',published_at=datetime(2026,11,8,tzinfo=timezone.utc),ai_score=9,metadata={'feed_name':'The Verge AI','gn_query':'private-fixture-query','publisher_url':'https://www.theverge.com/?signature=fixture-only'})
    assert direct_tier(item,cfg)=='secondary'
    path=tmp_path/'state.json';saved=roundtrip(item,path)
    assert saved.metadata['discovery_fallback'] is True and direct_tier(saved,cfg)=='secondary'
    assert saved.metadata['publisher_url']=='https://theverge.com'
    assert 'gn_query' not in saved.metadata and 'private-fixture-query' not in path.read_text() and 'signature=' not in path.read_text()
