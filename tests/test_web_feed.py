"""Chinese static reader safety, source time, stable revisions, full paragraphs."""
from bs4 import BeautifulSoup
from test_core_site import story
from src.web_feed import render_web_feed
from src.archive import build_records
from src.api_output import build_edition_payload


def test_reader_renders_full_summary_background_and_source_time_without_scripts():
    soup=BeautifulSoup(render_web_feed([story()],date='2026-11-08'),'html.parser')
    article=soup.select_one('article')
    assert '第一段事实。' in article.text and '第二段事实。' in article.text
    assert article.select_one('.story-background')
    assert article.select_one('time')['datetime']=='2026-11-08T09:23:00+08:00'
    assert not article.select('script')


def test_escaping_and_url_validation_cover_title_body_and_references():
    item=story();item.metadata.update(title_zh='<script>标题</script>',detailed_summary_zh='<img src=x>',
        background_zh='<iframe>背景</iframe>',sources=[{'title':'<svg>','url':'javascript:alert(1)'}])
    text=render_web_feed([item],date='2026-11-08')
    assert all(x not in text for x in ('<script>','<img','<iframe','<svg','href="javascript:'))
    assert '&lt;script&gt;' in text and '&lt;img' in text


def test_reader_and_api_revisions_agree_and_track_changed_chinese_text():
    item=story();revisions=[]
    for title in ('中文标题一','中文标题二'):
        item.metadata['title_zh']=title
        payload=build_edition_payload(build_records([item],date='2026-11-08',top_category_of=lambda _:'crypto'),date='2026-11-08',stats={})
        article=BeautifulSoup(render_web_feed([item],date='2026-11-08'),'html.parser').select_one('article')
        assert article['data-content-revision']==payload['items'][0]['content_revision']['zh']
        revisions.append(article['data-content-revision'])
    assert revisions[0]!=revisions[1]
