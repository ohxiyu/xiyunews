"""Persist previously qualified selections for a safe, AI-free brief edition."""
from __future__ import annotations
import hashlib
import json
from datetime import datetime,timedelta,timezone
from pathlib import Path
from .publication_state import read_document, write_document
from .edition import items_in_edition_window,edition_window_for,EditionWindow
from .models import ContentItem
from .ai.chinese import chinese_ready,brief

PATH=Path('data/qualified-cache.json')


def model_key(config):
    return hashlib.sha256(json.dumps({'provider':config.ai.provider.value,'model':config.ai.model,'threshold':config.filtering.ai_score_threshold,'languages':config.ai.languages,'contract':'qualified-chinese-v1'},sort_keys=True).encode()).hexdigest()


def open_window(now,timezone_name='Asia/Shanghai'):
    completed=edition_window_for(now,timezone_name)
    return EditionWindow(start=completed.end,end=completed.end+timedelta(days=1),date=(completed.end+timedelta(days=1)).date().isoformat(),timezone=timezone_name)


def load(path=PATH):
    try:
        value=read_document(path, primary=True)
        return value if isinstance(value,dict) and value.get('version')==1 and isinstance(value.get('editions'),dict) else {'version':1,'editions':{}}
    except (OSError,ValueError,TypeError):return {'version':1,'editions':{}}


def save_selection(items,config,window,*,now=None,path=PATH):
    """Call only after successful scoring and semantic duplicate checks."""
    now=(now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    qualified=[i for i in items_in_edition_window(items,window) if i.ai_score is not None and i.ai_score>=config.filtering.ai_score_threshold and chinese_ready(i) and not i.metadata.get('chinese_invalid')]
    if not qualified:return
    value=load(path)
    previous=value['editions'].get(window.date)
    if previous and previous.get('generated_at','')>=now.isoformat():return
    value['editions'][window.date]={'generated_at':now.isoformat(),'model_key':model_key(config),'dedup_verified':True,'items':[i.model_dump(mode='json') for i in qualified]}
    value['editions']={date:row for date,row in value['editions'].items() if date>=(now-timedelta(days=4)).date().isoformat()}
    write_document(path, value)


def cached_selection(config,window,*,path=PATH):
    row=load(path)['editions'].get(window.date,{})
    if not isinstance(row,dict):return []
    if row.get('model_key')!=model_key(config) or row.get('dedup_verified') is not True:return []
    try:items=[ContentItem.model_validate(i) for i in row.get('items',[])]
    except (ValueError,TypeError):return []
    result=[]
    for item in items_in_edition_window(items,window):
        if item.ai_score is not None and item.ai_score>=config.filtering.ai_score_threshold and not item.metadata.get('chinese_invalid') and brief(item):result.append(item)
    return sorted(result,key=lambda i:i.ai_score,reverse=True)[:config.filtering.max_items]
