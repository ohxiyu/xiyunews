# FomoBTC

Low-latency Binance spot move alerts, official exchange announcements and on-chain
Binance flows, delivered through one Telegram group.
Formerly CoinSignal; the repository is now https://github.com/ohxiyu/fomobtc.

Delivery: one Telegram forum group with topics for market moves, exchange
announcements and on-chain Binance flows (no web frontend). Current deployment and remaining
credential requirements: [handoff](docs/handoff.md).

## Runtime

- Python 3.11/3.12, asyncio/aiohttp; one VPS process managed by systemd.
- Binance spot aggregate trades, one rule: the price moved 2% / 3% / 5% (by 24h volume
  tier) within the last 3 minutes and held for 3s. Same coin and direction alert once
  per hour, sooner after a further 10% move; new 24h highs/lows are noted. Settings
  live in [config/thresholds.yaml](config/thresholds.yaml); exact rules in the
  [data contract](docs/data-contract.md).
- Binance signed English announcement stream, OKX REST polling, Hyperliquid
  public channel preview fallback or an optional authorized Telegram client.
- SQLite WAL stores immutable events, a persistent outbox and the per-coin,
  per-direction alert gate. API and Telegram share one title and event.
- Market notices due within the same second go out as one message; per-chat pacing
  and delayed retries.
  Timeouts are marked unknown, not silently reported as successful.
- Read-only API on the VPS (`/api/health`, `/api/ready`, `/api/events`) for
  monitoring and inspection; there is no web frontend. fomobtc.com redirects to the
  Telegram group from the same nginx.
- An off-server Cloudflare Worker checks `/api/health` every 5 minutes and alerts the
  operator privately in Telegram (scripts/deploy/watchdog).

## Quick start

```bash
python3.12 -m venv venv
venv/bin/pip install --require-hashes -r requirements.lock
cp .env.example .env
# Configure Telegram and source credentials, or explicitly use log-only mode:
TELEGRAM_ENABLED=false venv/bin/python run.py
```

Initial announcement history is archived without notification. Missing source
credentials are visible as blocked. Public Hyperliquid preview is degraded and
cannot satisfy realtime acceptance. Configuration lives in .env and must never
be committed. API defaults to http://127.0.0.1:8080/api/health.

## Validation

```bash
python -m ruff check .
python -m mypy src
TELEGRAM_ENABLED=false python -m pytest
python -m compileall -q src run.py
python scripts/check_repository.py
```

CI runs Python checks on 3.11/3.12 plus repository checks.

## Handoff and delivery

Read [AGENTS.md](AGENTS.md), [current handoff](docs/handoff.md),
[backlog](docs/backlog.md), [data contract](docs/data-contract.md),
[UI rules](docs/ui-rules.md), [deployment and rollback](docs/deployment.md),
and [release evidence](docs/releases/README.md).
Production runtime and real notification acceptance must be verified separately
from local tests.
