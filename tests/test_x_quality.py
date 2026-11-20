"""Public text must retain every entity, number and qualifier from complete published facts."""
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock
import pytest
from src.models import Config,SourceType
from src.source_quality import direct_tier,host
from src.x_quality import candidates,approved_text,compose,eligible,priority
from src.x_switch import effective_enabled
from test_core_site import story


def config():return Config.model_validate_json(Path('data/config.github.json').read_text())


def article():
    item=story();item.url='https://www.theverge.com/news/security-update'
    item.metadata={'feed_name':'The Verge AI','title_zh':'钱包软件修复已公布的安全问题',
      'detailed_summary_zh':'Acme确认钱包软件的安全更新，用户资金未发生转移，损失并非200万美元。用户需要核对自己的软件版本，按照公告中的说明完成安全更新。',
      'background_zh':'该钱包由Acme提供，允许用户管理自己的密钥和交易签名。'}
    return type(item).model_validate(item.model_dump(warnings=False))


def test_full_sentences_prevent_number_entity_and_negation_inventions():
    item=article();rows=candidates(item);text='\n\n'.join(r['text'] for r in rows[:2])
    assert approved_text(item,text)
    for bad in [text.replace('200','300'),text.replace('Acme','其他公司'),text.replace('未发生','发生'),text.replace('并非','为'),text.replace('，损失并非200万美元','')]:
        assert not approved_text(item,bad)
    assert not approved_text(item,rows[0]['text']+'\n\n'+rows[0]['text'])
    assert not approved_text(item,rows[-1]['text']+'\n\n'+rows[0]['text'])


@pytest.mark.parametrize('answer',[{'sentences':[0]}, {'sentences':[0,99]}, {'sentences':[True,1]}, {'sentences':[0,0]}, {'post':'新机构称损失300万美元。'}, {'sentences':[]}])
def test_invalid_model_choices_do_not_create_fallback_text(answer):
    client=type('Client',(),{'complete':AsyncMock(return_value=json.dumps(answer,ensure_ascii=False))})()
    assert asyncio.run(compose(client,article())) is None
    assert client.complete.await_count==1


def test_valid_composer_only_returns_exact_published_words():
    client=type('Client',(),{'complete':AsyncMock(return_value='{"sentences":[0,1]}')})()
    item=article();text=asyncio.run(compose(client,item))
    assert text=='\n\n'.join(r['text'] for r in candidates(item)[:2])
    assert client.complete.call_args.kwargs['response_format']=='json'


def test_identity_requires_configured_source_and_canonical_host():
    cfg=config();item=article()
    assert direct_tier(item,cfg)=='original' and eligible(item,cfg)
    item.url='https://theverge.com.attacker.example/story'
    assert direct_tier(item,cfg)=='secondary' and not eligible(item,cfg)
    item.url='https://www.theverge.com/story';item.metadata['feed_name']='Unknown outlet'
    assert not eligible(item,cfg)
    item.metadata['feed_name']='The Verge AI';item.source_type=SourceType.GOOGLE_NEWS
    assert not eligible(item,cfg)
    item.source_type=SourceType.RSS;item.metadata['fallback']='google_news'
    assert not eligible(item,cfg)


def test_official_telegram_identity_does_not_trust_display_label():
    cfg=config();item=article();item.source_type=SourceType.TELEGRAM
    item.metadata['channel']='binance_announcements';item.url='https://www.binance.com/en/support/announcement/new'
    assert direct_tier(item,cfg)=='primary'
    item.url='https://t.me/binance_announcements/123'
    assert direct_tier(item,cfg)=='primary'
    item.url='https://t.me/other_channel/123'
    assert direct_tier(item,cfg)=='secondary'
    for channel in ('foresightnews','theblockbeats'):
        item.metadata['channel']=channel;item.url='https://t.me/'+channel+'/123'
        assert direct_tier(item,cfg)=='secondary'


def test_github_only_accepts_enabled_configured_release_repository():
    cfg=config();item=article();item.source_type=SourceType.GITHUB
    item.metadata['repo']='bitcoin/bitcoin';item.url='https://github.com/bitcoin/bitcoin/releases/tag/v1'
    assert direct_tier(item,cfg)=='primary'
    item.url='https://github.com/bitcoin/bitcoin/issues/1';assert direct_tier(item,cfg)=='secondary'
    item.metadata['repo']='attacker/bitcoin';item.url='https://github.com/attacker/bitcoin/releases/tag/v1'
    assert direct_tier(item,cfg)=='secondary'


def test_brief_low_score_and_marketing_cannot_reach_public_composition():
    cfg=config();item=article()
    for score in (7.99,float('nan'),float('inf')):
        item.ai_score=score;assert not eligible(item,cfg)
    item.ai_score=8;item.metadata['edition_mode']='brief';assert not eligible(item,cfg)
    item.metadata.pop('edition_mode');item.metadata['title_zh']='某币新增交易对即将上币';assert not eligible(item,cfg)


def test_operator_switch_is_authoritative_and_invalid_values_fail_closed():
    assert not effective_enabled(True,{'X_DELIVERY_ENABLED':'false'})
    assert effective_enabled(False,{'X_DELIVERY_ENABLED':'true'})
    assert effective_enabled(True,{}) and not effective_enabled(False,{})
    with pytest.raises(ValueError):effective_enabled(True,{'X_DELIVERY_ENABLED':'yes'})
    assert host('https://safe.example:bad')=='' and host('https://key@safe.example')==''

@pytest.mark.parametrize('sentence',[
    '比特币预计将涨至20万美元。', '以太坊有望在下周上涨。',
    '投资者应该在今天加仓。', '这被认为是一个合适的买点。',
    '市场人士看涨比特币，预计突破十万美元。',
])
def test_forecast_or_advice_is_blocked_even_when_it_was_published(sentence):
    item=article();item.metadata['detailed_summary_zh']=sentence+'用户需要核对自己的软件版本，按照公告中的说明完成安全更新。'
    text='\n\n'.join(r['text'] for r in candidates(item)[:2])
    assert not approved_text(item,text)
