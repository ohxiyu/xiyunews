---
layout: default
title: Configuration Guide
---

# Configuration Guide

## Quick Post AI preview (unified Worker)

The authenticated /s/ desk reads the existing provider and model from
data/config.github.json. It does not alter the daily model or quota.
Set QUICK_POST_AI_API_KEY as a Cloudflare Worker **Secret**, and
QUICK_POST_AI_ENABLED=true as a Worker variable after the owner confirms the
secret is ready. Both are required. Never copy the key into Git, browser storage,
logs or chat; do not copy it from Actions. Missing configuration returns a clear
503 without model calls, and manual drafts/legacy records remain usable.

No new database or service: existing STATE KV stores validated previews for
24 hours, keyed by exact normalized input, model and prompt version. Only an
explicit generate action invokes AI; publishing and viewing do not. Existing
DeepSeek usage is billable under the owner's current plan; this is not a free
model-call guarantee. No automatic retries, web searches or channel sends.

xiyu.news is configured through two files: a `.env` file for API keys and a `data/config.json` file for sources, AI provider, and filtering options.

## AI Providers

Configure which AI model scores and summarizes your content.

`api_key_env` is always an environment variable name, not the API key value.
Store secrets in `.env` or your shell environment, then point `api_key_env` at
that variable:

```bash
OPENAI_API_KEY=sk-your-key
GOOGLE_API_KEY=your-gemini-key
```

When xiyu.news starts, environment variables have priority because
`data/config.json` does not store the secret. For local VS Code runs, create
`.env` in the repository root and launch xiyu.news from that same root directory.

Common API key variable names:

| Provider | `api_key_env` value |
| --- | --- |
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Azure OpenAI | `AZURE_OPENAI_API_KEY` |
| Gemini | `GOOGLE_API_KEY` |
| MiniMax | `MINIMAX_API_KEY` |
| Aliyun DashScope | `DASHSCOPE_API_KEY` |
| Doubao | `DOUBAO_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |

**Anthropic Claude**:

```json
{
  "ai": {
    "provider": "anthropic",
    "model": "claude-sonnet-4.5-20250929",
    "api_key_env": "ANTHROPIC_API_KEY",
    "throttle_sec": 0
  }
}
```

**OpenAI**:

```json
{
  "ai": {
    "provider": "openai",
    "model": "gpt-4",
    "api_key_env": "OPENAI_API_KEY",
    "throttle_sec": 0
  }
}
```

**Gemini**:

```json
{
  "ai": {
    "provider": "gemini",
    "model": "gemini-2.0-flash",
    "api_key_env": "GOOGLE_API_KEY",
    "throttle_sec": 0
  }
}
```

**Azure OpenAI**:

```json
{
  "ai": {
    "provider": "azure",
    "model": "gpt-4o-production",
    "api_key_env": "AZURE_OPENAI_API_KEY",
    "azure_endpoint_env": "AZURE_OPENAI_ENDPOINT",
    "api_version": "2024-10-21",
    "throttle_sec": 0
  }
}
```

Set `AZURE_OPENAI_API_KEY` and `AZURE_OPENAI_ENDPOINT` in your `.env`. The `model` field should be your Azure deployment name, not just the base model family name.

**MiniMax**:

The built-in provider defaults to `MiniMax-M3` and the global
OpenAI-compatible endpoint:

```json
{
  "ai": {
    "provider": "minimax",
    "model": "MiniMax-M3",
    "api_key_env": "MINIMAX_API_KEY",
    "base_url": "https://api.minimax.io/v1",
    "throttle_sec": 0
  }
}
```

Available models: `MiniMax-M3`, `MiniMax-M2.7`, `MiniMax-M2.7-highspeed`.

Use the endpoint for your account region and preferred compatible API:

| Region | OpenAI-compatible base URL | Anthropic-compatible base URL |
| --- | --- | --- |
| Global | `https://api.minimax.io/v1` | `https://api.minimax.io/anthropic` |
| China | `https://api.minimaxi.com/v1` | `https://api.minimaxi.com/anthropic` |

For the Anthropic-compatible API, keep `provider` set to `minimax` and pass
the base URL directly without adding `/v1`. xiyu.news selects its Anthropic
client for this endpoint, and the SDK appends `/v1/messages` when sending a
request:

```json
{
  "ai": {
    "provider": "minimax",
    "model": "MiniMax-M3",
    "api_key_env": "MINIMAX_API_KEY",
    "base_url": "https://api.minimax.io/anthropic",
    "throttle_sec": 0
  }
}
```

**Aliyun DashScope** (OpenAI-compatible):

```json
{
  "ai": {
    "provider": "ali",
    "model": "qwen-plus",
    "api_key_env": "DASHSCOPE_API_KEY",
    "throttle_sec": 0
  }
}
```

