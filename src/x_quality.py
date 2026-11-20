"""Fail closed before public X delivery; only complete published sentences pass."""
import json
import math
import re
from .ai.errors import account_error
from .ai.utils import parse_json_response
from .services.x_delivery import post_source_fields,_weighted_length
from .source_quality import direct_tier

CONTRACT='x-published-sentences-v2'
BANNED=('重磅','震惊','暴涨','暴富','抄底','买入','卖出','喊单','目标价','价格预测','值得注意的是','不难看出','这意味着','从某种意义上说','归根结底','赋能','你怎么看','转发','不是投资建议')
MARKETING=re.compile(r'上币|新增交易对|开放交易|launchpool|launchpad|spot listing|will list|\blisting\b',re.I)
PRICE_ADVICE=re.compile(r'(?:预计|预测|有望|将会?|可能|或将|看好|看涨|看跌|目标).{0,18}(?:涨至|跌至|上涨|下跌|翻倍|突破|美元|美金|\$)|(?:建议|应该|可以|适合|值得|趁机).{0,12}(?:买|卖|加仓|减仓|建仓|做多|做空)|(?:买点|卖点|止盈|止损|稳赚|必涨|必跌|逢低|追涨|抄底|满仓)',re.I)
EMOJI=re.compile('[\U0001f000-\U0001faff\u2300-\u27ff\ufe0f]')
CJK=re.compile('[\u3400-\u9fff]')
from .ai.prompts import X_POST_SYSTEM as SYSTEM


def candidates(item):
    fields=post_source_fields(item,'zh');result=[]
    for field in ('summary','background'):
        for line in fields[field].splitlines():
            start=0
            for match in re.finditer(r'[。！？](?:[”’」』）\]])?',line):
                sentence=line[start:match.end()].strip();start=match.end()
                if CJK.search(sentence) and not any(r['text']==sentence for r in result):
                    result.append({'index':len(result),'field':field,'text':sentence})
    return result


def style_ok(text,limit=280):
    return (60<=_weighted_length(text)<=min(limit,280) and bool(CJK.search(text))
        and not any(word in text for word in BANNED) and not EMOJI.search(text)
        and not re.search(r'https?://|www\.|#|[<>`]|(?:^|\n)\s*(?:[-*•]|\d+[.)、]\s)',text,re.I)
        and not MARKETING.search(text) and not PRICE_ADVICE.search(text) and '?' not in text and '？' not in text)


def approved_text(item,text,*,limit=280):
    parts=text.split('\n\n')
    rows=candidates(item)
    return (len(parts)==2 and parts[0]!=parts[1]
        and any(r['field']=='summary' and r['text']==parts[0] for r in rows)
        and any(r['text']==parts[1] for r in rows) and style_ok(text,limit))


def eligible(item,config):
    fields=post_source_fields(item,'zh')
    return (item.ai_score is not None and math.isfinite(item.ai_score) and 8<=item.ai_score<=10 and direct_tier(item,config) in ('primary','original')
        and item.metadata.get('edition_mode')!='brief' and not item.metadata.get('chinese_invalid')
        and bool(CJK.search(fields['title'])) and bool(CJK.search(fields['summary']))
        and not MARKETING.search(fields['title']+' '+fields['summary']))


def priority(item):
    fields=post_source_fields(item,'zh');text=fields['title']+' '+fields['summary']
    return (not bool(re.search(r'比特币|\bbitcoin\b|\bBTC\b|安全|被盗|漏洞|托管',text,re.I)),-(item.ai_score or 0))


async def compose(ai_client,item,*,limit=280):
    rows=candidates(item)
    if len(rows)<2:return None
    try:
        response=await ai_client.complete(system=SYSTEM,user=json.dumps({'title':post_source_fields(item,'zh')['title'],'sentences':rows},ensure_ascii=False),response_format='json')
        parsed=parse_json_response(response)
        if isinstance(parsed,str):parsed=json.loads(parsed)
        indices=parsed.get('sentences') if isinstance(parsed,dict) else None
        if not isinstance(indices,list) or len(indices)!=2 or any(type(i) is not int or not 0<=i<len(rows) for i in indices):return None
        text='\n\n'.join(rows[i]['text'] for i in indices)
        return text if approved_text(item,text,limit=limit) else None
    except Exception as exc:
        blocked=account_error(exc)
        if blocked is not None:raise blocked from exc
        return None
