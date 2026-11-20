"""OAuth user verification and one-shot planned X POST; no digest or template sender."""
from __future__ import annotations
import base64,hashlib,hmac,os,re,secrets,time
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote,urlsplit,parse_qsl
import httpx
from rich.console import Console
from ..models import ContentItem,XDeliveryConfig


X_TWEETS_ENDPOINT = "https://api.x.com/2/tweets"

TWEET_LIMIT = 280

TCO_LENGTH = 23

_SINGLE_WEIGHT_RANGES = (
    (0x0000, 0x10FF),
    (0x2000, 0x200D),
    (0x2010, 0x201F),
    (0x2032, 0x2037),
)

_URL_PATTERN = re.compile(r"https?://\S+")

def _percent_encode(value: str) -> str:
    return quote(str(value), safe="-._~")

def _oauth_header(
    method: str,
    url: str,
    *,
    consumer_key: str,
    consumer_secret: str,
    access_token: str,
    access_secret: str,
    nonce: str | None = None,
    timestamp: str | None = None,
) -> str:
    """Build an OAuth 1.0a Authorization header for a JSON-body request.

    A JSON body is not part of the signature base string; only the request
    method, URL, and OAuth parameters are signed.
    """
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": nonce or secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": timestamp or str(int(time.time())),
        "oauth_token": access_token,
        "oauth_version": "1.0",
    }
    split = urlsplit(url)
    pairs = [*parse_qsl(split.query, keep_blank_values=True), *oauth_params.items()]
    parameter_string = "&".join(
        f"{key}={value}" for key, value in sorted(
            (_percent_encode(key), _percent_encode(value)) for key, value in pairs)
    )
    base_url = f"{split.scheme}://{split.netloc}{split.path}"
    base_string = "&".join(
        [
            method.upper(),
            _percent_encode(base_url),
            _percent_encode(parameter_string),
        ]
    )
    signing_key = (
        f"{_percent_encode(consumer_secret)}&{_percent_encode(access_secret)}"
    )
    signature = base64.b64encode(
        hmac.new(
            signing_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha1,
        ).digest()
    ).decode("ascii")
    header_params = {**oauth_params, "oauth_signature": signature}
    joined = ", ".join(
        f'{_percent_encode(key)}="{_percent_encode(header_params[key])}"'
        for key in sorted(header_params)
    )
    return f"OAuth {joined}"

def _character_weight(text: str) -> int:
    """Weighted length of text containing no URLs."""
    total = 0
    for char in text:
        code = ord(char)
        if any(start <= code <= end for start, end in _SINGLE_WEIGHT_RANGES):
            total += 1
        else:
            total += 2
    return total

def _weighted_length(text: str) -> int:
    """Count a post the way X does, collapsing every URL to a t.co token."""
    total = 0
    position = 0
    for match in _URL_PATTERN.finditer(text):
        total += _character_weight(text[position : match.start()])
        total += TCO_LENGTH
        position = match.end()
    return total + _character_weight(text[position:])

def post_source_fields(item: ContentItem, language: str) -> dict[str, str]:
    """The published fields a post may draw on, and nothing else.

    These are exactly what the reader sees on the edition page. The raw
    article body is deliberately excluded: it is unedited source text, and a
    post built from it can carry claims the page itself left out.
    """
    if language != 'zh':
        raise ValueError('Only Chinese daily distribution is supported')
    metadata = item.metadata or {}

    def field(name: str) -> str:
        return str(metadata.get(f'{name}_{language}') or metadata.get(name) or '').strip()
    return {'title': str(metadata.get(f'title_{language}') or item.title or '').strip(), 'summary': field('detailed_summary') or str(item.ai_summary or '').strip(), 'background': field('background'), 'market_impact': field('market_impact'), 'discussion': field('community_discussion')}

async def compose_story_post(ai_client, item: ContentItem, *, language: str, limit: int=280) -> Optional[str]:
    """Select complete published sentences; an invalid choice has no fallback."""
    if language != 'zh':raise ValueError('Only Chinese daily distribution is supported')
    from ..x_quality import compose
    return await compose(ai_client,item,limit=limit)

@dataclass(frozen=True)
class PostOutcome:
    """What one planned-post attempt proved about the post.

    ``kind`` is one of:

    - ``sent``: X accepted the post and returned its id.
    - ``not_sent``: the request provably never reached X (no connection), so
      trying again cannot produce a duplicate.
    - ``rate_limited``: X refused with HTTP 429 and created nothing.
    - ``failed``: X refused definitively (401, 403, other 4xx). Retrying the
      same request will not help; a person has to look.
    - ``unknown``: the request may have been accepted (timeout after sending,
      5xx, unreadable success body). Never retried automatically.

    ``detail`` is safe for public logs: it never contains a response body.
    """

    kind: str
    detail: str = ""
    tweet_id: str = ""

