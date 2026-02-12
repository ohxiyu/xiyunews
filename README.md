# QweSignalHub

Unified project for three Telegram data-push services:

- `qsh-openmolt`: Moltbook daily digest
- `qsh-crypto-monitor`: Binance 3-minute change alerts
- `qsh-truth-machine`: Prediction market daily reports + API

## Project Layout

```text
QweSignalHub/
  ecosystem.config.js         # One PM2 config for all services
  scripts/
    reload_pm2.sh             # Reload all services
    health_check.sh           # Quick runtime health check
  workers/
    openmolt/
    crypto_monitor/
    truth_machine/
```

## Runtime Notes

- Services are still isolated workers, but now managed from one project root.
- PM2 names are unified with `qsh-*` prefix.
- Each worker keeps its own config/data inside its worker directory.

## PM2 Commands

```bash
cd /home/deploy/apps/QweSignalHub
./scripts/reload_pm2.sh
./scripts/health_check.sh
```

## Notes

The old standalone directories are deprecated. Use `QweSignalHub` as the single runtime source of truth.
