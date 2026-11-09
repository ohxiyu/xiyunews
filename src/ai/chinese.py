"""One bounded translation repair; never invent a title or a model score."""
from __future__ import annotations
import re
from .utils import parse_json_response
from .errors import account_error
from ..models import ContentItem

CHINESE_CONTRACT = '\nReturn title_zh and summary in Simplified Chinese. Preserve names, numbers, uncertainty and source meaning. JSON fields score, reason, tags and category stay unchanged. Never leave title_zh or summary in English.'


def is_chinese(value) -> bool:
    return isinstance(value,str) and bool(re.search(r'[\u3400-\u9fff]',value))


def chinese_title(item):
    return item.metadata.get('title_zh') or (item.title if is_chinese(item.title) else '')


def chinese_summary(item):
    return item.metadata.get('detailed_summary_zh') or item.ai_summary or ''


def chinese_ready(item):
    return is_chinese(chinese_title(item)) and is_chinese(chinese_summary(item))


async def repair_chinese(item:ContentItem,client) -> bool:
    if chinese_ready(item):return True
    try:
        response=await client.complete(system='Translate source facts to Simplified Chinese. Return JSON only. Do not add facts, change numbers or remove uncertainty.',user=f'Title: {item.title}\nSummary: {chinese_summary(item)}\nReturn {{"title_zh":"中文标题","summary_zh":"中文摘要"}}',max_tokens=1200)
        value=parse_json_response(response)
        if isinstance(value,dict) and is_chinese(value.get('title_zh')) and is_chinese(value.get('summary_zh')):
            item.metadata['title_zh']=value['title_zh'].strip()
            item.metadata['detailed_summary_zh']=value['summary_zh'].strip()
            return True
    except Exception as exc:
        blocked=account_error(exc)
        if blocked is not None:raise blocked from None
    item.metadata['chinese_invalid']=True
    return False


def brief(item):
    """Use only already scored Chinese facts; background is unavailable."""
    title=chinese_title(item);summary=chinese_summary(item)
    if not is_chinese(title) or not is_chinese(summary):return False
    for key in list(item.metadata):
        if key.startswith(('background','community_discussion','market_impact')) or key=='sources':item.metadata.pop(key,None)
    item.metadata.update(title_zh=title,detailed_summary_zh=summary,enrichment_status='brief',edition_mode='brief')
    return True
