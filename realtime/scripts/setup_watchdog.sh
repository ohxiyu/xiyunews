#!/usr/bin/env bash
# Give the Cloudflare watchdog its Telegram credentials straight from the server config.
# Run on your computer (needs the fomobtc-tokyo SSH config and a wrangler login):
#   bash scripts/setup_watchdog.sh
# Values go from the server into Cloudflare secrets through pipes and are never printed.
set -euo pipefail
cd "$(dirname "$0")/deploy/watchdog"
SSH=(ssh -F "$HOME/.ssh/fomobtc_tokyo_config" fomobtc-tokyo)

TOKEN=$("${SSH[@]}" 'sudo sed -n "s/^TELEGRAM_BOT_TOKEN=//p" /etc/fomobtc.env | tail -1')
[[ $TOKEN =~ ^[0-9]+:[A-Za-z0-9_-]{30,}$ ]] || { echo "服务器上没有有效的机器人 Token"; exit 1; }
# Pushes now go to the group; the operator's private chat id is the positive chat id in
# the configuration backed up before the switch to topics.
CHAT=$("${SSH[@]}" 'sudo sh -c "grep -h \"^TELEGRAM_CHAT_ID=[0-9]\" /etc/fomobtc.env.bak-* 2>/dev/null | tail -1 | cut -d= -f2"')
[[ $CHAT =~ ^[0-9]+$ ]] || { echo "找不到你的私聊 ID"; exit 1; }

printf %s "$TOKEN" | npx -y wrangler@4 secret put TELEGRAM_BOT_TOKEN >/dev/null
printf %s "$CHAT" | npx -y wrangler@4 secret put ALERT_CHAT_ID >/dev/null
printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$TOKEN" |
  curl -sS --max-time 15 -K - --data-urlencode "chat_id=$CHAT" \
    --data-urlencode "text=🧪 FomoBTC 看门狗已连接：服务异常时会在这里提醒你" -o /dev/null
echo "✓ 看门狗已获得 Telegram 凭据，并已给你私聊发了一条测试消息"
