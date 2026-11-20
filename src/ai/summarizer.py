"""Deterministic Chinese Markdown backup of the selected edition."""
import html
from ..models import ContentItem
from ..web_feed import _localized_title,_localized_text,_safe_url


class DailySummarizer:
    def __init__(self,display_timezone='Asia/Shanghai'):
        self.display_timezone=display_timezone

    async def generate_summary(self,items,date,total_fetched,language='zh'):
        if language!='zh':raise ValueError('Only Chinese daily summaries are supported')
        parts=[f'# xiyu.news 日报 · {date}\n\n']
        for index,item in enumerate(items,1):
            parts.append(f'## {index}. {html.escape(_localized_title(item,"zh"))}\n\n')
            background=_localized_text(item,'background','zh')
            if background:parts.append('背景：'+html.escape(background)+'\n\n')
            parts.append(html.escape(_localized_text(item,'detailed_summary','zh') or item.ai_summary or '')+'\n\n')
            url=_safe_url(item.url)
            if url:parts.append(f'[原始来源]({url})\n\n')
        return ''.join(parts)