Use the [DashScope compatible-mode](https://help.aliyun.com/zh/dashscope/developer-reference/use-dashscope-by-calling-openai-api) endpoint. Set `DASHSCOPE_API_KEY` in your `.env`. Optional: set `base_url` to override the default `https://dashscope.aliyuncs.com/compatible-mode/v1`.

**Ollama**:

```json
{
  "ai": {
    "provider": "ollama",
    "model": "llama3.1",
    "api_key_env": "",
    "base_url": "http://192.168.1.10:11434",
    "throttle_sec": 0
  }
}
```

Omit `base_url` to use the default `http://localhost:11434/v1`.
For remote Ollama servers, set `ai.base_url` in `data/config.json` or set
`BMTNEWS_OLLAMA_BASE_URL` in `.env`. `OLLAMA_BASE_URL` and `OLLAMA_HOST` are
also recognized. If the value omits `/v1`, xiyu.news appends it automatically
for Ollama's OpenAI-compatible endpoint.

### AI throttling

If your model has a strict per-minute request cap, you can slow the scorer down in `data/config.json`:

```json
{
  "ai": {
    "throttle_sec": 4.5
  }
}
```

- `throttle_sec`: Pause between scored items in seconds. Default is `0`.
- `4.5` is a reasonable starting point for free-tier models capped around 15 requests per minute.
- Set it back to `0` if you have enough throughput headroom and want maximum speed.

### AI Concurrency

By default, AI scoring and enrichment run one item at a time. If your API endpoint supports concurrent requests, you can increase throughput:

```json
{
  "ai": {
    "analysis_concurrency": 4,
    "enrichment_concurrency": 2
  }
}
```

- `analysis_concurrency`: Number of items scored in parallel. Default is `1`.
- `enrichment_concurrency`: Number of high-scoring items enriched in parallel. Default is `1`.
- Both values are clamped to a minimum of `1`.
- Preserve the existing retry behavior per item.
- Result ordering is preserved regardless of concurrency.
- If you also use `throttle_sec`, the wait happens after releasing the concurrency slot.

### AI prefilter and persistent result cache

Large daily windows can use a low-cost batched title prefilter before the
slower per-story analysis. Each failed batch is kept in full, and a reserve
is kept for every configured category so scarce policy or AI coverage is not
silently removed.

```json
{
  "ai": {
    "prefilter_enabled": true,
    "prefilter_batch_size": 20,
    "prefilter_max_candidates": 140,
    "result_cache_enabled": true,
    "result_cache_path": "data/analysis-cache.json",
    "result_cache_ttl_days": 30,
    "result_cache_max_entries": 4000
  }
}
```

The cache key includes the provider model, prompt revision, URL, title and
source content. Changed content or prompts are analyzed again. GitHub Actions
stores this file with the staging cache, making force-republish and recovery
runs incremental without committing it to `main` or `gh-pages`.

**Custom Base URL** (for proxies):

```json
{
  "ai": {
    "provider": "anthropic",
    "base_url": "https://your-proxy.com/v1",
    ...
  }
}
```

For OpenAI-compatible gateways, xiyu.news sends `temperature` by default. If a newer reasoning-style model rejects that parameter with an error such as `temperature is deprecated for this model`, xiyu.news retries once without it and remembers that capability for later requests.

## Information Sources

All sources are configured under the top-level `sources` key in `config.json`.

### GitHub

```json
{
  "sources": {
    "github": [
      {
        "type": "user_events",
        "username": "gvanrossum",
        "enabled": true,
        "category": "oss"
      },
      {
        "type": "repo_releases",
        "owner": "python",
        "repo": "cpython",
        "enabled": true,
        "category": "oss"
      }
    ]
  }
}
```

### Hacker News

```json
{
  "sources": {
    "hackernews": {
      "enabled": true,
      "fetch_top_stories": 30,
      "min_score": 100,
      "category": "tech"
    }
  }
}
```

### RSS Feeds

```json
{
  "sources": {
    "rss": [
      {
        "name": "Blog Name",
        "url": "https://example.com/feed.xml",
        "enabled": true,
        "category": "ai-ml"
      }
    ]
  }
}
```

### Reddit

Reddit scraping is free and does not require API keys. Subreddit posts and comments prefer `old.reddit.com`; JSON and RSS endpoints are used as fallbacks when needed.

```json
{
  "sources": {
    "reddit": {
      "enabled": true,
      "fetch_comments": 5,
      "subreddits": [
        {
          "subreddit": "MachineLearning",
          "sort": "hot",
          "fetch_limit": 25,
          "min_score": 10,
          "category": "ai-ml"
        }
      ],
      "users": [
        {
          "username": "spez",
          "sort": "new",
          "fetch_limit": 10,
          "category": "social"
        }
      ]
    }
  }
}
```

### Telegram

Telegram scraping uses the public web preview at `https://t.me/s/<channel>`, so no API key is required. Only public channels are supported.

```json
{
  "sources": {
    "telegram": {
      "enabled": true,
      "channels": [
        {
          "channel": "zaihuapd",
          "enabled": true,
          "fetch_limit": 20,
          "category": "ai-news"
        }
      ]
    }
  }
}
```

- `enabled` — enable or disable Telegram fetching globally
- `channels` — list of public Telegram channels to monitor
- `channel` — Telegram channel username only, without `@` or the full `https://t.me/` URL
- `fetch_limit` — maximum number of recent messages to inspect per channel per run (default: `20`)
- `pages` — preview pages to read per run (default `1`, at most `5`). The public preview shows about 20 messages per page; a channel that posts more than that between runs needs older pages (`?before=<id>`). Paging stops once a page reaches back past the collection window. Raise `fetch_limit` to match (about 20 per page).
- `category` — optional tag for balanced digest grouping (e.g., `"ai-news"`, `"finance"`)
- `probe` — trial mode (default `false`). The channel is fetched and reported
  but its messages never enter the edition. Crypto channel names are often
  impersonated, so add new channels with `"probe": true`, confirm from the
  run report that the title and subscriber count belong to the official
  channel, then remove `probe`.

Every fetch reports each channel in the run summary ("Telegram 频道" table)
and the Actions log: title, subscribers, messages visible on the public
preview, messages inside the window, messages kept, and the newest message.
`messages_seen` 0 usually means the channel disabled its public preview;
`in_window` 0 with messages seen means nothing new; `kept` below `in_window`
means media-only messages were skipped.

### Twitter

Requires an [Apify](https://apify.com) account. Set `APIFY_TOKEN` in your `.env` file. The free tier includes $5/month of credit, enough for roughly 20,000 tweets.

```json
{
  "sources": {
    "twitter": {
      "enabled": true,
      "users": ["karpathy", "ylecun"],
      "fetch_limit": 10,
      "category": "social",
      "fetch_reply_text": false,
      "max_replies_per_tweet": 3,
      "max_tweets_to_expand": 10,
      "reply_min_likes": 5
    }
  }
}
```

- `users` — Twitter screen names to monitor, without the `@` prefix
- `fetch_limit` — maximum tweets to fetch per run (across all users combined; minimum 100 due to actor constraint)
- `category` — optional tag for balanced digest grouping (applies to all tweets from this source)
- `fetch_reply_text` — when `true`, fetch actual reply bodies for important tweets and append them under `--- Top Comments ---` so the AI can factor in community discussion. Disabled by default.
- `max_replies_per_tweet` — maximum reply lines to append per tweet (default: 3)
- `max_tweets_to_expand` — cap on how many tweets get reply expansion per run, to control Apify credit usage (default: 10)
- `reply_min_likes` — only include replies with at least this many likes (default: 0)

The scraper uses the `altimis/scweet` actor by default. You can override it with `actor_id` if needed.

### OpenBB Financial News

OpenBB is useful when you want equity or macro news from providers such as yfinance, Benzinga, FMP, Intrinio, Tiingo, SEC, or Federal Reserve through one SDK.

Install the optional dependency before enabling the source:

```bash
uv sync --extra openbb
```

If your platform struggles to build transitive dependencies, prefer:

```bash
uv pip install --only-binary=:all: openbb openbb-benzinga
```

```json
{
  "sources": {
    "openbb": {
      "enabled": true,
      "watchlists": [
        {
          "name": "megacaps",
          "enabled": true,
          "provider": "yfinance",
          "fetch_limit": 20,
          "category": "equities",
          "symbols": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
        }
      ]
    }
  }
}
```

- `enabled` — enable or disable the OpenBB source globally
- `watchlists` — list of named ticker groups; each watchlist becomes one `news.company()` call per run
- `name` — label shown in xiyu.news metadata and selection breakdowns
- `provider` — OpenBB provider name such as `yfinance` or `benzinga`
- `fetch_limit` — maximum news rows requested for that watchlist
- `category` — optional tag stored on fetched items
- `symbols` — ticker symbols to fetch together; group symbols by provider to keep requests efficient

OpenBB provider credentials are handled by the OpenBB SDK itself, using its own environment variables or user settings. xiyu.news does not pass those secrets through `data/config.json`.

### OSS Insight (Trending GitHub Repos)

Pulls top star-gain repositories from the [OSS Insight](https://ossinsight.io) public API, which aggregates GitHub WatchEvents. Useful for surfacing repos that are gaining stars right now without needing to scrape GitHub Trending or query BigQuery.

```json
{
  "sources": {
    "ossinsight": {
      "enabled": true,
      "period": "past_24_hours",
      "languages": ["All", "Python", "TypeScript"],
      "keywords": [],
      "min_stars": 10,
      "max_items": 30,
      "category": "oss-trending"
    }
  }
}
```

- `period` — time window for star-gain ranking. Supported: `past_24_hours`, `past_28_days`. (`past_7_days` is currently broken upstream.)
- `languages` — primary language buckets to query. Use `"All"` for the full ranking, or any GitHub language label such as `"Python"`, `"TypeScript"`, `"Rust"`, `"Jupyter Notebook"`. The scraper fans out one request per language and merges results.
- `keywords` — optional case-insensitive substrings matched against `description`, `collection_names`, and `repo_name`. Only repos containing at least one keyword pass through. Leave empty to ingest everything trending.
- `min_stars` — drop repos with fewer than this many stars gained in the period.
- `max_items` — final cap after merging and sorting by `stars_gained` descending.
- `category` — optional tag for balanced digest grouping (e.g., `"oss-trending"`)

No API key is required.

## Filtering

Content is scored 0-10:

- **9-10**: Groundbreaking - Major breakthroughs, paradigm shifts
- **7-8**: High Value - Important developments, deep technical content
- **5-6**: Interesting - Worth knowing but not urgent
- **3-4**: Low Priority - Generic or routine content
- **0-2**: Noise - Spam, off-topic, or trivial

```json
{
  "filtering": {
    "ai_score_threshold": 7.0,
    "time_window_hours": 24,
    "max_items": 20,
    "category_groups": {
      "ai": {
        "name": "AI / Machine Learning",
        "limit": 5,
        "categories": ["ai-news", "ai-tools", "machine-learning", "llm"]
      },
      "finance": {
        "name": "Finance",
        "limit": 5,
        "categories": ["finance", "equities", "crypto"]
      }
    },
    "default_group": "other",
    "default_group_limit": 3,
    "primary_groups": ["finance"],
    "primary_group_min_items": 5,
    "minimum_candidate_items": 20,
    "minimum_qualified_items": 7,
    "minimum_display_items": 5,
    "fallback_window_hours": 36,
    "primary_group_borrow_limit": 6,
    "max_items_per_source": 2,
    "source_tiers": {"primary": ["SEC Press Releases"], "original": ["CoinDesk"]},
    "source_tier_limits": {"secondary": 4}
  }
}
```

- `ai_score_threshold`: Only include content scoring >= this value
- `time_window_hours`: Fetch content from last N hours
- `max_items`: Optional final cap after all group limits are applied
- `category_groups`: Optional map of quota groups. Each group requires a positive
  `limit` and a non-empty `categories` list. Items within each group are kept by
  AI score, highest first.
- `category_groups.*.name`: Optional display name used in run logs
- `default_group`: Group key for items whose category does not match any
  configured group. Default is `other`.
- `default_group_limit`: Optional positive limit for unmatched items. If omitted,
  unmatched items are unlimited except for `max_items`.
- `primary_groups`: Optional list of configured group keys that form the digest's
  main topic.
- `primary_group_min_items`: Optional positive reservation for qualified items
  across `primary_groups`. It cannot exceed `max_items` or the combined primary
  group capacity. The reservation never bypasses the AI threshold or group caps.
- `minimum_candidate_items`: Optional warning threshold for raw candidates in
  the fixed 24-hour edition window.
- `minimum_qualified_items`: Optional warning threshold for items that retain
  the configured AI score after analysis.
- `minimum_display_items`: Optional short-edition threshold. When selection is
  below it, the resilience rules below are activated.
- `low_signal_minimum_items`: Optional empty-edition guard. When nothing
  reaches `ai_score_threshold`, the highest-scored analyzed items (capped at
  two per source) are published instead of an empty edition, up to this
  count, and a `low_signal_edition` alert is recorded. It cannot exceed
  `max_items`.
- `fallback_window_hours`: Optional extended lookback used only when the normal
  edition is short. It must exceed both the fixed 24-hour edition window and
  `time_window_hours`; previously published items remain excluded and the AI
  score threshold is unchanged.
- `primary_group_borrow_limit`: Optional soft per-group limit for unused primary
  topic capacity. Side-topic caps remain hard.
- `max_items_per_source`: Optional cap per outlet in one edition. The outlet
  is the source label, so CoinDesk via RSS and via Google News share one cap.
  Relaxed only when the edition would otherwise fall below
  `minimum_display_items`.
- `source_tiers`: `{"primary": [...], "original": [...]}` source labels (feed
  name, `@channel`, outlet or domain; case-insensitive). Primary is first-hand
  (official channels, regulators, company blogs; GitHub releases and editor
  picks always count as primary); original is outlets that do their own
  reporting; everything else is secondary. When several outlets carry the same
  story, topic dedup keeps the highest-tier copy among those scoring within
  one point of the best.
- `source_tier_limits`: e.g. `{"secondary": 4}`. Most items of a tier in the
  crypto track (`primary_groups`). The crypto target
  (`primary_group_min_items`) is filled first under the cap and then without
  it, so rewrites still appear when original reporting is scarce; other tracks
  keep their own quotas.

When resilience is configured, xiyu.news first selects the normal fixed-window
edition. If it is short, primary groups may borrow unused capacity. Only if the
edition is still short does xiyu.news analyze the older supplemental segment.
Historical identity and semantic-topic deduplication both run before those
items can be selected. A short edition is still published with an explicit run
warning; xiyu.news never reuses a published story or lowers the score threshold.

Balanced digest filtering runs after AI score threshold filtering and topic
deduplication, but before enrichment. This reduces enrichment calls to only the
items that can appear in the final digest.

A group may also set `min_items` (default 0, never above `limit`). Those
slots are filled with the group's best stories before the open ranking, so a
busy day in one track cannot crowd another out. Only stories that already
passed the score threshold and deduplication are eligible; a quiet day yields
fewer stories rather than weaker ones. Production reserves 3 of 14 slots for AI
(`technology`: `min_items` 3, `limit` 5).

Group matching uses the source category stored in `ContentItem.metadata.category`.
All source types support a `category` field: `sources.rss[].category`,
`sources.github[].category`, `sources.hackernews.category`,
`sources.reddit.subreddits[].category`, `sources.reddit.users[].category`,
`sources.telegram.channels[].category`, `sources.twitter.category`,
`sources.openbb.watchlists[].category`, `sources.ossinsight.category`,
`sources.gdelt.category`, and `sources.google_news.category`.
Sources without a category set enter the default group.

If the same category appears in multiple groups, xiyu.news logs a warning and uses
the first group in configuration order. Omitting both `category_groups` and
`max_items` preserves the previous filtering behavior.

## Aggregator Domain Filters

Google News and GDELT surface any page that mentions the query, including
press-release mills. Both accept domain lists, matched against the domain and
its subdomains (`www.` is ignored):

- `sources.google_news.blocked_domains` / `allowed_domains`: checked against the
  publisher link Google News attaches to each entry, before any link resolution.
- `sources.gdelt.blocked_domains` / `allowed_domains`: checked against the
  article domain GDELT reports.
- A non-empty `allowed_domains` keeps only those domains; `blocked_domains`
  always wins.

`sources.google_news.resolve_links` (default 40, 0 disables) resolves that many
opaque `news.google.com` redirect links per fetch to the publisher's article
URL. A failed resolution keeps the redirect link, so it never drops an item.

`sources.google_news.extra_queries` runs more searches in the same fetch, each
with its own `query`, `category`, `max_results` (default 20) and domain lists;
link resolution shares the one `resolve_links` budget. A story returned by
several searches keeps the first search's category. A failed search does not
affect the others. Production uses one to follow crypto coverage by major
outlets (`site:` operators plus an `allowed_domains` list), which replaced
GDELT after its API rate-limited every GitHub Actions run.

## Environment Variable Substitution

Any string value in `data/config.json` supports `${VAR_NAME}` syntax. Variables are expanded at runtime from the environment (including values loaded from `.env`). This lets you keep secrets, tenant-specific endpoints, and private URLs out of the checked-in JSON file.

Example:

```json
{
  "ai": {
    "base_url": "${BMTNEWS_AI_BASE_URL}"
  },
  "sources": {
    "rss": [
      {
        "name": "LWN.net",
        "url": "https://lwn.net/headlines/full_text?key=${LWN_KEY}",
        "enabled": true
      }
    ]
  },
  "webhook": {
    "url_env": "BMTNEWS_WEBHOOK_URL",
    "headers": "Authorization: Bearer ${BMTNEWS_WEBHOOK_TOKEN}"
  }
}
```

- `${NAME}` is replaced only when `NAME` is a valid identifier like `LWN_KEY` or `BMTNEWS_AI_BASE_URL`.
- Unset variables are left as `${NAME}` instead of becoming an empty string, so configuration mistakes fail loudly downstream.
- Expansion is recursive through dicts, lists, and tuples; non-string values are left unchanged.

## Email Subscription

Email delivery is optional and disabled unless `email.enabled` is `true`. xiyu.news uses SMTP to send daily summaries and IMAP to check subscribe/unsubscribe requests.

```json
{
  "email": {
    "enabled": true,
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "smtp_username": null,
    "imap_enabled": true,
    "imap_server": "imap.qq.com",
    "imap_port": 993,
    "email_address": "xxx@qq.com",
    "password_env": "EMAIL_PASSWORD",
    "sender_name": "xiyu.news Daily",
    "subscribe_keyword": "SUBSCRIBE",
    "unsubscribe_keyword": "UNSUBSCRIBE"
  }
}
```

- `enabled`: Turns email subscription handling and daily email delivery on or off.
- `smtp_server` / `smtp_port`: SMTP server used to send emails.
- `smtp_username`: Optional SMTP login username. If omitted, xiyu.news uses `email_address`.
- `imap_enabled`: Turns IMAP subscribe/unsubscribe checks on or off. Set it to `false` for send-only SMTP providers.
- `imap_server` / `imap_port`: IMAP server used to scan incoming subscription requests when `imap_enabled` is `true`.
- `email_address`: Sender account and mailbox checked for subscription requests.
- `password_env`: Environment variable containing the email password or app password. Defaults to `EMAIL_PASSWORD`.
- `sender_name`: Display name shown in sent emails.
- `subscribe_keyword` / `unsubscribe_keyword`: Keywords xiyu.news looks for in incoming email subjects.

Resend SMTP example:

```json
{
  "email": {
    "enabled": true,
    "smtp_server": "smtp.resend.com",
    "smtp_port": 465,
    "smtp_username": "resend",
    "password_env": "RESEND_API_KEY",
    "imap_enabled": false,
    "imap_server": "",
    "imap_port": 993,
    "email_address": "noreply@example.com",
    "sender_name": "xiyu.news Daily"
  }
}
```

Set `RESEND_API_KEY` in `.env`. Recipients are loaded from `data/subscribers.json`.

## Telegram Daily Edition Delivery

Telegram delivery uses the official Bot API to publish one compact edition to
a channel after the daily summary is generated. It is separate from
`sources.telegram`, which only collects posts from public channels.

```json
{
  "telegram_delivery": {
    "enabled": true,
    "bot_token_env": "TELEGRAM_BOT_TOKEN",
    "channel_id_env": "TELEGRAM_CHANNEL_ID",
    "languages": ["zh"],
    "site_url": "https://xiyu.news/",
    "required": false,
    "max_message_chars": 3900,
    "featured_items": 3,
    "max_items": 10
  }
}
```

- `enabled`: Enables delivery after an edition is generated.
- `bot_token_env`: Environment variable containing the BotFather token.
- `channel_id_env`: Environment variable containing a public channel username
  such as `@channelname`, or the channel's numeric ID.
- `languages`: Languages to publish. xiyu.news uses `["zh"]` so the bilingual
  generation loop sends only one channel message per day.
- `site_url`: Link appended to the message for the complete edition.
- `required`: When `true`, a missing credential or failed Telegram request
  fails the publication run. When `false`, the website continues publishing
  and the run report records the skipped or failed delivery.
- `max_message_chars`: Maximum rendered message size. Keep this at or below
  Telegram's 4096-character `sendMessage` limit. The renderer keeps whole HTML
  blocks and links instead of cutting through markup.
- `featured_items`: Number of leading stories that include one complete lead
  sentence. Remaining stories use a compact title-only list.
- `max_items`: Maximum number of ranked story titles in the channel message;
  omitted stories remain available through the full-edition link.

Online setup requires no local service:

1. Create a bot with [@BotFather](https://t.me/BotFather).
2. Add the bot to the destination channel as an administrator with permission
   to post messages.
3. In GitHub, open **Settings → Secrets and variables → Actions** and create
   `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHANNEL_ID` repository secrets. The
   channel value may be `@channelname`, a plain username, a `t.me` URL, or the
   channel's `-100…` numeric ID.
4. Normal 07:26 publication runs send automatically after generation completes.
   Do not force-republish an existing edition to test delivery: rebuilt editions
   deliberately skip Telegram. For a confirmed bot-not-member 403, use the
   manual **xiyu.news Telegram Recovery** workflow on `main`, entering the published
   date and original Daily Edition run ID. First leave `send=false` to verify
   permissions without posting, then dispatch once with `send=true` after checking
   the channel. It reuses the existing compact message, with no AI or publication
   writes. Other failures (including timeouts), changed editions, send reruns and
   any earlier send invocation for that date are refused. Inspect ambiguous
   outcomes manually: Telegram provides no sendMessage idempotency key.
   Sanitized receipts are kept as Actions artifacts for 90 days; the conservative
   duplicate gate uses workflow history, not artifact retention. This is an
   operator recovery tool, not a new automatic retry or queue service.

The token is used only to call the official
[`sendMessage`](https://core.telegram.org/bots/api#sendmessage) endpoint and is
never included in saved summaries, run reports, or logs. The checked-in GitHub
configuration is safe when Secrets are absent: delivery is skipped and the
site still publishes.

## Webhook Notification

Webhook notification is optional and disabled unless `webhook.enabled` is `true`. xiyu.news can call Feishu/Lark, DingTalk, Slack, Discord, or any custom webhook endpoint when the pipeline succeeds or fails.

```json
{
  "webhook": {
    "enabled": true,
    "url_env": "BMTNEWS_WEBHOOK_URL",
    "delivery": "summary",
    "overview_position": "first",
    "platform": "generic",
    "layout": "markdown",
    "fallback_layout": "markdown",
    "languages": null,
    "request_body": {
      "text": "#{message_title}\n#{summary}"
    },
    "headers": ""
  }
}
```

- `enabled`: Turns webhook delivery on or off. The default is `false`.
- `url_env`: Environment variable that contains the webhook URL. For example, set `BMTNEWS_WEBHOOK_URL=https://...` in `.env`.
- `delivery`: Controls how messages are sent. Use `summary` for one full message, or `summary_and_items` for one overview message followed by one message per selected item.
- `overview_position`: Controls where the overview is sent in `summary_and_items` mode. Use `first` for the traditional order, or `last` to send item details in reverse and keep the overview as the newest chat message.
- `platform`: Optional webhook platform hint. Use `generic` by default, or `feishu` / `lark` to enable platform-specific card rendering.
- `layout`: Controls the message layout. Use `markdown` for templated Markdown delivery, or `collapsible` with `platform: "feishu"` / `"lark"` for a single Feishu Card JSON 2.0 message with each item in a collapsed panel.
- `fallback_layout`: Reserved fallback layout for unsupported platform/layout combinations. The current safe fallback is `markdown`.
- `languages`: Optional webhook-only language filter. Use `["zh"]` or `["en"]` to send only selected languages; use `null` or omit it to send all configured `ai.languages`.
- `request_body`: Optional request body. If empty, xiyu.news sends a `GET` request. If provided, xiyu.news sends a `POST` request.
- `headers`: Optional custom headers, one `Key: Value` pair per line.

When `request_body` is a JSON object or array, xiyu.news renders placeholders and serializes it as JSON. When it is a string, xiyu.news renders it directly and detects JSON if the rendered string is valid JSON.

### Delivery Modes And Layouts

`delivery` controls how many webhook messages xiyu.news sends:

- `summary`: Sends one message containing the full daily summary. This is simple, but some chat platforms may reject long messages.
- `summary_and_items`: Sends one overview message plus one message per selected item. In each item message, `#{summary}` contains only that item's Markdown body. This is useful for platforms that reject or truncate long messages.

`layout` controls how each message is rendered:

- `markdown`: Uses your `request_body` template for each message. This is the default and works with generic webhooks, DingTalk, Slack, Discord, Feishu, and Lark.
- `collapsible`: Currently supported for `platform: "feishu"` or `"lark"`. xiyu.news ignores `request_body` and builds one Feishu/Lark Card JSON 2.0 message with each item in a collapsed panel.

For platforms without a platform-specific layout, keep `layout: "markdown"` and choose the message count with `delivery`.

Example `summary_and_items` Markdown delivery config:

```json
{
  "webhook": {
    "enabled": true,
    "url_env": "BMTNEWS_WEBHOOK_URL",
    "delivery": "summary_and_items",
    "overview_position": "last",
    "platform": "generic",
    "layout": "markdown",
    "request_body": {
      "text": "#{message_title}\n\n#{summary?limit=3000&split=---}"
    }
  }
}
```

With `summary_and_items`, xiyu.news sends one overview plus one message per selected item. `overview_position: "last"` sends item messages first and keeps the overview as the newest chat message; omit it or set `"first"` to send the overview first.

### Webhook Templates

Available variables:

| Variable | Description |
|----------|-------------|
| `#{date}` | Report date, for example `2026-04-24` |
| `#{language}` | Language code, such as `en` or `zh` |
| `#{important_items}` | Number of items that passed the score threshold |
| `#{all_items}` | Total number of fetched items |
| `#{result}` | `success` or `failed` |
| `#{timestamp}` | Unix timestamp |
| `#{message_title}` | Message title, such as the daily title, overview title, or item title |
| `#{message_kind}` | Message kind: `summary`, `overview`, `item`, `failure`, or `manual` |
| `#{summary}` | Message Markdown. In `summary_and_items` mode this is the overview or one item body, depending on the message |

When `delivery` is `summary_and_items`, item messages also include:

| Variable | Description |
|----------|-------------|
| `#{item_index}` | 1-based item number |
| `#{item_count}` | Total number of item messages |
| `#{item_title}` | Current item title |
| `#{item_url}` | Current item URL |
| `#{item_score}` | Current item AI score |

For webhook delivery, xiyu.news flattens HTML disclosure blocks such as `<details><summary>...</summary>` in `#{summary}` into plain Markdown link lists. This makes the generated summary easier to render in chat products. Saved Markdown files, GitHub Pages, and email content are unchanged.

Use `#{key?limit=N&split=DELIM}` to truncate long values by splitting on `DELIM` and keeping segments until the total character count reaches `N`.

```text
#{summary?limit=3000&split=---}
```

### DingTalk

In DingTalk, create a custom group robot and use a custom keyword such as `xiyu.news`. The keyword must appear in the body content.

```json
{
  "msgtype": "markdown",
  "markdown": {
    "title": "xiyu.news #{date} Daily",
    "text": "xiyu.news result: #{result}\n\nxiyu.news important items: #{important_items}/#{all_items}\n\n#{summary}"
  }
}
```

### Feishu / Lark

In Feishu or Lark, create a custom group robot and use a custom keyword such as `xiyu.news`. The keyword must appear in the body content.

Use Card JSON 2.0 for Markdown rendering. The card must include `"schema": "2.0"` and put rich-text Markdown components under `card.body.elements`.

To keep the group chat compact while still allowing readers to browse the full briefing inside Feishu, use the collapsible layout:

```json
{
  "webhook": {
    "enabled": true,
    "url_env": "BMTNEWS_WEBHOOK_URL",
    "platform": "feishu",
    "layout": "collapsible",
    "fallback_layout": "markdown",
    "languages": ["zh"]
  }
}
```

With this layout, xiyu.news sends one interactive card containing the overview and one collapsed panel per selected item. Each panel can be expanded in Feishu to read the full item detail. The regular `request_body` template is ignored for this rendered card.

```json
{
  "msg_type": "interactive",
  "card": {
    "schema": "2.0",
    "config": {
      "wide_screen_mode": true
    },
    "header": {
      "title": {
        "tag": "plain_text",
        "content": "#{message_title}"
      },
      "template": "blue"
    },
    "body": {
      "elements": [
        {
          "tag": "markdown",
          "content": "xiyu.news result: #{result}\nxiyu.news important items: #{important_items}/#{all_items}"
        },
        {
          "tag": "hr"
        },
        {
          "tag": "markdown",
          "content": "#{summary}"
        }
      ]
    }
  }
}
```

## Static Site

xiyu.news writes generated summaries to `data/summaries/` and copies publishable Markdown into `docs/` for the GitHub Pages site. The repository includes a ready-to-use workflow at `.github/workflows/daily-summary.yml`.

To use GitHub Pages, enable Pages for the repository and run the scheduled workflow or trigger it manually. The generated site is built from the `docs/` directory.

## MCP Server

xiyu.news includes an MCP server for AI assistants and MCP-compatible clients.

```bash
uv run bmtnews-mcp
```

Available tools include `bmt_validate_config`, `bmt_fetch_items`, `bmt_score_items`, `bmt_filter_items`, `bmt_enrich_items`, `bmt_generate_summary`, and `bmt_run_pipeline`.

See [`src/mcp/README.md`](../src/mcp/README.md) for the full tool reference and [`src/mcp/integration.md`](../src/mcp/integration.md) for client setup.

## 生产新闻评分与去重

生产配置为 `ai.provider=siliconflow`、`ai.model=deepseek-ai/DeepSeek-V3.2`。同一次分析调用
直接返回 0–10 重要性分数、理由、摘要、标签和内容分类；提示词包含五档
评分锚点及时效规则。`filtering.ai_score_threshold` 保持 7.0。粗筛失败
进入完整分析；分析响应无法解析时记零分并且不缓存为有效分析。

URL 规范化去重之后，事件目录匹配与 AI 语义比较分别处理跨日
重报和当期相同事件。语义比较至多两次尝试，失败会留下脱敏诊断并
停止发布，不会把未经比较的候选整批放行。扩写使用来源正文和搜索摘要；
引用只能选自实际搜索结果。没有独立的扩写后事实核验。扩写失败时
回退翻译，运行报告标记降级。

分析缓存键包括模型、评分策略版本、提示词及来源输入，旧策略的分数
不会当作当前分数复用；生产缓存 30 天自然过期，不手改缓存分支。
运行报告汇总 `score_models`，新归档行有 `score_model`。已有归档不
重新评分；周报的历史分数仍按原值读取，切换初期须人工观察新旧
分数分布与 7.0 门槛的命中数量。


## 硅基流动接入

`AIProvider.SILICONFLOW`及生产日报使用`deepseek-ai/DeepSeek-V3.2`，
接口仍为`https://api.siliconflow.cn/v1`，密钥环境变量仍为`SILICONFLOW_API_KEY`。
这是用户2026-11-08明确指定的模型切换，沿用已配置Secret；无需改密钥或使用DeepSeek官方账户。
参见[硅基流动文本生成文档](https://docs.siliconflow.cn/docs/userguide/capabilities/text-generation)。

按[硅基流动协议](https://docs.siliconflow.cn/docs/userguide/capabilities/reasoning)，
客户端发送`enable_thinking`，不发送DeepSeek官方接口的`thinking`或`reasoning_effort`。
经济模式下所有JSON任务（含动态评分、扩写、事件关联）关闭额外思考，保留最终回答预算；
复杂任务8192，简单评分1536。非经济模式及自由正文仍按既有策略启用思考，
`thinking_budget=4096`。仅返回最终`content`，拒绝空答案与截断输出。
120秒整次请求和30分钟工作流上限、并发、重试及费用边界保持原值。

背景检索优先寻找主体身份、前因与必要机制，不再因主体知名或新闻看似自明而跳过。
每项最多3条查询；查询为空、格式错误或提取失败时，使用来源标题构造1条定向背景查询，
不增加AI调用次数。扩写优先提供1–3句中英背景，事实在两种语言中保持一致；
单侧缺失或非文本背景按既有重试和翻译降级路径处理。来源及搜索均无可靠背景时允许两侧留空，
不填占位、不重复正文凑数、不编造历史，引用仍限于真实搜索URL。
生成字段与HTML展示均须验收，公开摘要API没有背景字段，不据此判断生成丢失。

新缓存按`siliconflow:deepseek-ai/DeepSeek-V3.2`及完整背景提示词隔离，旧模型/旧提示的结果
自然失效，不手改缓存或历史归档。缺密钥或401/402/403保持脱敏快速失败。
实际调用有费用；不因模型切换承诺永久免费或永不失败。

## 核心站生产配置（2026-11-08）

`core_only: true` 与 `ai.languages: ["zh"]` 选择中文核心流水线，模型维持硅基流动 `deepseek-ai/DeepSeek-V3.2`。`x_delivery.enabled` 为 false，邮件/Webhook 关闭，Telegram 仅中文日报，由独立发布后任务处理。英文旧渲染器和非核心库代码保留，生产任务与路由停用。仅开启旧库开关不能恢复已退役的生产入口或发送计划。

## Daily reliability and private operations

The Chinese profile requires both a Chinese title and summary. A missing Chinese
field gets one translation repair; an invalid result is excluded rather than
published in English. Account HTTP 401/402/403 stops retries and queued AI work.
If enrichment is unavailable, the edition uses scored Chinese summaries and is
marked 简版. If scoring/deduplication is unavailable, only a previously qualified
cohort in the exact edition window may be used (`data/qualified-cache.json`).
No qualified cohort means no edition. Brief editions cannot enter X delivery.
Existing published editions and Telegram delivery receipts remain authoritative.

- Actions Secret `TELEGRAM_ALERT_CHAT_ID`: a positive numeric **private** chat ID.
  The existing `TELEGRAM_BOT_TOKEN` is reused. `getChat` must confirm a private
  destination; no channel/group fallback is permitted. Start a chat with the bot
  before testing. Feed Collection → Run workflow → `alert_test=true` sends one
  test, without collection/publication. The test fails unless delivery is confirmed.
- Runner `XIYUNEWS_STATE_DIR`: existing durable publication SQLite directory,
  e.g. the path configured by `ops/runner/30-publication-state.conf`. Cost ledger
  and alert receipts use this same database. Missing durable state reports
  `state_unavailable` and refuses to send; never use an ephemeral retry receipt.
- Optional repository variables `AI_BALANCE_BASELINE_CNY` and
  `AI_BALANCE_BASELINE_AT`: manually observed balance and timezone-aware ISO time.
  SiliconFlow retired `/user/info` on 2026-08-14; no balance request uses that
  endpoint. Missing/invalid baseline means unknown balance. Remaining-day alerts
  require seven complete recorded days and priced usage. Estimates only cover
  this project's recorded usage; account-wide consumption/top-ups are not known.
- `run_report.ai_cost`: estimated CNY at SiliconFlow DeepSeek-V3.2 prices
  (input 4, cached input 0.4, output 6 per million tokens). Reasoning tokens are
  included in output, never billed twice. Other models are marked unpriced.
  Per-run ledger writes are idempotent; daily/month totals show recorded usage,
  not a provider invoice. Financial estimates remain in private artifacts.
- The normal unified deployment copies a configured private destination into the
  Worker's optional `TELEGRAM_ALERT_CHAT_ID` and `DAILY_TELEGRAM_BOT_TOKEN` bindings.
  The latter reuses the existing Actions daily bot; it leaves the independent
  realtime watchdog's `TELEGRAM_BOT_TOKEN` and `ALERT_CHAT_ID` unchanged. Worker checks collection lag
  (>30 minutes, one alert until recovery) and missing editions after 07:45.
- Alert attempts are persisted before sending; timeouts/5xx become unknown and
  are never retried automatically. `not_configured`, `destination_unverified`,
  `state_unavailable`, failed and unknown must not be described as delivered.

Official provider changes/prices:
https://docs.siliconflow.cn/docs/release-notes/overview
