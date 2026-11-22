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
                       _source_html, _references_html)

ZONE = ZoneInfo("Asia/Shanghai")
EVENT_SLOT = "<!--core-events-->"
HISTORY_DAYS = 7


def _details(kind: str, title: str, content: str) -> str:
    return f'<details class="{kind}"><summary>{title}</summary>{content}</details>'


def _background_html(content: str) -> str:
    return f'<div class="story-background"><p class="background-label">背景</p>{content}</div>'


def _card(*, attrs: dict, heading: str, body: str, meta: str) -> str:
    attributes = " ".join(f'{key}="{_escape(value)}"' for key, value in attrs.items())
    copy = '<button type="button" class="copy-body" data-copy-body hidden>复制正文</button>'
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
        if background:
            body += _background_html(_summary_html(background, "zh"))
        refs = _references_html(item, "zh")
        if refs:
            body += _details("references", "参考资料", refs.replace("<h3>参考资料</h3>", "", 1))
        body += f'<p class="source-line">{_source_html(item, language="zh", display_timezone=ZoneInfo(display_timezone))}</p>'
        meta = '<span class="priority-label">本期重点</span>' if index <= 3 else ''
        cards.append(_card(attrs={"id":f"zh-{date}-item-{index}","data-story-id":item.id,
            "data-content-revision":story_revision(str(item.url),title,summary)},
            heading=f'<h2>{_escape(title)}</h2>', body=body,meta=meta))
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
            references = story.select(':scope > details.references')
            source = story.select_one(':scope > .source-line')
            actions = story.parent.select_one(':scope > .story-meta > .story-actions, :scope > .story-body > .story-actions')
            summary_body = story.select_one(':scope > .story-summary-body')
            if background and background.name in ('details', 'aside'):
                background.name = 'div'
                del background['open']
                label = background.find(['summary', 'span'], recursive=False)
                if label:
                    label.name = 'p'
                    label['class'] = 'background-label'
                changed = True
            for reference in references:
                if reference.has_attr('open'):
                    del reference['open']
                    changed = True
                for title in reference.select('section > h3'):
                    if title.get_text(strip=True) == '参考资料':
                        title.decompose()
                        changed = True
            if actions and (button := actions.select_one('button[data-copy]')):
                del button['data-copy']
                button['data-copy-body'] = ''
                button['class'] = 'copy-body'
                button.string = '复制正文'
                changed = True
            order = [part for part in (summary_body, background, *references, source, actions) if part is not None]
            if summary_body and [part for part in story.find_all(recursive=False) if part in order] != order:
                for part in order:
                    story.append(part.extract())
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
        bg=article.select_one('[data-context-kind="background"]')
        if bg:
            for h in bg.select('h3'):h.decompose()
            body += _background_html(bg.decode_contents())
        # References markup from all existing generations is retained.
        after=article.select_one('[data-context-placement="after"]')
        if after:
            for section in list(after.select('section')):
                if section.select_one('a[href]'):
                    label = section.find('h3', recursive=False)
                    if label and label.get_text(strip=True) == "参考资料":
                        label.decompose()
                    body += _details("references", "参考资料", str(section))
        if source:body+=str(source)
        thread=article.select_one('.thread-pill')
        if thread:body+=str(thread).replace('持续追踪','事件流')
        meta = '<span class="priority-label">本期重点</span>' if index <= 3 else ''
        heading=f'<h2>{_escape(heading.get_text(" ",strip=True))}</h2>'
        attrs={k:article[k] for k in ('id','data-story-id','data-content-revision') if k in article.attrs}
        if not attrs.get('id'):raise ValueError('published story missing stable identity')
        cards.append(_card(attrs=attrs,heading=heading,body=body,meta=meta))
        if index==3:cards.append(EVENT_SLOT)
    if not cards:
        # An explicit empty edition remains empty; do not erase unknown formats.
        if soup.select_one('.empty-state'):return '<p class="empty-state">本期暂无达到展示标准的资讯。</p>'
        return content  # Pre-renderer historical Markdown remains readable and intact.
    if len(cards)<3:cards.append(EVENT_SLOT)
    return '<div class="core-feed" data-core-feed="2">'+''.join(cards)+'</div>\n'


