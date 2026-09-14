# CoinSignal

CoinSignal is a headless Binance market monitor that detects large three-minute
price moves across USDT spot and USD-M futures pairs and sends confirmed
Telegram alerts.

## How it works

1. Every ten minutes, CoinSignal groups Binance pairs by 24-hour quote volume.
2. Every minute, it fetches four one-minute klines for each eligible pair.
3. It compares the current close with the close three minutes earlier.
4. When the configured threshold is crossed, it sends a Telegram alert.
5. A two-hour per-symbol cooldown is recorded only after Telegram confirms
   delivery. Redis preserves cooldowns across restarts when available.

Current thresholds are stored in `config/thresholds.yaml`:

| Market | High volume | Mid volume | Low volume |
| --- | ---: | ---: | ---: |
| Spot | 2.5% | 6% | 10% |
| USD-M futures | 4% | 10% | 20% |

Pairs below USD 500,000 in 24-hour quote volume are ignored.

## Requirements

- Python 3.11 or 3.12
- PM2 for production process management
- Redis is recommended but optional

## Installation

```bash
git clone https://github.com/ohxiyu/coinsignal.git
cd coinsignal
python3.11 -m venv venv
./venv/bin/pip install --require-hashes -r requirements.lock
cp .env.example .env
```

Fill in `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and optionally
`TELEGRAM_ADMIN_ID`. Telegram delivery is enabled by default and missing
credentials stop startup. To run intentionally without Telegram, set
`TELEGRAM_ENABLED=false`; alerts will then be written only to logs.

## Running

Run directly:

```bash
./venv/bin/python run.py
```

Run with PM2:

```bash
./scripts/reload_pm2.sh
./scripts/health_check.sh
```

The PM2 service name and namespace are both `coinsignal`. Paths in
`ecosystem.config.js` are resolved from the checkout directory and are no
longer tied to a specific server path.

## Migration from QweSignalHub

Deploy this repository as `/home/deploy/apps/coinsignal`, copy the old Crypto
Monitor `.env` into the new root, create a fresh virtual environment, then run
`scripts/reload_pm2.sh`. That script removes the retired
`qsh-crypto-monitor` and `qsh-polymarket` PM2 entries before saving the new PM2
process list.

Do not delete the previous checkout until `scripts/health_check.sh` confirms
that `coinsignal` is online and a test alert has been delivered.

## Validation

```bash
python -m ruff check .
python -m mypy src
python -m pytest
```

GitHub Actions runs the same checks on Python 3.11 and 3.12.

## Agent collaboration

Start with [AGENTS.md](AGENTS.md) and [current handoff](docs/handoff.md).
Track scoped work in Issues and delivery evidence in PRs. See the
[backlog](docs/backlog.md), [data contract](docs/data-contract.md),
[message rules](docs/ui-rules.md), and [release records](docs/releases/README.md).

Run `python scripts/check_repository.py` for version, handoff and local Markdown
file-link checks. In a PR, also run `python scripts/check_repository.py --base origin/main`
to enforce handoff and validation records for application changes. CI additionally
compiles Python sources; this headless service has no frontend build step.
