"""Core data models for xiyu.news."""

from datetime import datetime, timezone
from enum import Enum
import re
from typing import Annotated, Literal, Optional, List, Dict, Any, NamedTuple, Union
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, HttpUrl, Field, field_validator, model_validator


class SourceType(str, Enum):
    """Supported information source types."""

    GITHUB = "github"
    HACKERNEWS = "hackernews"
    RSS = "rss"
    REDDIT = "reddit"
    TELEGRAM = "telegram"
    TWITTER = "twitter"
    OPENBB = "openbb"
    OSSINSIGHT = "ossinsight"
    GDELT = "gdelt"
    GOOGLE_NEWS = "google_news"
    EDITORIAL = "editorial"


class SourceDefinition(NamedTuple):
    """How a top-level source is represented in SourcesConfig."""

    config_field: str
    config_is_list: bool = False
    item_fields: tuple[str, ...] = ()


SOURCE_REGISTRY = {
    SourceType.GITHUB.value: SourceDefinition("github", config_is_list=True),
    SourceType.HACKERNEWS.value: SourceDefinition("hackernews"),
    SourceType.RSS.value: SourceDefinition("rss", config_is_list=True),
    SourceType.TELEGRAM.value: SourceDefinition("telegram", item_fields=("channels",)),
    SourceType.GOOGLE_NEWS.value: SourceDefinition("google_news"),
}


class ContentItem(BaseModel):
    """Unified content item model from any source."""

    id: str  # Format: {source}:{subtype}:{native_id}
    source_type: SourceType
    title: str
    url: HttpUrl
    content: Optional[str] = None
    author: Optional[str] = None
    published_at: datetime
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)

    # AI analysis results
    ai_score: Optional[float] = None  # 0-10 importance score
    ai_reason: Optional[str] = None
    ai_summary: Optional[str] = None
    ai_tags: List[str] = Field(default_factory=list)


