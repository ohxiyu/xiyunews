"""Verify publisher identity against configured source provenance, not labels alone."""
from urllib.parse import urlsplit
from .models import SourceType

DISCOVERY_CHANNELS={'foresightnews','theblockbeats'}
CHANNEL_PUBLISHERS={
    'binance_announcements':('binance.com',),
    'okxannouncements':('okx.com',),
    'bybit_announcements':('bybit.com',),
    'hyperliquid_announcements':('hyperliquid.xyz',),
    'wublockchainenglish':('wublockchain.xyz','wublockchain.com'),
}
AGGREGATOR_HOSTS={'news.google.com','hnrss.org','mshibanami.github.io'}
FALLBACK_FIELDS=('fallback','fallback_source','fallback_google_news','google_news_fallback','gn_query','discovery_fallback')


def host(value):
    try:
        parsed=urlsplit(str(value))
        if parsed.scheme!='https' or parsed.username or parsed.password or parsed.port not in (None,443):return ''
        return (parsed.hostname or '').lower().removeprefix('www.')
    except ValueError:return ''


def same_publisher(actual, expected):
    return bool(expected and (actual==expected or actual.endswith('.'+expected)))


def direct_tier(item,config):
    """X accepts only a direct, enabled configured first-hand/original source."""
    actual=host(item.url)
    if not actual or item.source_type in (SourceType.GOOGLE_NEWS,SourceType.HACKERNEWS,SourceType.EDITORIAL):return 'secondary'
    meta=item.metadata
    if any(meta.get(key) for key in FALLBACK_FIELDS):return 'secondary'
    if item.source_type==SourceType.GITHUB:
        for source in config.sources.github:
            repo=f'{source.owner}/{source.repo}'.lower()
            if source.enabled and source.type=='repo_releases' and str(meta.get('repo','')).lower()==repo and actual=='github.com' and urlsplit(str(item.url)).path.lower().startswith('/'+repo+'/releases/'):
                return 'primary'
        return 'secondary'
    if item.source_type==SourceType.RSS:
        for feed in config.sources.rss:
            expected=host(feed.url)
            if feed.enabled and meta.get('feed_name')==feed.name and expected not in AGGREGATOR_HOSTS and same_publisher(actual,expected):
                return config.filtering.source_tier(feed.name)
        return 'secondary'
    if item.source_type==SourceType.TELEGRAM and config.sources.telegram.enabled:
        channel=str(meta.get('channel','')).lstrip('@').lower()
        if channel in DISCOVERY_CHANNELS:return 'secondary'
        source=next((s for s in config.sources.telegram.channels if s.enabled and not s.probe and s.channel.lower().lstrip('@')==channel),None)
        if source is None:return 'secondary'
        canonical=actual in ('t.me','telegram.me') and urlsplit(str(item.url)).path.lower().startswith('/'+channel+'/')
        publisher=any(same_publisher(actual,p) for p in CHANNEL_PUBLISHERS.get(channel,()))
        if canonical or publisher:return config.filtering.source_tier('@'+channel)
    return 'secondary'
