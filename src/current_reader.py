"""Render the current edition using the deployed reader's static page shell."""
from __future__ import annotations

from datetime import date, datetime
from email.utils import format_datetime
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from .core_site import ZONE, _reader_layout, convert_feed

_SITE = "https://xiyu.news"
_STATS = (("candidates", "采集"), ("analyzed", "分析"),
          ("displayed", "展示"), ("high_priority", "高优先级"))


def _window(metadata: dict) -> str:
    window = metadata.get("window") or {}
    if not (window.get("start") and window.get("end")):
        return ""
    start, end = (datetime.fromisoformat(window[key].replace("Z", "+00:00")).astimezone(ZONE)
                  for key in ("start", "end"))
    return f'<span class="day-window">{start:%m.%d %H:%M}–{end:%m.%d %H:%M}</span>'


def _outline(headlines: list[dict], data: dict, label: str) -> tuple[str, str]:
    def link(row: dict) -> str:
        return f'<a href="#{escape(row["id"])}">{escape(row["title"])}</a>'

    highlights = data.get("overview")
    headline = escape(highlights) if highlights else link(headlines[0])
    tail = headlines[:3] if highlights else headlines[1:4]
    lines = []
    for row in tail:
        category = row.get("category")
        topic = f'<span class="signal-category">{escape(category)}</span>' if category else ""
        lines.append(f'<li><a href="#{escape(row["id"])}">{topic}<span>{escape(row["title"])}</span>'
                     f'<span class="signal-rank">#{row["rank"]}</span></a></li>')
    details = ""
    if lines:
        details = ('<details class="edition-overview-disclosure" data-desktop-open open>'
                   f'<summary>{len(lines)} 条线索</summary><ol class="edition-overview-signals">'
                   + "".join(lines) + "</ol></details>")

    filters = data.get("filters", {})
    controls = ""
    if len(filters) > 1:
        choices = "".join(
            f'<button type="button" data-category-filter="{escape(category)}" aria-pressed="false">'
            f'{escape(category)} <small>{count}</small></button>'
            for category, count in filters.items())
        controls = ('<div class="category-filters" aria-label="资讯分类" role="group" hidden>'
                    f'<button type="button" data-category-filter="" aria-pressed="true">全部 <small>'
                    f'{len(headlines)}</small></button>{choices}</div>')

    orientation = ('<div class="feed-orientation"><section class="edition-overview" aria-label="本期脉络">'
                   '<p class="edition-overview-title">本期脉络</p>'
                   f'<p class="edition-overview-headline">{headline}</p>{details}</section>'
                   '<div class="feed-toolbar"><p>本期资讯按影响力排序，前三条为本期重点。</p>'
                   f'{controls}</div></div>')

    rows = []
    for row in headlines:
        category = row.get("category")
        category_attribute = f' data-category="{escape(category)}"' if category else ""
        score = row.get("score")
        score_badge = f'<span class="score-badge">{escape(score)}</span>' if score else ""
        rows.append(f'<li{category_attribute}><span class="rank-number">{row["rank"]}</span>'
                    f'{link(row)}{score_badge}</li>')
    ranking = (f'<aside class="headline-rail" aria-label="{label} 排行榜">'
               '<details class="headline-index" data-desktop-open open>'
               f'<summary><span>{label} 排行榜</span><small data-ranking-count>{len(rows)}</small></summary>'
               '<ol class="headline-list">' + "".join(rows) + '</ol></details></aside>')
    return orientation, ranking


def edition_section(markup: str, metadata: dict) -> str:
    day = date.fromisoformat(metadata["date"]).isoformat()
    if day != metadata["date"]:
        raise ValueError("expected a canonical edition date")
    label = day.replace("-", ".")
    content, reader = _reader_layout(convert_feed(markup), metadata, day)
    headlines = reader.get("headlines", [])
    if not headlines or len(headlines) != len(metadata["items"]):
        raise ValueError("reader article count does not match the current API")
    actual = BeautifulSoup(content, "html.parser").select("article.digest-item")
    expected = [item["content_revision"]["zh"] for item in metadata["items"]]
    if [item.get("data-content-revision") for item in actual] != expected:
        raise ValueError("reader article order or content changed")
    summary = "".join(
        f"<span><strong>{escape(str(reader['stats'][key]))}</strong> 条{title}</span>"
        for key, title in _STATS if key in reader["stats"])
    orientation, ranking = _outline(headlines, reader, label)
    return (
        f'<section class="daily-day" data-language="zh" data-date="{day}">'
        f'<header class="day-divider" data-latest-edition-date="{day}"><div class="day-divider-title">'
        f'<span class="day-state">最新</span><h2><time datetime="{day}">{label}</time></h2>{_window(metadata)}</div>'
        f'<div class="day-divider-stats" aria-label="日报统计">{summary}</div></header>'
        f'<div class="daily-feed-layout">{orientation}{ranking}'
        f'<div class="daily-story-stream">{content}</div></div></section>'
    )


def render_current(markup: str, metadata: dict, home_shell: str, page_shell: str) -> dict[str, str]:
    """Render one newly accepted date without reading or building an archive."""
    section = edition_section(markup, metadata)
    day = metadata["date"]
    permalink = f"{_SITE}/{day.replace('-', '/')}/summary-zh"
    pages = {}
    for name, shell in (("home", home_shell), ("page", page_shell)):
        soup = BeautifulSoup(shell, "html.parser")
        sections = soup.select("section.daily-day")
        if len(sections) != 1:
            raise ValueError("reader shell needs exactly one edition slot")
        sections[0].replace_with(BeautifulSoup(section, "html.parser").section)
        if name == "page":
            canonical = soup.select_one("link[rel=canonical]")
            if canonical is not None:
                canonical["href"] = permalink
            if soup.title is not None:
                soup.title.string = f"{day} 日报 · xiyu.news"
        pages[name] = str(soup)

    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "xiyu.news 中文日报"
    ET.SubElement(channel, "link").text = _SITE
    ET.SubElement(channel, "description").text = "每天一期，加密与 AI 精选。"
    ET.SubElement(channel, "language").text = "zh-cn"
    entry = ET.SubElement(channel, "item")
    ET.SubElement(entry, "title").text = f"{day} 日报"
    ET.SubElement(entry, "link").text = permalink
    ET.SubElement(entry, "guid", {"isPermaLink": "true"}).text = permalink
    ET.SubElement(entry, "pubDate").text = format_datetime(
        datetime.fromisoformat(metadata["generated_at"].replace("Z", "+00:00")))
    ET.SubElement(entry, "description").text = " · ".join(row["title"]["zh"] for row in metadata["items"])[:1200]
    pages["rss"] = ET.tostring(rss, encoding="unicode", xml_declaration=True)
    return pages


def render_files(post: Path, payload: Path, home: Path, page: Path) -> dict[str, str]:
    """Render the exact output from the daily producer and a code-only shell."""
    import json

    text = post.read_text()
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0]:
        raise ValueError("expected a rendered edition with front matter")
    return render_current(parts[2], json.loads(payload.read_text()), home.read_text(), page.read_text())