READER_CATEGORIES = {"crypto": "Crypto", "technology": "AI 科技", "policy": "宏观政策"}


def _reader_layout(content: str, payload: dict) -> tuple[str, dict]:
    """Add reading chrome using the published article IDs and matching API rows."""
    soup = BeautifulSoup(content, "html.parser")
    feed = soup.select_one(".core-feed")
    if feed is None:
        return content, {}
    public_items = {
        row.get("content_revision", {}).get("zh"): row for row in payload.get("items", [])
        if isinstance(row.get("content_revision"), dict) and row["content_revision"].get("zh")
    }
    headlines = []
    filters: dict[str, int] = {}
    for index, article in enumerate(feed.select(":scope > article.digest-item"), 1):
        heading = article.find("h2")
        if heading is None or not article.get("id"):
            continue
        rank = f"{index:02d}"
        headline = {"id": article["id"], "rank": rank, "title": heading.get_text(" ", strip=True)}
        public = public_items.get(article.get("data-content-revision"), {})
        category = READER_CATEGORIES.get(public.get("top_category"))
        if category:
            headline["category"] = category
            article["data-category"] = category
            filters[category] = filters.get(category, 0) + 1
        else:
            del article["data-category"]
        headlines.append(headline)

        meta = article.select_one(":scope > .story-meta")
        body = article.select_one(":scope > .story-body")
        if meta is None or body is None:
            continue
        if rail := article.select_one(":scope > .story-rank"):
            rail.decompose()
        if body.select_one(".source-line time") and (stamp := meta.find("time")):
            stamp.decompose()

        for ornament in meta.select(".rank-number, .category-pill, .score-badge"):
            ornament.decompose()
        label = meta.find("span", recursive=False)
        if label:
            if label.get_text(strip=True) == "更多资讯":
                label.decompose()
            elif label.get_text(strip=True) == "本期重点":
                label["class"] = "priority-label"
        if category:
            category_label = soup.new_tag("span", attrs={"class": "category-pill"})
            category_label.string = category
            meta.insert(0, category_label)
        number = soup.new_tag("span", attrs={"class": "rank-number"})
        number.string = rank
        meta.insert(0, number)
        for thread in body.select(".thread-pill"):
            thread.decompose()

    data = {"headlines": headlines, "stats": payload.get("stats", {})}
    if sum(filters.values()) == len(headlines):
        data["filters"] = filters
    return str(soup), data


def republish(root: Path) -> dict:
    count = 0
    reader_editions = {}
    latest = root / "api/latest.json"
    latest_payload = json.loads(latest.read_text()) if latest.exists() else {}
    for post in sorted((root/'_posts').glob('*-summary-zh.md')):
        text=post.read_text()
        parts=text.split('---',2)
        if len(parts)!=3:raise ValueError('invalid published front matter')
        day = post.name[:10]
        edition_file = root / "editions" / day / "edition.json"
        payload = json.loads(edition_file.read_text()) if edition_file.exists() else latest_payload
        if payload.get("date") != day:
            payload = {}
        body, reader_editions[day] = _reader_layout(convert_feed(parts[2]), payload)
        _atomic_write_text(post,'---'+parts[1]+'---\n\n'+body)
        fragment=root/'editions'/day/'zh.html';fragment.parent.mkdir(parents=True,exist_ok=True)
        _atomic_write_text(fragment,f'<div class="daily-feed-content" data-feed-fragment="2" data-language="zh" data-date="{day}">{body}</div>\n')
        count+=1
    if reader_editions:
        (root / "_data").mkdir(exist_ok=True)
        _atomic_write_text(root / "_data/reader_editions.json", json.dumps(reader_editions, ensure_ascii=False) + "\n")
    if latest_payload:
        value = latest_payload
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
