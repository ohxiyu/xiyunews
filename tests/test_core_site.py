import asyncio
import json
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from bs4 import BeautifulSoup
from src.core_site import render_core_feed,convert_feed
from src.core_delivery import claim,delivery_eligible
from src.daily_feed import DailyFeedState
from src.models import ContentItem,SourceType
from src.publication_state import PublicationState
from src.web_feed import render_web_feed
from src.ai.enricher import ContentEnricher
from src.ai.prompts import CORE_ENRICHMENT_SYSTEM,CONCEPT_EXTRACTION_SYSTEM


def story(index=1):
 return ContentItem(id=str(index),title='原始新闻标题',url=f'https://example.com/{index}',source_type=SourceType.RSS,published_at=datetime(2026,11,8,1,23,tzinfo=timezone.utc),ai_summary='报道事实。',ai_score=9,metadata={'title_zh':'原始新闻标题','detailed_summary_zh':'第一段事实。\n\n第二段事实。','background_zh':'有证据的主体背景。'})


def test_top_three_full_timestamp_background_and_compact_remainder():
 soup=BeautifulSoup(render_core_feed([story(i) for i in range(1,6)],date='2026-11-08'),'html.parser')
 articles=soup.select('article.digest-item')
 assert len(articles)==5
 assert all(not a.select_one('.compact-story') for a in articles[:3])
 assert len(soup.select('details.compact-story:not([open])'))==2
 assert all('11.08 09:23 CST' in a.select_one('.story-meta').text for a in articles)
 assert len(soup.select('.story-background'))==5
 assert '第二段事实。' in articles[-1].text
 assert soup.select_one('#zh-2026-11-08-item-5')


def test_migration_keeps_published_text_revisions_sources_and_is_idempotent():
 items=[story(i) for i in range(5)]
 old=render_web_feed(items,date='2026-11-08',total_fetched=25,language='zh',display_timezone='Asia/Shanghai')
 new=convert_feed(old)
 a=BeautifulSoup(old,'html.parser');b=BeautifulSoup(new,'html.parser')
 assert [x['data-content-revision'] for x in a.select('article')]==[x['data-content-revision'] for x in b.select('article')]
 assert [x['id'] for x in a.select('article')]==[x['id'] for x in b.select('article')]
 assert len(b.select('.story-background'))==5
 assert all(a.select_one('a.source-link')['href']==b.select_one('a.source-link')['href'] for _ in [0])
 assert convert_feed(new)==new
 assert 'headline-rail' not in new and 'data-story-share' not in new


def test_delivery_claim_survives_process_restart_and_never_retries_unknown(tmp_path):
 first=PublicationState(tmp_path/'state')
 assert claim(first,'2026-11-08','@daily')
 assert not claim(PublicationState(tmp_path/'state'),'2026-11-08','@daily')
 assert claim(first,'2026-11-09','@daily')
 with first.connect() as db:
  assert db.execute('select status from core_telegram_receipts').fetchall()==[('attempted_unknown',),('attempted_unknown',)]


def test_old_or_rebuilt_editions_cannot_be_sent():
 state=DailyFeedState(date='2026-11-08',timezone='Asia/Shanghai',updated_at=story().published_at,items=[story()])
 report={'date':state.date,'kind':'daily_publish','started_at':state.updated_at.isoformat(),'metrics':{'displayed_today':1},'alerts':[{'code':'telegram_deferred'}]}
 assert delivery_eligible(report,state)
 report['alerts'].append({'code':'telegram_rebuild_skipped'})
 assert not delivery_eligible(report,state)
 report['alerts']=[]
 assert not delivery_eligible(report,state)


