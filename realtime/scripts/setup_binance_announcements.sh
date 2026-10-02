#!/usr/bin/env bash
# One-command Binance announcement stream setup on the production host.
# Usage (from your computer):
#   ssh -t -F ~/.ssh/fomobtc_tokyo_config fomobtc-tokyo \
#     'sudo bash /opt/fomobtc/current/scripts/setup_binance_announcements.sh'
# Key and secret are read with hidden input and never appear in argv, logs or output.
# The key must be read-only: the script refuses keys that can trade or withdraw.
set -euo pipefail

ENV_FILE=/etc/fomobtc.env
[[ $EUID -eq 0 ]] || { echo "请用 sudo 运行"; exit 1; }
[[ -f $ENV_FILE ]] || { echo "找不到 $ENV_FILE"; exit 1; }

read -rsp "粘贴 API Key（输入不显示），回车：" KEY; echo
read -rsp "粘贴 Secret Key（输入不显示），回车：" SECRET; echo
[[ $KEY =~ ^[A-Za-z0-9]{32,128}$ && $SECRET =~ ^[A-Za-z0-9]{32,128}$ ]] || { echo "Key 格式不对"; exit 1; }

# Signed read-only request; key goes in a curl config on stdin, not the command line.
QUERY="timestamp=$(date +%s%3N)&recvWindow=10000"
SIG=$(SECRET="$SECRET" QUERY="$QUERY" python3 -c 'import hmac,hashlib,os;print(hmac.new(os.environ["SECRET"].encode(),os.environ["QUERY"].encode(),hashlib.sha256).hexdigest())')
RESULT=$(printf 'url = "https://api.binance.com/sapi/v1/account/apiRestrictions?%s&signature=%s"\nheader = "X-MBX-APIKEY: %s"\n' "$QUERY" "$SIG" "$KEY" |
  curl -sS --max-time 15 -K - | python3 -c '
import json, sys
d = json.load(sys.stdin)
if "enableReading" not in d:
    print("ERROR " + str(d.get("msg", "unknown error"))[:120]); sys.exit()
risky = [k for k in ("enableWithdrawals", "enableSpotAndMarginTrading", "enableFutures",
                     "enableMargin", "enableInternalTransfer", "permitsUniversalTransfer",
                     "enableVanillaOptions", "enablePortfolioMarginTrading") if d.get(k)]
if not d.get("enableReading"):
    print("ERROR 未开启读取权限")
elif risky:
    print("RISKY " + ", ".join(risky))
else:
    print("OK ipRestrict=" + str(d.get("ipRestrict")))
')
case $RESULT in
  OK*) echo "✓ Key 有效且只读（$RESULT）" ;;
  RISKY*) echo "✗ 这个 Key 开了交易/提现类权限：${RESULT#RISKY }。请到币安 API 管理里只保留「启用读取」后重试。"; exit 1 ;;
  *) echo "✗ Key 校验失败：${RESULT#ERROR }"; exit 1 ;;
esac

BACKUP=$ENV_FILE.bak-$(date -u +%Y%m%dT%H%M%SZ)
install -m 600 -o root -g root "$ENV_FILE" "$BACKUP"
KEY="$KEY" SECRET="$SECRET" python3 - "$ENV_FILE" <<'PY'
import os, sys
path = sys.argv[1]
values = {
    "BINANCE_ANNOUNCEMENT_API_KEY": os.environ["KEY"],
    "BINANCE_ANNOUNCEMENT_API_SECRET": os.environ["SECRET"],
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
echo "服务已重启，等待公告推送流连接…"
for _ in $(seq 1 20); do
  sleep 2
  STATE=$(curl -s --max-time 5 http://127.0.0.1:8080/api/health |
    python3 -c 'import json,sys;s=json.load(sys.stdin)["sources"].get("binance_announcements",{});print(s.get("state",""),"|",s.get("detail",""))' 2>/dev/null || true)
  if [[ $STATE == live* ]]; then
    echo "✓ 币安公告实时推送流已连接：$STATE"
    echo "配置备份：$BACKUP"
    exit 0
  fi
done
echo "✗ 40 秒内未连上（当前：${STATE:-无响应}），正在恢复原配置"
install -m 600 "$BACKUP" "$ENV_FILE"; systemctl restart fomobtc
exit 1
