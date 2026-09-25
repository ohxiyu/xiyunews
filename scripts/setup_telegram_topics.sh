#!/usr/bin/env bash
# Move FomoBTC pushes into one Telegram forum group with a topic per product.
# Usage (from your computer):
#   ssh -t -F ~/.ssh/fomobtc_tokyo_config fomobtc-tokyo \
#     'sudo bash /opt/fomobtc/current/scripts/setup_telegram_topics.sh'
# Uses the bot token already in /etc/fomobtc.env; it is never printed or put in argv.
set -euo pipefail

ENV_FILE=/etc/fomobtc.env
[[ $EUID -eq 0 ]] || { echo "请用 sudo 运行"; exit 1; }
TOKEN=$(grep -E '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | tail -1 | cut -d= -f2-)
[[ -n $TOKEN ]] || { echo "未找到 TELEGRAM_BOT_TOKEN，请先运行 setup_telegram.sh"; exit 1; }

api() {
  local method=$1
  shift
  printf 'url = "https://api.telegram.org/bot%s/%s"\n' "$TOKEN" "$method" |
    curl -sS --max-time 15 -K - "$@"
}
field() { python3 -c "import json,sys;d=json.load(sys.stdin);print($1)"; }

BOT_ID=$(api getMe | field 'd["result"]["id"] if d.get("ok") else ""')
BOT=$(api getMe | field 'd["result"]["username"] if d.get("ok") else ""')
[[ -n $BOT_ID ]] || { echo "机器人 Token 无效"; exit 1; }

cat <<EOF
请先在 Telegram 里完成：
  1. 新建一个群组（例如“FomoBTC”）
  2. 群组设置 → 打开“话题（Topics）”
  3. 把 @$BOT 加进群，设为管理员，并勾选“管理话题”
  4. 在群里发送：/start@$BOT
EOF
read -rp "完成后回车继续…" _

GROUP=$(api getUpdates | python3 -c '
import json, sys
found = {}
for update in json.load(sys.stdin).get("result", []):
    for key in ("message", "my_chat_member", "chat_member"):
        chat = (update.get(key) or {}).get("chat") or {}
        if chat.get("type") == "supergroup":
            found[chat["id"]] = chat.get("title", "")
for chat_id, title in found.items():
    print(chat_id, title)
' | tail -1)
[[ -n $GROUP ]] || { echo "没有找到群组。确认机器人已在群里，并在群里发送了 /start@$BOT 后重试。"; exit 1; }
CHAT_ID=${GROUP%% *}
echo "✓ 找到群组：${GROUP#* }（$CHAT_ID）"
read -rp "是这个群吗？[y/N] " ok; [[ $ok == [yY] ]] || exit 1

FORUM=$(api getChat --data-urlencode "chat_id=$CHAT_ID" | field 'd.get("result", {}).get("is_forum", False)')
[[ $FORUM == True ]] || { echo "✗ 这个群还没有开启“话题（Topics）”，请在群设置里打开后重试"; exit 1; }
RIGHTS=$(api getChatMember --data-urlencode "chat_id=$CHAT_ID" --data-urlencode "user_id=$BOT_ID" |
  field 'd["result"]["status"] + " " + str(d["result"].get("can_manage_topics", False))')
[[ $RIGHTS == "administrator True" ]] || { echo "✗ 机器人需要是管理员并有“管理话题”权限（当前：$RIGHTS）"; exit 1; }
echo "✓ 群组已开启话题，机器人有管理权限"

declare -A NAMES=([market]="📈 行情异动" [announcement]="📢 交易所公告" [flow]="💰 资金流向")
declare -A TOPICS=()
for kind in market announcement flow; do
  TOPICS[$kind]=$(api createForumTopic --data-urlencode "chat_id=$CHAT_ID" \
    --data-urlencode "name=${NAMES[$kind]}" | field 'd["result"]["message_thread_id"] if d.get("ok") else ""')
  [[ -n ${TOPICS[$kind]} ]] || { echo "✗ 创建话题“${NAMES[$kind]}”失败"; exit 1; }
  api sendMessage --data-urlencode "chat_id=$CHAT_ID" \
    --data-urlencode "message_thread_id=${TOPICS[$kind]}" \
    --data-urlencode "text=FomoBTC：${NAMES[$kind]}推送将发在这里 ✅" >/dev/null
  echo "✓ 已创建话题 ${NAMES[$kind]}（ID ${TOPICS[$kind]}），并发送测试消息"
done
read -rp "三个话题都收到测试消息了吗？收到则切换推送并重启服务 [y/N] " ok
[[ $ok == [yY] ]] || exit 1

BACKUP=$ENV_FILE.bak-$(date -u +%Y%m%dT%H%M%SZ)
install -m 600 -o root -g root "$ENV_FILE" "$BACKUP"
CHAT_ID="$CHAT_ID" MARKET="${TOPICS[market]}" ANNOUNCEMENT="${TOPICS[announcement]}" \
  FLOW="${TOPICS[flow]}" python3 - "$ENV_FILE" <<'PY'
import os, sys
path = sys.argv[1]
values = {
    "TELEGRAM_CHAT_ID": os.environ["CHAT_ID"],
    # Announcements now share the group; a separate announcement chat would bypass topics.
    "TELEGRAM_ANNOUNCEMENT_CHAT_ID": "",
    "TELEGRAM_TOPIC_MARKET": os.environ["MARKET"],
    "TELEGRAM_TOPIC_ANNOUNCEMENT": os.environ["ANNOUNCEMENT"],
    "TELEGRAM_TOPIC_FLOW": os.environ["FLOW"],
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
  echo "✓ 已切换：之后的推送进入群组的三个话题，私聊不再收到。配置备份：$BACKUP"
else
  echo "✗ 服务启动失败，正在恢复原配置"; install -m 600 "$BACKUP" "$ENV_FILE"; systemctl restart fomobtc
  exit 1
fi