class XEditionPublisher:
    """Post one compact edition summary to X."""

    def __init__(self, config: XDeliveryConfig, *, console: Console | None=None, transport: httpx.AsyncBaseTransport | None=None) -> None:
        self.config = config
        self.console = console or Console()
        self.transport = transport

    def _credentials(self) -> tuple[str, str, str, str]:
        return (os.getenv(self.config.consumer_key_env, '').strip(), os.getenv(self.config.consumer_secret_env, '').strip(), os.getenv(self.config.access_token_env, '').strip(), os.getenv(self.config.access_secret_env, '').strip())

    async def verify_account(self) -> dict:
        """Read the existing user context; this does not prove POST entitlement."""
        credentials = self._credentials()
        if not all(credentials):
            return {'status': 'missing_credentials'}
        endpoint = 'https://api.x.com/2/users/me?user.fields=public_metrics'
        authorization = _oauth_header('GET', endpoint, consumer_key=credentials[0], consumer_secret=credentials[1], access_token=credentials[2], access_secret=credentials[3])
        try:
            async with httpx.AsyncClient(timeout=15, transport=self.transport, follow_redirects=False) as client:
                response = await client.get(endpoint, headers={'Authorization': authorization})
            if response.status_code != 200:
                return {'status': 'unavailable', 'http_status': response.status_code}
            data = response.json().get('data', {})
            username = data.get('username')
            identity = str(data.get('id') or '')
            if not isinstance(username, str) or not identity.isdecimal():
                return {'status': 'invalid_response'}
            if username.lower() != 'ohxiyu':
                return {'status': 'wrong_account', 'username': username}
            result = {'status': 'verified', 'username': username, 'write_access': 'not_yet_observed'}
            followers = data.get('public_metrics', {}).get('followers_count')
            if type(followers) is int and followers >= 0:
                result['followers_count'] = followers
            return result
        except Exception:
            return {'status': 'unavailable'}

    def not_ready_reason(self) -> str:
        """Why a planned post cannot be attempted now, or "" when it can.

        Checked before a job is marked pending, so a missing credential leaves
        the plan untouched instead of producing an attempt that never ran.
        """
        if not self.config.enabled:
            return 'X delivery is disabled in the configuration.'
        if not all(self._credentials()):
            return 'X credentials are not fully configured; nothing posted.'
        return ''

    async def publish_post(self, text: str) -> PostOutcome:
        """Attempt one planned post and classify what the attempt proved."""
        reason = self.not_ready_reason()
        if reason:
            return PostOutcome('not_sent', reason)
        if not text.strip():
            return PostOutcome('not_sent', 'Nothing to post.')
        if _weighted_length(text)>min(self.config.max_post_chars,280):
            return PostOutcome('failed','Stored post exceeds the approved weighted limit.')
        consumer_key, consumer_secret, access_token, access_secret = self._credentials()
        authorization = _oauth_header('POST', X_TWEETS_ENDPOINT, consumer_key=consumer_key, consumer_secret=consumer_secret, access_token=access_token, access_secret=access_secret)
        try:
            async with httpx.AsyncClient(timeout=20.0, transport=self.transport) as client:
                response = await client.post(X_TWEETS_ENDPOINT, headers={'Authorization': authorization, 'Content-Type': 'application/json'}, json={'text': text})
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            return PostOutcome('not_sent', f'X request not sent: {type(exc).__name__}')
        except httpx.HTTPError as exc:
            return PostOutcome('unknown', f'X request outcome unknown: {type(exc).__name__}')
        code = response.status_code
        if code == 429:
            return PostOutcome('rate_limited', 'X API returned HTTP 429.')
        if code >= 500:
            return PostOutcome('unknown', f'X API returned HTTP {code}.')
        if code >= 400:
            return PostOutcome('failed', f'X API returned HTTP {code}.')
        try:
            tweet_id = str((response.json().get('data') or {}).get('id') or '')
        except (ValueError, AttributeError):
            tweet_id = ''
        if not tweet_id.isdigit():
            return PostOutcome('unknown', f'X API returned HTTP {code} without a post id.')
        return PostOutcome('sent', f'X API returned HTTP {code}.', tweet_id)
