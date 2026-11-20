"""Chinese core reader: deterministic rendering, no AI, catalog edits or delivery."""
from __future__ import annotations

import argparse
import json
import re
import shutil
from datetime import date as calendar_date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
from ._file_utils import _atomic_write_text
from .models import ContentItem
from .publication_revision import story_revision
from .web_feed import (_escape, _localized_title, _localized_text, _summary_html,
                       _source_html, _references_html, _safe_url)

ZONE = ZoneInfo("Asia/Shanghai")
EVENT_SLOT = "<!--core-events-->"
HISTORY_DAYS = 7


def _open_details(kind: str, title: str, content: str) -> str:
    return f'<details class="{kind}" open><summary>{title}</summary>{content}</details>'


def _card(*, attrs: dict, heading: str, body: str, meta: str, index: int) -> str:
    attributes = " ".join(f'{key}="{_escape(value)}"' for key, value in attrs.items())
    match=re.fullmatch(r"zh-(\d{4})-(\d{2})-(\d{2})-item-\d+",attrs['id'])
    target=(f"/{match[1]}/{match[2]}/{match[3]}/summary-zh.html" if match else "")+"#"+attrs['id']
    copy = f'<button type="button" class="copy-link" data-copy="{_escape(target)}" hidden>复制链接</button>'
    content = f'<div class="story-body">{body}<div class="story-actions">{copy}</div></div>'
    content = f'<div class="story-meta">{meta}</div>{heading}{content}'
    return f'<article class="digest-item core-story" {attributes}>{content}</article>'


def render_core_feed(items: list[ContentItem], *, date: str, display_timezone="Asia/Shanghai") -> str:
    cards = []
    if any(item.metadata.get("edition_mode")=="brief" for item in items):
        cards.append('<p class="edition-notice" data-edition-mode="brief">简版 · 部分背景暂不可用，本期保留已评分内容的中文摘要。</p>')
    for index, item in enumerate(items, 1):
        title = _localized_title(item, "zh")
        summary = _localized_text(item, "detailed_summary", "zh") or item.ai_summary or ""
        background = _localized_text(item, "background", "zh")
        body = _summary_html(summary, "zh")
        body += f'<p class="source-line">{_source_html(item, language="zh", display_timezone=ZoneInfo(display_timezone))}</p>'
        if background:
            body += _open_details("story-background", "背景", _summary_html(background, "zh"))
        refs = _references_html(item, "zh")
        if refs:
            body += _open_details("references", "参考资料", refs.replace("<h3>参考资料</h3>", "", 1))
        stamp = item.published_at.astimezone(ZoneInfo(display_timezone))
        meta = f'<span>{"本期重点" if index <= 3 else "更多资讯"}</span><time datetime="{stamp.isoformat()}">{stamp:%m.%d %H:%M} CST</time>'
        cards.append(_card(attrs={"id":f"zh-{date}-item-{index}","data-story-id":item.id,
            "data-content-revision":story_revision(str(item.url),title,summary)},
            heading=f'<h2>{_escape(title)}</h2>', body=body,meta=meta,index=index))
        if index == 3: cards.append(EVENT_SLOT)
    if len(items)<3:cards.append(EVENT_SLOT)
    return '<div class="core-feed" data-core-feed="2">'+"".join(cards)+'</div>\n'


def convert_feed(content: str) -> str:
    """Migrate published markup, preserving exact body, order, anchors/revisions.

    Historical texts are never regenerated from a truncated public API.
    """
    if re.search(r'data-core-feed="[12]"', content):
        soup=BeautifulSoup(content,'html.parser')
        changed = False
        for details in list(soup.select('details.compact-story')):
            summary=details.find('summary',recursive=False)
            if summary:
                label=summary.select_one('.expand-label')
                if label:label.decompose()
                summary.unwrap()
            details.unwrap()
            changed = True
        feed=soup.select_one('[data-core-feed]')
        if feed['data-core-feed'] != '2':
            feed['data-core-feed'] = '2'
            changed = True
        for story in feed.select('article .story-body'):
            background = story.select_one(':scope > .story-background')
            references = story.select_one(':scope > details.references')
            if background and background.name == 'aside':
                background.name = 'details'
                label = background.find('span', recursive=False)
                if label:
                    label.name = 'summary'
                background['open'] = ''
                before = references or story.select_one('.story-actions')
                if before:
                    before.insert_before(background.extract())
                else:
                    story.append(background.extract())
                changed = True
            if references:
                if not references.has_attr('open'):
                    references['open'] = ''
                    changed = True
                for title in references.select('section > h3'):
                    if title.get_text(strip=True) == '参考资料':
                        title.decompose()
                        changed = True
        return str(soup) if changed else content

    soup = BeautifulSoup(content,"html.parser")
    cards=[]
    for index, article in enumerate(soup.select('article.digest-item'),1):
        heading=article.find('h2')
        summary=article.select_one('.story-summary-body')
        if not heading or not summary:raise ValueError('published story missing full heading/body')
        body=str(summary)
        source=article.select_one('.source-line')
        if source:body+=str(source)
        bg=article.select_one('[data-context-kind="background"]')
        if bg:
            for h in bg.select('h3'):h.decompose()
            body += _open_details("story-background", "背景", bg.decode_contents())
        # References markup from all existing generations is retained.
        after=article.select_one('[data-context-placement="after"]')
        if after:
            for section in list(after.select('section')):
                if section.select_one('a[href]'):
                    label = section.find('h3', recursive=False)
                    if label and label.get_text(strip=True) == "参考资料":
                        label.decompose()
                    body += _open_details("references", "参考资料", str(section))
        thread=article.select_one('.thread-pill')
        if thread:body+=str(thread).replace('持续追踪','事件流')
        stamp=source.find('time') if source else None
        if stamp and stamp.get('datetime'):
            parsed=datetime.fromisoformat(stamp['datetime']).astimezone(ZONE)
            stamp.string=parsed.strftime('%m.%d %H:%M CST')
        meta=f'<span>{"本期重点" if index<=3 else "更多资讯"}</span>'+(str(stamp) if stamp else '<span>来源未提供时间</span>')
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
    return '<div class="core-feed" data-core-feed="2">'+''.join(cards)+'</div>\n'


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
        week_start = calendar_date.fromisoformat(value['date']) - timedelta(days=HISTORY_DAYS - 1)
        meta={'date':value['date'],'generated_at':value.get('generated_at',''),
              'history_start':int(week_start.strftime('%Y%m%d'))}
        if meta['generated_at']:
            meta['display_time']=datetime.fromisoformat(meta['generated_at'].replace('Z','+00:00')).astimezone(ZONE).strftime('%m.%d %H:%M CST')
        _atomic_write_text(root/'_data/core_edition.json',json.dumps(meta,ensure_ascii=False)+'\n')
    return {"editions_rendered":count,"ai_calls":0,"messages_sent":0}


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