def test_chinese_enrichment_does_not_require_or_generate_english(monkeypatch):
 item=story();client=type('Client',(),{})()
 async def complete(**kw):
  if kw['system']==CONCEPT_EXTRACTION_SYSTEM:return '{"queries":[]}'
  assert kw['system']==CORE_ENRICHMENT_SYSTEM
  return json.dumps({'title_zh':'原始新闻标题','whats_new_zh':'新的具体进展。','background_zh':'有证据的背景。','sources':[]})
 client.complete=complete
 enricher=ContentEnricher(client,languages=['zh'])
 monkeypatch.setattr(enricher,'_cached_web_search',AsyncMock(return_value=[]))
 asyncio.run(enricher._enrich_item(item))
 assert item.metadata['background_zh']=='有证据的背景。'
 assert 'detailed_summary_en' not in item.metadata


def test_chinese_background_retains_year_grounding_guard(monkeypatch):
 item=story();client=type('Client',(),{})()
 async def complete(**kw):
  if kw['system']==CONCEPT_EXTRACTION_SYSTEM:return '{"queries":[]}'
  return json.dumps({'title_zh':'原始新闻标题','whats_new_zh':'新的进展。','background_zh':'项目于2022年成立。'})
 client.complete=complete;enricher=ContentEnricher(client,languages=['zh'])
 monkeypatch.setattr(enricher,'_cached_web_search',AsyncMock(return_value=[]))
 with pytest.raises(Exception):asyncio.run(enricher._enrich_item(item))
 assert 'background_zh' not in item.metadata


def test_first_event_displays_more_than_ten_and_preserves_catalog(tmp_path,monkeypatch):
 from src.core_site import republish_events
 from src.site_pages import build_event_index_data
 from test_api_output_and_pages import make_event
 from src.events import EventStatus,EventTimePrecision
 event=make_event('evt_corefull',updates=16)
 event.status=EventStatus.DEVELOPING
 for u in event.updates:u.importance_score=9
 second=make_event('evt_coreother',updates=16)
 second.status=EventStatus.DEVELOPING
 for u in second.updates:u.importance_score=8
 root=tmp_path/'docs';(root/'_data').mkdir(parents=True)
 catalog=root/'_data/events.json';original=json.dumps({'schema_version':1,'events':[e.model_dump(mode='json') for e in [event,second]]})
 catalog.write_text(original)
 now=max(e.last_updated_at for e in [event,second])
 monkeypatch.setattr('src.site_pages.build_event_index_data',lambda events:build_event_index_data(events,now=now,focus_policy={}))
 republish_events(root)
 payload=json.loads((root/'_data/core_stream.json').read_text())
 assert len(payload['focus'][0]['timeline'])>10
 assert len(payload['focus'][1]['timeline'])==3
 assert catalog.read_text()==original
 first=payload['focus'][0]
 detail=BeautifulSoup((root/'events'/f'{first["event_id"]}.html').read_text(),'html.parser')
 assert len(detail.select('.core-timeline>li'))==len(first['timeline'])


def test_core_schedule_and_publish_jobs_cannot_block_daily_with_event_ai():
 text=Path('.github/workflows/event-updates.yml').read_text()
 compute,publish=text.split('\n  publish:',1)
 assert 'bmtnews-feed-update' not in compute
 assert 'bmtnews-feed-update' in publish
 assert 'src.core_events' in compute and 'src.core_events' not in publish
 for name in ['daily-summary.yml','feed-collection.yml']:
  workflow=Path('.github/workflows',name).read_text()
  assert 'exclude_assets: "events/**,threads/**,api/events/**,api/events.json,_data/events.json,_data/event-legacy-urls.json' in workflow


def test_core_prompt_change_invalidates_only_enrichment_cache(monkeypatch,tmp_path):
 from src.ai.result_cache import AnalysisResultCache
 from src.ai import prompts
 cache=AnalysisResultCache(tmp_path/'cache.json',model='v3.2')
 item=story();before=cache._key(item,'enrichment');analysis=cache._key(item,'analysis')
 monkeypatch.setattr(prompts,'CORE_ENRICHMENT_SYSTEM','Changed Chinese evidence rules')
 assert cache._key(item,'enrichment')!=before
 assert cache._key(item,'analysis')==analysis
