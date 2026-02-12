#!/bin/bash
cd /home/deploy/apps/QweSignalHub/workers/crypto_monitor

echo "Starting qsh-crypto-monitor..."
pm2 start ecosystem.config.js

sleep 2

echo "Service started."
pm2 status qsh-crypto-monitor
echo "View logs: pm2 logs qsh-crypto-monitor"
