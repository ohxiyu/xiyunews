# FomoBTC

Low-latency Binance price-change alerts and official announcements from Binance,
OKX and Hyperliquid, delivered through Telegram with a read-only dashboard.
Formerly CoinSignal; the repository is now https://github.com/ohxiyu/fomobtc.

Dashboard: [fomobtc.com](https://fomobtc.com). Current deployment and remaining
credential requirements: [handoff](docs/handoff.md).

## Runtime

- Python 3.11/3.12, asyncio/aiohttp; one VPS process managed by systemd.
- Binance spot aggregate trades: rolling 60s/180s burst alerts with 3s confirmation.
  Closed 15m candles: 6h/24h trend alerts and previous-day high/low breakouts.
  Volume tiers, confirmation and cooldown settings live in
  [config/thresholds.yaml](config/thresholds.yaml); exact rules in the
  [data contract](docs/data-contract.md).
- Binance signed English announcement stream, OKX REST polling, Hyperliquid
  public channel preview fallback or an optional authorized Telegram client.
- SQLite WAL stores immutable events, a persistent outbox and direction-specific
  gates: burst 15 minutes plus re-cross, trend 6 hours plus one breakout escalation.
  Web and Telegram share one title and event; no Redis required.
- Up to one second merges simultaneous signals; per-chat pacing and delayed retries.
  Timeouts are marked unknown, not silently reported as successful.
- Static frontend: live feed, searchable history and source health; optional
  Cloudflare hosting. Read-only API and SSE run on the VPS.

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

Frontend, from web/: `npm ci`, `npm run check`, `npm run build`.
CI runs Python checks on 3.11/3.12 plus frontend and repository checks.

## Handoff and delivery

Read [AGENTS.md](AGENTS.md), [current handoff](docs/handoff.md),
[backlog](docs/backlog.md), [data contract](docs/data-contract.md),
[UI rules](docs/ui-rules.md), [deployment and rollback](docs/deployment.md),
and [release evidence](docs/releases/README.md).
Production runtime and real notification acceptance must be verified separately
from local tests and frontend publication.
