import asyncio
import json
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from bs4 import BeautifulSoup
from src.core_site import render_core_feed,convert_feed,republish
from src.daily_feed import DailyFeedState
from src.models import ContentItem,SourceType
from src.web_feed import render_web_feed
from src.ai.enricher import ContentEnricher
from src.ai.prompts import CORE_ENRICHMENT_SYSTEM,CONCEPT_EXTRACTION_SYSTEM


def story(index=1):
 return ContentItem(id=str(index),title='原始新闻标题',url=f'https://example.com/{index}',source_type=SourceType.RSS,published_at=datetime(2026,11,8,1,23,tzinfo=timezone.utc),ai_summary='报道事实。',ai_score=9,metadata={'title_zh':'原始新闻标题','detailed_summary_zh':'第一段事实。\n\n第二段事实。','background_zh':'有证据的主体背景。'})


def test_dense_feed_all_full_timestamp_and_background():
 soup=BeautifulSoup(render_core_feed([story(i) for i in range(1,6)],date='2026-11-08'),'html.parser')
 articles=soup.select('article.digest-item')
 assert len(articles)==5
 assert all(not a.select_one('.compact-story') for a in articles[:3])
 assert not soup.select('details.compact-story')
 assert all('11.08 09:23 CST' in a.select_one('.story-meta').text for a in articles)
 assert len(soup.select('.story-background'))==5
 assert '第二段事实。' in articles[-1].text
 assert soup.select_one('#zh-2026-11-08-item-5')
 assert soup.select_one('#zh-2026-11-08-item-5 [data-copy]')['data-copy']=='/2026/11/08/summary-zh.html#zh-2026-11-08-item-5'


def test_new_and_saved_feeds_open_background_and_references_after_text():
 item = story()
 item.metadata['sources'] = [{'title': '原始资料', 'url': 'https://example.com/reference'}]
 fresh = render_core_feed([item], date='2026-11-08')
 saved = '''<div class="core-feed" data-core-feed="2">
 <article class="digest-item core-story" id="saved" data-content-revision="old">
 <h2>原始新闻标题</h2><div class="story-body">
 <aside class="story-background"><span>背景</span><div class="story-summary-body"><p>有证据的主体背景。</p></div></aside>
 <div class="story-summary-body"><p>第一段事实。</p></div>
 <p class="source-line"><a href="https://example.com/1">原文</a></p>
 <details class="references"><summary>参考资料</summary><section><h3>参考资料</h3><ul><li><a href="https://example.com/reference">原始资料</a></li></ul></section></details>
 <div class="story-actions"></div></div></article></div>'''
 for markup in (fresh, convert_feed(saved)):
  soup = BeautifulSoup(markup, 'html.parser')
  parts = soup.select('.story-body > *')
  assert [part['class'][0] for part in parts] == [
   'story-summary-body', 'source-line', 'story-background', 'references', 'story-actions',
  ]
  assert all(part.name == 'details' and part.has_attr('open') for part in parts[2:4])
  assert parts[3].get_text(strip=True).count('参考资料') == 1
  assert parts[3].find('a')['href'] == 'https://example.com/reference'
  assert convert_feed(markup) == markup
 assert BeautifulSoup(convert_feed(saved), 'html.parser').select_one('#saved')['data-content-revision'] == 'old'


def test_history_window_uses_calendar_days_but_keeps_older_post_files(tmp_path):
 posts = tmp_path / '_posts'
 posts.mkdir()
 (tmp_path / 'api').mkdir()
 (tmp_path / '_data').mkdir()
 latest = tmp_path / 'api/latest.json'
 original_api = '{"date":"2026-11-02","items":[]}'
 latest.write_text(original_api)
 old = posts / '2026-10-20-summary-zh.md'
 old.write_text('---\ntitle: 旧刊\n---\n旧刊内容')
 assert republish(tmp_path)['editions_rendered'] == 1
 assert json.loads((tmp_path / '_data/core_edition.json').read_text())['history_start'] == 20261027
 assert latest.read_text() == original_api
 assert '旧刊内容' in old.read_text()
 assert '旧刊内容' in (tmp_path / 'editions/2026-10-20/zh.html').read_text()


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






def test_core_prompt_change_invalidates_only_enrichment_cache(monkeypatch,tmp_path):
 from src.ai.result_cache import AnalysisResultCache
 from src.ai import prompts
 cache=AnalysisResultCache(tmp_path/'cache.json',model='v3.2')
 item=story();before=cache._key(item,'enrichment');analysis=cache._key(item,'analysis')
 monkeypatch.setattr(prompts,'CORE_ENRICHMENT_SYSTEM','Changed Chinese evidence rules')
 assert cache._key(item,'enrichment')!=before
 assert cache._key(item,'analysis')==analysis



def test_reader_staging_omits_event_inputs_without_deleting_or_modifying_them(tmp_path):
 from src.core_site import stage_reader,EVENT_OWNED_PATHS
 source=tmp_path/'docs';source.mkdir()
 for relative in ['_data/events.json','_data/event-legacy-urls.json','api/events.json','api/events/evt_x.json','events/evt_x.html','threads/old.html','_posts/current.md','api/latest.json','threads.html','history.html']:
  target=source/relative;target.parent.mkdir(parents=True,exist_ok=True);target.write_text('exact:'+relative)
 destination=tmp_path/'reader-output';stage_reader(source,destination)
 for relative in ['_data/events.json','_data/event-legacy-urls.json','api/events.json','api/events/evt_x.json','events/evt_x.html','threads/old.html']:
  assert not (destination/relative).exists()
  assert (source/relative).read_text()=='exact:'+relative
 for relative in ['_posts/current.md','api/latest.json','threads.html','history.html']:
  assert (destination/relative).read_text()=='exact:'+relative


def test_v1_migration_unwraps_full_text_and_retains_anchors():
 original='<div data-core-feed="1"><article id="old"><details class="compact-story"><summary><h2>标题</h2><span class="expand-label">展开</span></summary><div class="story-body">完整背景与正文</div></details></article></div>'
 migrated=convert_feed(original)
 assert '完整背景与正文' in migrated and 'id="old"' in migrated
 assert 'compact-story' not in migrated and 'expand-label' not in migrated
 assert 'data-core-feed="2"' in migrated
 assert convert_feed(migrated)==migrated
