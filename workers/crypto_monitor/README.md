# QweCryptoMonitor

Binance 3-minute price-change alert worker.

## What It Does

- Pulls Binance spot and USD-M futures ticker/klines data with REST APIs.
- Groups USDT pairs by 24h quote volume.
- Sends Telegram alerts when 3-minute price movement crosses the configured threshold.
- Persists cooldown state in Redis when Redis is available.

## Current Thresholds

```text
spot_high: 2.5%
spot_mid: 6%
spot_low: 10%
futures_high: 4%
futures_mid: 10%
futures_low: 20%
```

Configuration lives in `config/thresholds.yaml`.

## Runtime

Managed by the root `QweSignalHub/ecosystem.config.js` as `qsh-crypto-monitor`.

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
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
LOG_LEVEL=INFO
```
