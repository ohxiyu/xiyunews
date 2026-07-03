# QwePolymarket

Polymarket breaking market reporter.

## What It Does

- Fetches `https://polymarket.com/zh/breaking` data via `/api/biggest-movers`.
- Builds a Chinese Telegram report for the largest 24h price movers.
- Saves generated reports to SQLite.
- Serves latest/history/report lookup through FastAPI.

## Runtime

Managed by the root `QweSignalHub/ecosystem.config.js` as `qsh-polymarket`.

```bash
cd /home/deploy/apps/QweSignalHub
./scripts/reload_pm2.sh
./scripts/health_check.sh
```

## Environment

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_channel_or_chat_id
TELEGRAM_ADMIN_ID=your_admin_chat_id
API_PORT=8081
REPORTS_DB_PATH=/home/deploy/apps/QweSignalHub/workers/polymarket/db/reports.db
```

## API

```text
GET /health
GET /healthz
GET /v1/reports/latest?platform=polymarket&refresh=false&limit=8
GET /v1/reports/history?platform=polymarket&days=7
GET /v1/reports/{report_id}
```
