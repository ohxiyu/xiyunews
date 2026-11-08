"""Chinese core reader: deterministic rendering, no AI, catalog edits or delivery."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from ._file_utils import _atomic_write_text
from .models import ContentItem
from .publication_revision import story_revision
from .web_feed import (_escape, _localized_title, _localized_text, _summary_html,
                       _source_html, _references_html, _safe_url, _thread_html)

ZONE = ZoneInfo("Asia/Shanghai")
EVENT_SLOT = "<!--core-events-->"


def _card(*, attrs: dict, heading: str, body: str, meta: str, index: int) -> str:
    attributes = " ".join(f'{key}="{_escape(value)}"' for key, value in attrs.items())
    copy = f'<button type="button" class="copy-link" data-copy="#{_escape(attrs["id"])}" hidden>复制链接</button>'
    content = f'<div class="story-body">{body}<div class="story-actions">{copy}</div></div>'
    if index <= 3:
        content = f'<div class="story-meta">{meta}</div>{heading}{content}'
    else:
        content = f'<details class="compact-story"><summary><span class="story-meta">{meta}</span>{heading}<span class="expand-label">展开全文</span></summary>{content}</details>'
    return f'<article class="digest-item core-story" {attributes}>{content}</article>'


def render_core_feed(items: list[ContentItem], *, date: str, display_timezone="Asia/Shanghai") -> str:
    cards = []
    for index, item in enumerate(items, 1):
        title = _localized_title(item, "zh")
        summary = _localized_text(item, "detailed_summary", "zh") or item.ai_summary or ""
        background = _localized_text(item, "background", "zh")
        body = (f'<aside class="story-background"><span>背景</span>{_summary_html(background,"zh")}</aside>' if background else "")
        body += _summary_html(summary, "zh")
        body += f'<p class="source-line">{_source_html(item, language="zh", display_timezone=ZoneInfo(display_timezone))}</p>'
        refs = _references_html(item, "zh")
        if refs: body += f'<details class="references"><summary>参考资料</summary>{refs}</details>'
        body += _thread_html(item, "zh").replace("持续追踪", "事件流")
        stamp = item.published_at.astimezone(ZoneInfo(display_timezone))
        meta = f'<span>{"本期重点" if index <= 3 else "更多资讯"}</span><time datetime="{stamp.isoformat()}">{stamp:%m.%d %H:%M} CST</time>'
        cards.append(_card(attrs={"id":f"zh-{date}-item-{index}","data-story-id":item.id,
            "data-content-revision":story_revision(str(item.url),title,summary)},
            heading=f'<h2>{_escape(title)}</h2>', body=body,meta=meta,index=index))
        if index == 3: cards.append(EVENT_SLOT)
    if len(items)<3:cards.append(EVENT_SLOT)
    return '<div class="core-feed" data-core-feed="1">'+"".join(cards)+'</div>\n'


def convert_feed(content: str) -> str:
    """Migrate published markup, preserving exact body, order, anchors/revisions.

    Historical texts are never regenerated from a truncated public API.
    """
    if 'data-core-feed="1"' in content:return content
    soup = BeautifulSoup(content,"html.parser")
    cards=[]
    for index, article in enumerate(soup.select('article.digest-item'),1):
        heading=article.find('h2')
        summary=article.select_one('.story-summary-body')
        if not heading or not summary:raise ValueError('published story missing full heading/body')
        body=''
        bg=article.select_one('[data-context-kind="background"]')
        if bg:
            for h in bg.select('h3'):h.decompose()
            body=f'<aside class="story-background"><span>背景</span>{bg.decode_contents()}</aside>'
        body+=str(summary)
        source=article.select_one('.source-line')
        if source:body+=str(source)
        refs=article.select_one('.reference-list')
        # References markup from all existing generations is retained.
        after=article.select_one('[data-context-placement="after"]')
        if after:
            for section in list(after.select('section')):
                if section.select_one('a[href]'):body+=f'<details class="references"><summary>参考资料</summary>{section}</details>'
        thread=article.select_one('.thread-pill')
        if thread:body+=str(thread).replace('持续追踪','事件流')
        stamp=source.find('time') if source else None
        if stamp and stamp.get('datetime'):
            parsed=datetime.fromisoformat(stamp['datetime']).astimezone(ZONE)
            stamp.string=parsed.strftime('%m.%d %H:%M CST')
        meta=f'<span>{"本期重点" if index<=3 else "更多资讯"}</span>'+(str(stamp) if stamp else '<span>来源未提供时间</span>')
        # Native details summary contains text only, no nested source link.
        heading=f'<h2>{_escape(heading.get_text(" ",strip=True))}</h2>'
        attrs={k:article[k] for k in ('id','data-story-id','data-content-revision') if k in article.attrs}
        if not attrs.get('id'):raise ValueError('published story missing stable identity')
        cards.append(_card(attrs=attrs,heading=heading,body=body,meta=meta,index=index))
        if index==3:cards.append(EVENT_SLOT)
    if not cards:
        # An explicit empty edition remains empty; do not erase unknown formats.
        if soup.select_one('.empty-state'):return '<p class="empty-state">本期暂无达到展示标准的资讯。</p>'
        return content  # Pre-renderer historical Markdown remains readable and intact.
    if len(cards)<3:cards.append(EVENT_SLOT)
    return '<div class="core-feed" data-core-feed="1">'+''.join(cards)+'</div>\n'


def republish(root: Path) -> dict:
    count=0
    for post in sorted((root/'_posts').glob('*-summary-zh.md')):
        text=post.read_text()
        parts=text.split('---',2)
        if len(parts)!=3:raise ValueError('invalid published front matter')
        body=convert_feed(parts[2])
        _atomic_write_text(post,'---'+parts[1]+'---\n\n'+body)
        day=post.name[:10]
        fragment=root/'editions'/day/'zh.html';fragment.parent.mkdir(parents=True,exist_ok=True)
        _atomic_write_text(fragment,f'<div class="daily-feed-content" data-feed-fragment="2" data-language="zh" data-date="{day}">{body}</div>\n')
        count+=1
    latest=root/'api/latest.json'
    if latest.exists():
        value=json.loads(latest.read_text())
        meta={'date':value['date'],'generated_at':value.get('generated_at','')}
        if meta['generated_at']:
            meta['display_time']=datetime.fromisoformat(meta['generated_at'].replace('Z','+00:00')).astimezone(ZONE).strftime('%m.%d %H:%M CST')
        _atomic_write_text(root/'_data/core_edition.json',json.dumps(meta,ensure_ascii=False)+'\n')
    republish_events(root)
    return {"editions_rendered":count,"ai_calls":0,"messages_sent":0}


def republish_events(root: Path) -> None:
    from .event_pipeline import load_event_catalog
    from .site_pages import build_event_index_data, _timeline, _front_matter
    catalog=root/'_data/events.json'
    if not catalog.exists():return
    _,events=load_event_catalog(catalog)
    payload=build_event_index_data(events)
    by_id={event.event_id:event for event in events}
    focus=payload['focus']
    for index,row in enumerate(focus):
        event=by_id[row['event_id']]
        material=sorted((u for u in event.updates if u.material_change),key=lambda u:(u.occurred_at,u.first_seen_at,u.update_id))
        row['timeline']=_timeline(material,limit=len(material) if index==0 else 3)
    for group in ('focus','threads','archived','dormant','other','completed'):
        for row in payload.get(group,[]):
            for step in row.get('timeline',[]):
                step['sources']=[{**source,'url':_safe_url(source.get('url',''))} for source in step.get('sources',[]) if _safe_url(source.get('url',''))]
    (root/'_data').mkdir(parents=True,exist_ok=True)
    _atomic_write_text(root/'_data/core_stream.json',json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    # Event details show every distinct material development with its evidence.
    for event in events:
        material=sorted((u for u in event.updates if u.material_change),key=lambda u:(u.occurred_at,u.first_seen_at,u.update_id))
        timeline=_timeline(material,limit=len(material))
        title=event.title_zh or event.title_en
        body=f'<header class="page-heading"><p class="eyebrow">事件流</p><h1>{_escape(title)}</h1></header>'+timeline_html(timeline)
        body+='<p class="archive-back"><a href="/threads/">返回事件流</a></p>'
        path=root/'events'/f'{event.event_id}.html';path.parent.mkdir(parents=True,exist_ok=True)
        _atomic_write_text(path,_front_matter(title=title,permalink=f'/events/{event.event_id}/',language='zh',page_class='core-event-detail')+body)


def timeline_html(timeline: list[dict]) -> str:
    rows=[]
    for row in timeline:
        source_links=[]
        for source in row['sources']:
            url=_safe_url(source.get('url',''))
            if url:source_links.append(f'<a href="{url}" target="_blank" rel="noopener noreferrer">{_escape(source.get("label") or "原始来源")}</a>')
        rows.append(f'<li id="{_escape(row["update_id"])}"><time datetime="{_escape(row["timestamp"])}">{_escape(row["display_time"])}</time><div><p>{_escape(row["text_zh"] or row["text_en"])}</p><p class="source-line">{" · ".join(source_links)}</p></div></li>')
    return '<ol class="core-timeline">'+''.join(rows)+'</ol>'


EVENT_OWNED_PATHS = {
    "events", "threads", "api/events", "api/events.json", "_data/events.json",
    "_data/event-legacy-urls.json", "_data/threads.json", "_data/core_stream.json",
}


def stage_reader(source: Path, destination: Path) -> None:
    """Omit event-owned INPUTS; the publisher must never delete remote assets.

    peaceiris exclude_assets removes matching files from its destination even
    with keep_files, so it is deliberately not used for state preservation.
    """
    source=source.resolve();destination=destination.resolve()
    if destination.exists() or destination==source or destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("reader staging requires a separate new directory")
    def omit(directory, names):
        parent=Path(directory).relative_to(source)
        return [name for name in names if (parent/name).as_posix() in EVENT_OWNED_PATHS]
    shutil.copytree(source,destination,ignore=omit)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=Path('docs'))
    parser.add_argument('--stage-reader',type=Path)
    args=parser.parse_args()
    print(json.dumps(republish(args.root),ensure_ascii=False))
    if args.stage_reader:stage_reader(args.root,args.stage_reader)
