#!/usr/bin/env bash
# One-command Telegram private-chat setup on the production host.
# Usage (from your computer):
#   ssh -t -F ~/.ssh/fomobtc_tokyo_config fomobtc-tokyo \
#     'sudo bash /opt/fomobtc/current/scripts/setup_telegram.sh'
# The token is read with hidden input and never appears in argv, logs or output.
set -euo pipefail

ENV_FILE=/etc/fomobtc.env
DB=/var/lib/fomobtc/fomobtc.sqlite3
[[ $EUID -eq 0 ]] || { echo "请用 sudo 运行"; exit 1; }
[[ -f $ENV_FILE ]] || { echo "找不到 $ENV_FILE"; exit 1; }

# Token goes to curl through a config on stdin, not the command line.
api() {
  printf 'url = "https://api.telegram.org/bot%s/%s"\n' "$TOKEN" "$1" |
    curl -sS --max-time 15 -K - "${@:2}"
}

read -rsp "粘贴 Bot Token（输入不显示），回车：" TOKEN; echo
[[ $TOKEN =~ ^[0-9]+:[A-Za-z0-9_-]{30,}$ ]] || { echo "Token 格式不对"; exit 1; }

BOT=$(api getMe | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["result"]["username"] if d.get("ok") else "")')
[[ -n $BOT ]] || { echo "Token 无效（getMe 失败）"; exit 1; }
echo "✓ 机器人 @$BOT"

echo
echo "现在在手机 Telegram 打开 https://t.me/$BOT ，点“开始”或发送 /start"
read -rp "发完后回车继续…" _

CHAT=$(api getUpdates | python3 -c '
import json, sys
d = json.load(sys.stdin)
chats = [u["message"]["chat"] for u in d.get("result", []) if "message" in u]
private = [c for c in chats if c.get("type") == "private"]
if private:
    c = private[-1]
    print(c["id"], c.get("first_name", ""), c.get("username", ""))
')
[[ -n $CHAT ]] || { echo "没有收到私聊消息。确认给 @$BOT 发了 /start 后重新运行。"; exit 1; }
CHAT_ID=${CHAT%% *}
echo "✓ 找到私聊：$CHAT"
read -rp "是你本人吗？[y/N] " ok; [[ $ok == [yY] ]] || exit 1

PENDING=$(python3 -c "
import sqlite3
db = sqlite3.connect('file:$DB?mode=ro', uri=True)
print(db.execute(\"SELECT count(*) FROM events WHERE status IN ('pending','sending')\").fetchone()[0])")
echo "待发送队列：$PENDING 条（行情 120 秒、公告 1 小时自动过期，不补发历史）"

TEXT="FomoBTC 测试消息：Telegram 配置成功 ✅"
RESULT=$(api sendMessage --data-urlencode "chat_id=$CHAT_ID" --data-urlencode "text=$TEXT" |
  python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["result"]["message_id"] if d.get("ok") else "FAIL")')
[[ $RESULT != FAIL ]] || { echo "测试消息发送失败"; exit 1; }
echo "✓ 测试消息已发送（message_id=$RESULT）"
read -rp "手机收到了吗？收到则启用推送并重启服务 [y/N] " ok; [[ $ok == [yY] ]] || exit 1

BACKUP=$ENV_FILE.bak-$(date -u +%Y%m%dT%H%M%SZ)
install -m 600 -o root -g root "$ENV_FILE" "$BACKUP"
TOKEN="$TOKEN" CHAT_ID="$CHAT_ID" python3 - "$ENV_FILE" <<'PY'
import os, sys
path = sys.argv[1]
values = {
    "TELEGRAM_BOT_TOKEN": os.environ["TOKEN"],
    "TELEGRAM_CHAT_ID": os.environ["CHAT_ID"],
    "TELEGRAM_ENABLED": "true",
}
lines, seen = [], set()
for line in open(path).read().splitlines():
    key = line.split("=", 1)[0].strip()
    if key in values:
        line = f"{key}={values[key]}"
        seen.add(key)
    lines.append(line)
lines += [f"{k}={v}" for k, v in values.items() if k not in seen]
tmp = path + ".tmp"
with open(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600), "w") as f:
    f.write("\n".join(lines) + "\n")
os.replace(tmp, path)
PY
chown root:root "$ENV_FILE"; chmod 600 "$ENV_FILE"

systemctl restart fomobtc
sleep 5
if systemctl is-active --quiet fomobtc; then
  echo "✓ 服务已重启，Telegram 推送已启用。配置备份：$BACKUP"
else
  echo "✗ 服务启动失败，正在恢复原配置"; install -m 600 "$BACKUP" "$ENV_FILE"; systemctl restart fomobtc
  journalctl -u fomobtc -n 20 --no-pager | grep -v -i token; exit 1
fi