class AIProvider(str, Enum):
    """Supported AI providers."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    AZURE = "azure"
    ALI = "ali"
    GEMINI = "gemini"
    DOUBAO = "doubao"
    MINIMAX = "minimax"
    DEEPSEEK = "deepseek"
    SILICONFLOW = "siliconflow"
    OLLAMA = "ollama"


# Provider-specific defaults used by setup and provider-chain expansion.
AI_PROVIDER_DEFAULTS = {
    AIProvider.ANTHROPIC: {
        "model": "claude-3-5-sonnet-20241022",
        "api_key_env": "ANTHROPIC_API_KEY",
        "base_url": None,
    },
    AIProvider.OPENAI: {
        "model": "gpt-4",
        "api_key_env": "OPENAI_API_KEY",
        "base_url": None,
    },
    AIProvider.AZURE: {
        "model": "gpt-4",
        "api_key_env": "AZURE_OPENAI_API_KEY",
        "base_url": None,
        "azure_endpoint_env": "AZURE_OPENAI_ENDPOINT",
        "api_version": "2024-10-21",
    },
    AIProvider.ALI: {
        "model": "qwen-plus",
        "api_key_env": "DASHSCOPE_API_KEY",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    },
    AIProvider.GEMINI: {
        "model": "gemini-1.5-flash",
        "api_key_env": "GOOGLE_API_KEY",
        "base_url": None,
    },
    AIProvider.DOUBAO: {
        "model": "doubao-pro-32k",
        "api_key_env": "DOUBAO_API_KEY",
        "base_url": "https://ark.cn-beijing.volces.com/api/v3",
    },
    AIProvider.MINIMAX: {
        "model": "MiniMax-M3",
        "api_key_env": "MINIMAX_API_KEY",
        "base_url": "https://api.minimax.io/v1",
    },
    AIProvider.DEEPSEEK: {
        "model": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "base_url": "https://api.deepseek.com",
    },
    AIProvider.OLLAMA: {
        "model": "llama3.1",
        "api_key_env": "",
        "base_url": "http://localhost:11434/v1",
    },
    AIProvider.SILICONFLOW: {
        "model": "deepseek-ai/DeepSeek-V3.2",
        "api_key_env": "SILICONFLOW_API_KEY",
        "base_url": "https://api.siliconflow.cn/v1",
    },
}


class AIConfig(BaseModel):
    """AI client configuration."""

    provider: AIProvider
    provider_chain: Optional[str] = None
    model: str
    base_url: Optional[str] = None
    api_key_env: str
    temperature: float = 0.3
    max_tokens: int = 4096
    economy_mode: bool = False
    request_timeout_seconds: int = Field(default=120, ge=10, le=600)
    throttle_sec: float = 0.0
    analysis_concurrency: int = 1
    enrichment_concurrency: int = 1
    prefilter_enabled: bool = False
    prefilter_batch_size: int = Field(default=20, ge=5, le=50)
    prefilter_max_candidates: int = Field(default=140, ge=20, le=1000)
    result_cache_enabled: bool = True
    result_cache_path: str = "data/analysis-cache.json"
    result_cache_ttl_days: int = Field(default=30, ge=1, le=365)
    result_cache_max_entries: int = Field(default=4000, ge=100, le=50000)
    languages: List[Literal["zh"]] = Field(default_factory=lambda: ["zh"], min_length=1, max_length=1)
    # Azure OpenAI specific; required when provider == AZURE
    azure_endpoint_env: Optional[str] = None
    api_version: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def reject_retired_evaluator(cls, value):
        if isinstance(value, dict) and "evaluator" in value:
            raise ValueError("ai.evaluator is no longer supported; remove this configuration block")
        return value

    @field_validator("languages")
    @classmethod
    def validate_languages(cls, languages: List[str]) -> List[str]:
        """Allow conventional language tags while excluding path syntax."""
        language_tag = re.compile(r"^[A-Za-z]{2,8}(?:[-_][A-Za-z0-9]{1,8})*$")
        invalid = [language for language in languages if not language_tag.fullmatch(language)]
        if invalid:
            raise ValueError(f"invalid language code: {invalid[0]!r}")
        return languages


class GitHubSourceConfig(BaseModel):
    """GitHub source configuration."""

    type: str  # "user_events", "repo_releases", etc.
    username: Optional[str] = None
    owner: Optional[str] = None
    repo: Optional[str] = None
    enabled: bool = True
    category: Optional[str] = None


class HackerNewsConfig(BaseModel):
    """Hacker News configuration."""

    enabled: bool = True
    fetch_top_stories: int = 30
    min_score: int = 100
    category: Optional[str] = None


class ExtractorType(str, Enum):
    TRAFILATURA = "trafilatura"


class TrafilaturaExtractorConfig(BaseModel):
    type: Literal[ExtractorType.TRAFILATURA] = ExtractorType.TRAFILATURA
    favor_precision: bool = False
    favor_recall: bool = False


ExtractorConfig = Annotated[
    Union[TrafilaturaExtractorConfig],
    Field(discriminator="type"),
]


class RSSSourceConfig(BaseModel):
    """RSS feed source configuration."""

    name: str
    url: HttpUrl
    enabled: bool = True
    category: Optional[str] = None
    content_extractor: Optional[str] = None
    # Public same-publisher index only; never bypass the publisher's access gate.
    fallback_google_news: bool = False








class TelegramChannelConfig(BaseModel):
    """Configuration for monitoring a specific Telegram channel."""

    channel: str  # channel username, e.g. "zaihuapd"
    enabled: bool = True
    fetch_limit: int = 20
    # The public preview shows about 20 messages per page. A busy channel
    # needs older pages (``?before=<id>``) to cover the collection window.
    pages: int = Field(default=1, ge=1, le=5)
    category: Optional[str] = None
    # Trial mode: fetch and report the channel (title, subscribers, message
    # counts) without letting its messages into the edition. Crypto channel
    # names are often impersonated, so a new channel stays in probe until a
    # maintainer has confirmed from the report that it is the real one.
    probe: bool = False


class TelegramConfig(BaseModel):
    """Telegram source configuration."""

    enabled: bool = True
    channels: List[TelegramChannelConfig] = Field(default_factory=list)












class GoogleNewsConfig(BaseModel):
    """Google News RSS search source configuration.

    Builds Google News RSS search URLs
    (https://news.google.com/rss/search) for a query and parses the
    resulting feed via feedparser. No API key is required.
    """

    enabled: bool = False
    query: str = "artificial intelligence"
    language: str = "en"  # hl
    country: str = "US"  # gl
    ceid: Optional[str] = None  # when None scraper derives it as "{country}:{language}"
    max_results: int = 100  # cap ~100
    category: Optional[str] = None
    # Publisher domains to drop (press-release mills, content farms). Matched
    # against the publisher link Google News attaches to every entry.
    blocked_domains: List[str] = Field(default_factory=list)
    allowed_domains: List[str] = Field(default_factory=list)
    # Google News links are opaque redirects; resolve up to this many per
    # fetch to the publisher's article URL (0 disables network resolution).
    resolve_links: int = Field(default=40, ge=0, le=100)
    # More searches in the same fetch, e.g. crypto news restricted to major
    # outlets with site: operators. Each keeps its own category and filters.
    extra_queries: List["GoogleNewsQuery"] = Field(default_factory=list)


class GoogleNewsQuery(BaseModel):
    """One additional Google News search."""

    query: str
    category: Optional[str] = None
    max_results: int = Field(default=20, ge=1, le=100)
    blocked_domains: List[str] = Field(default_factory=list)
    allowed_domains: List[str] = Field(default_factory=list)


GoogleNewsConfig.model_rebuild()


class SourcesConfig(BaseModel):
    """All sources configuration."""

    github: List[GitHubSourceConfig] = Field(default_factory=list)
    hackernews: HackerNewsConfig = Field(default_factory=HackerNewsConfig)
    rss: List[RSSSourceConfig] = Field(default_factory=list)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    google_news: Optional[GoogleNewsConfig] = None






class TelegramDeliveryConfig(BaseModel):
    """Telegram Bot API delivery configuration for published editions."""

    enabled: bool = False
    bot_token_env: str = "TELEGRAM_BOT_TOKEN"
    channel_id_env: str = "TELEGRAM_CHANNEL_ID"
    languages: List[Literal["zh"]] = Field(default_factory=lambda: ["zh"], min_length=1, max_length=1)
    site_url: str = "https://xiyu.news/"
    required: bool = False
    max_message_chars: int = Field(default=3900, ge=512, le=4096)
    featured_items: int = Field(default=3, ge=0, le=10)
    max_items: int = Field(default=10, ge=1, le=20)

    @field_validator("site_url")
    @classmethod
    def validate_site_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("telegram_delivery.site_url must be an HTTP(S) URL")
        return value

    @model_validator(mode="after")
    def validate_item_limits(self) -> "TelegramDeliveryConfig":
        if self.featured_items > self.max_items:
            raise ValueError(
                "telegram_delivery.featured_items must not exceed max_items"
            )
        return self


class XDeliveryConfig(BaseModel):
    """X (Twitter) distribution for published editions.

    Disabled by default. Posting also requires all four OAuth 1.0a
    credentials in the environment, so enabling the flag alone never
    results in an outward-facing post.
    """

    enabled: bool = False
    consumer_key_env: str = "X_CONSUMER_KEY"
    consumer_secret_env: str = "X_CONSUMER_SECRET"
    access_token_env: str = "X_ACCESS_TOKEN"
    access_secret_env: str = "X_ACCESS_SECRET"
    languages: List[Literal["zh"]] = Field(default_factory=lambda: ["zh"], min_length=1, max_length=1)
    site_url: str = "https://xiyu.news/"
    max_items: int = Field(default=3, ge=1, le=5)
    required: bool = False
    # "digest" posts one round-up when the edition publishes.
    # "drip" posts the top stories one at a time across the day, driven by
    # the x-distribution workflow; the publish step then posts nothing.
    mode: Literal["digest", "drip"] = "digest"
    # Drip plan: the first story goes out when the edition publishes, each
    # later one a seeded random gap after the previous post's actual send.
    drip_items: int = Field(default=2, ge=1, le=8)
    drip_gap_min_minutes: int = Field(default=180, ge=30, le=720)
    drip_gap_max_minutes: int = Field(default=360, ge=30, le=720)
    # An edition published later than expected_publish_time plus this delay
    # is not posted to X at all; its news is stale there by then.
    expected_publish_time: str = "07:26"
    max_publish_delay_minutes: int = Field(default=360, ge=0, le=1440)
    # A planned post that has not gone out this long after it was due, or by
    # window_end in the edition's timezone, expires instead of going out late.
    expire_after_minutes: int = Field(default=360, ge=30, le=1440)
    window_end: str = "23:30"
    history_days: int = Field(default=7, ge=1, le=30)
    # Where a drip post sends the reader. "none" posts no link at all, which
    # is what X's ranking favours; "site" keeps readers in the briefing and
    # "source" credits the outlet directly.
    link_target: Literal["none", "site", "source"] = "none"
    # "ai" writes each post in the account's voice; "template" assembles it
    # from the stored title and summary without an extra model call. AI
    # composition always falls back to the template on failure.
    compose: Literal["ai", "template"] = "ai"
    # Weighted characters, counted the way X does (CJK counts double).
    # 280 is the standard-account cap; Premium accounts post far longer.
    # The compact brief targets 90-150 Chinese characters. The configured
    # ceiling leaves headroom for Latin names and numbers within that range.
    max_post_chars: int = Field(default=400, ge=280, le=25000)

    @field_validator("expected_publish_time", "window_end")
    @classmethod
    def validate_clock(cls, value: str) -> str:
        match = re.fullmatch(r"(\d{2}):(\d{2})", value.strip())
        if not match or int(match.group(1)) > 23 or int(match.group(2)) > 59:
            raise ValueError("x_delivery times must be HH:MM")
        return value.strip()

    @model_validator(mode="after")
    def validate_drip_gap(self) -> "XDeliveryConfig":
        if self.drip_gap_min_minutes > self.drip_gap_max_minutes:
            raise ValueError(
                "x_delivery.drip_gap_min_minutes must not exceed drip_gap_max_minutes"
            )
        return self

    @field_validator("site_url")
    @classmethod
    def validate_site_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("x_delivery.site_url must be an HTTP(S) URL")
        return value


class CategoryGroupConfig(BaseModel):
    """A quota group containing one or more source categories."""

    name: Optional[str] = None
    limit: int = Field(gt=0)
    categories: List[str] = Field(min_length=1)
    # Reserve up to this many slots for the group's best stories. Only stories
    # that already passed the score threshold and deduplication are eligible,
    # so a quiet day yields fewer rather than weaker stories.
    min_items: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_min_items(self) -> "CategoryGroupConfig":
        if self.min_items > self.limit:
            raise ValueError("category group min_items must not exceed limit")
        return self


# Ordered best first: first-hand, original reporting, rewrites/aggregators.
SOURCE_TIERS = ("primary", "original", "secondary")


class FilteringConfig(BaseModel):
    """Content filtering configuration."""

    ai_score_threshold: float = 7.0
    time_window_hours: int = 24
    daily_timezone: str = "UTC"
    preserve_daily_items: bool = False
    max_items: Optional[int] = Field(default=None, gt=0)
    category_groups: Dict[str, CategoryGroupConfig] = Field(default_factory=dict)
    default_group: str = "other"
    default_group_limit: Optional[int] = Field(default=None, gt=0)
    primary_groups: List[str] = Field(default_factory=list)
    primary_group_min_items: Optional[int] = Field(default=None, gt=0)
    minimum_candidate_items: Optional[int] = Field(default=None, gt=0)
    minimum_qualified_items: Optional[int] = Field(default=None, gt=0)
    minimum_display_items: Optional[int] = Field(default=None, gt=0)
    low_signal_minimum_items: Optional[int] = Field(default=None, gt=0)
    fallback_window_hours: Optional[int] = Field(default=None, gt=0)
    primary_group_borrow_limit: Optional[int] = Field(default=None, gt=0)
    max_items_per_source: Optional[int] = Field(default=None, gt=0)
    # Editorial source tiers. "primary": first-hand (official channels,
    # regulators, company blogs); "original": outlets doing their own
    # reporting. Everything else is "secondary" (rewrites, aggregators).
    # Entries match the source label (feed name, @channel or outlet name),
    # case-insensitively. Duplicates keep the higher tier.
    source_tiers: Dict[str, List[str]] = Field(default_factory=dict)
    # Most items one tier may fill in an edition, e.g. {"secondary": 4}.
    # Relaxed like max_items_per_source when the edition would be too short.
    source_tier_limits: Dict[str, int] = Field(default_factory=dict)

    @field_validator("source_tiers")
    @classmethod
    def validate_source_tiers(cls, value: Dict[str, List[str]]) -> Dict[str, List[str]]:
        unknown = set(value) - {"primary", "original"}
        if unknown:
            raise ValueError(f"unknown source tiers: {sorted(unknown)}")
        return value

    @field_validator("source_tier_limits")
    @classmethod
    def validate_source_tier_limits(cls, value: Dict[str, int]) -> Dict[str, int]:
        unknown = set(value) - set(SOURCE_TIERS)
        if unknown:
            raise ValueError(f"unknown source tiers: {sorted(unknown)}")
        if any(limit <= 0 for limit in value.values()):
            raise ValueError("source tier limits must be positive")
        return value

    def source_tier(self, label: str) -> str:
        key = label.strip().lower()
        for tier in ("primary", "original"):
            if key in {entry.strip().lower() for entry in self.source_tiers.get(tier, [])}:
                return tier
        return "secondary"

    @field_validator("daily_timezone")
    @classmethod
    def validate_daily_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(f"Unknown IANA timezone: {value}") from exc
        return value

    @model_validator(mode="after")
    def validate_primary_group(self) -> "FilteringConfig":
        if (
            self.primary_group_min_items is not None
            or self.primary_group_borrow_limit is not None
        ) and not self.primary_groups:
            raise ValueError(
                "primary_groups is required when a primary group target or "
                "borrow limit is set"
            )
        missing = [
            group
            for group in self.primary_groups
            if group not in self.category_groups
        ]
        if missing:
            raise ValueError(
                "primary_groups must name configured category groups"
            )
        if self.primary_group_min_items is not None:
            capacity = sum(
                self.category_groups[group].limit
                for group in self.primary_groups
            )
            if self.primary_group_min_items > capacity:
                raise ValueError(
                    "primary_group_min_items cannot exceed primary group capacity"
                )
            if (
                self.max_items is not None
                and self.primary_group_min_items > self.max_items
            ):
                raise ValueError("primary_group_min_items cannot exceed max_items")
        if (
            self.minimum_display_items is not None
            and self.max_items is not None
            and self.minimum_display_items > self.max_items
        ):
            raise ValueError("minimum_display_items cannot exceed max_items")
        if (
            self.low_signal_minimum_items is not None
            and self.max_items is not None
            and self.low_signal_minimum_items > self.max_items
        ):
            raise ValueError("low_signal_minimum_items cannot exceed max_items")
        if (
            self.fallback_window_hours is not None
            and self.fallback_window_hours <= max(24, self.time_window_hours)
        ):
            raise ValueError(
                "fallback_window_hours must exceed the 24-hour edition window "
                "and time_window_hours"
            )
        return self


class Config(BaseModel):
    """Main configuration model."""

    rolling_feed: bool = False

    version: str = "1.0"
    ai: AIConfig
    sources: SourcesConfig
    filtering: FilteringConfig
    extractors: Dict[str, ExtractorConfig] = Field(default_factory=dict)
    telegram_delivery: Optional[TelegramDeliveryConfig] = None
    x_delivery: Optional[XDeliveryConfig] = None
