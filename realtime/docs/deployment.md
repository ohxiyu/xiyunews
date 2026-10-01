# FomoBTC deployment and rollback

## Combined private repository packaging

The maintained source is ohxiyu/xiyunews, under realtime/. Run development checks
inside realtime/, but package from the combined repository root after fetching
origin/main and verifying the reviewed merge SHA. Retain this module's independent
requirements.lock and pyproject. Never install the daily application's dependencies
or package its src into the realtime release.

```bash
git fetch origin
SOURCE_SHA=$(git rev-parse origin/main)
git merge-base --is-ancestor "$SOURCE_SHA" origin/main
git archive "$SOURCE_SHA" realtime | tar -x --strip-components=1 -C /opt/fomobtc/releases/"$SOURCE_SHA"
```

The target directory must first be created on the existing server; when packaging
on the operator's computer, transport the archive over the existing SSH connection.
Alternatively use bash realtime/scripts/deploy/package_release.sh "$SOURCE_SHA"
for the validated tar stream. SOURCE_COMMIT is this full combined-repository SHA;
/api/health must match it, not the pre-import fomobtc commit. Do not change the
systemd unit, /etc/fomobtc.env path, database path or nginx redirect. The complete
operator-only switch/backup/rollback checklist is below. It is prepared, not executed;
do not run the packaging example without its preparation steps.

## 现有东京服务迁移清单（阶段 4）

仅在阶段 3 使用 merge commit 合并、确认旧历史凭据已撤销后执行。以下迁移不重装 systemd、nginx、证书或看门狗，不改阈值、地址簿、群组、数据库位置与密钥；没有 SSH 配置或既有主机指纹时停止，不使用 StrictHostKeyChecking=no。所有标为“服务器”的命令在同一次 SSH 会话中执行，保留变量；命令不是本轮已执行的部署证据。

### 1. 运营者电脑：核对实际合并 SHA 与原连接

```bash
set -euo pipefail
XIYU_SSH_CONFIG='/填写已有SSH配置的绝对路径'
SOURCE_SHA='填写阶段3实际合并的40位SHA'
test -f "$XIYU_SSH_CONFIG"
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]
git fetch origin
git merge-base --is-ancestor "$SOURCE_SHA" origin/main
git merge-base --is-ancestor 7807126d8c7cdb51e18f0b91ba27f500271f9f08 "$SOURCE_SHA"
git cat-file -e "$SOURCE_SHA:realtime/requirements.lock"
ssh -F "$XIYU_SSH_CONFIG" -o StrictHostKeyChecking=yes fomobtc-tokyo \
  'systemctl is-active fomobtc; readlink -f /opt/fomobtc/current'
```

记录当前 release 路径和健康接口的 source_commit。SOURCE_SHA 必须来自实际合并的阶段 3 PR；当前仅网站迁移的 main 没有 realtime，不能拿它冒充服务器新版本。

### 2. 运营者电脑：传送独立模块

目标目录已存在时停止，避免覆盖旧 release；失败留下的新空目录也不自动删除。SSH 保持既有账号、主机别名和已知指纹。

```bash
ssh -F "$XIYU_SSH_CONFIG" -o StrictHostKeyChecking=yes fomobtc-tokyo \
  "test ! -e /opt/fomobtc/releases/$SOURCE_SHA && \
   sudo install -d -o fomobtc -g fomobtc /opt/fomobtc/releases/$SOURCE_SHA"
git archive "$SOURCE_SHA" realtime | \
  ssh -F "$XIYU_SSH_CONFIG" -o StrictHostKeyChecking=yes fomobtc-tokyo \
    "sudo -u fomobtc tar -x --strip-components=1 -C /opt/fomobtc/releases/$SOURCE_SHA"
ssh -t -F "$XIYU_SSH_CONFIG" -o StrictHostKeyChecking=yes fomobtc-tokyo
```

### 3. 服务器：安装新 release，停机后备份

下面重新填写同一个 SHA；不从旧仓 tag 或短 SHA 推断。先安装独立 venv，再停服务缩短停机时间，安装失败时旧服务不受影响。

```bash
set -euo pipefail
SOURCE_SHA='填写同一40位合并SHA'
[[ "$SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]]
XIYU_RELEASE="/opt/fomobtc/releases/$SOURCE_SHA"
XIYU_BACKUP="/opt/fomobtc/backups/xiyunews-$SOURCE_SHA"
XIYU_PREVIOUS=$(readlink -f /opt/fomobtc/current)
test -L /opt/fomobtc/current
test -x "$XIYU_PREVIOUS/venv/bin/python"
test -f "$XIYU_RELEASE/requirements.lock"
test ! -e "$XIYU_BACKUP"
python3 -c 'import sys; assert sys.version_info[:2] in {(3, 11), (3, 12)}'
sudo -u fomobtc python3 -m venv "$XIYU_RELEASE/venv"
sudo -u fomobtc "$XIYU_RELEASE/venv/bin/pip" install \
  --require-hashes -r "$XIYU_RELEASE/requirements.lock"
sudo install -d -m 0700 "$XIYU_BACKUP"
sudo cp -p /etc/fomobtc.env "$XIYU_BACKUP/runtime.env"
sudo systemctl stop fomobtc
if systemctl is-active --quiet fomobtc; then exit 1; fi
sudo "$XIYU_PREVIOUS/venv/bin/python" - "$XIYU_BACKUP" <<'PY'
import os
import sqlite3
import sys
from pathlib import Path
target = Path(sys.argv[1]) / 'fomobtc.sqlite3'
with sqlite3.connect('file:/var/lib/fomobtc/fomobtc.sqlite3?mode=ro', uri=True) as source:
    with sqlite3.connect(target) as backup:
        source.backup(backup)
        assert backup.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
os.chmod(target, 0o600)
print('SQLite backup verified')
PY
printf 'Previous release: %s\n' "$XIYU_PREVIOUS"
```

环境备份仅在服务器 root-only 目录，不下载、不提交、不展示内容。备份或停机检查失败时不切换；不要盲目执行后续代码块。记录原路径、原 source_commit 和备份路径，保留旧 release。

### 4. 服务器：只更新版本标识并原子切换

用 sudoedit 仅把 SOURCE_COMMIT 改为上面的完整 SHA，保留其余行，尤其 Token、群/话题、数据库和信源设置。不要整份覆盖环境文件，也不安装导入包中的 systemd/nginx 文件。

```bash
sudoedit /etc/fomobtc.env
sudo chmod 0600 /etc/fomobtc.env
test ! -e /opt/fomobtc/current.xiyunews-next
test ! -L /opt/fomobtc/current.xiyunews-next
sudo ln -s "$XIYU_RELEASE" /opt/fomobtc/current.xiyunews-next
sudo mv -T /opt/fomobtc/current.xiyunews-next /opt/fomobtc/current
XIYU_STARTED_AT=$(date +%s)
sudo systemctl start fomobtc
systemctl is-active fomobtc
systemctl show fomobtc --property=MainPID --value
```

只由既有 systemd 启动一个进程，不再运行 run.py 或第二份发布目录。若启动失败，停止验收并报告，不反复重发通知、清队列或自动回滚。

### 5. 运营者电脑与服务器：健康、自然回执、看门狗

现货连接需要至少 180 秒自然预热，期间 warming 不算完成；不要靠改状态或阈值绕过。运营者电脑检查完整 SHA 和三分片：

```bash
curl --max-time 20 -fsS https://api.fomobtc.com/api/health | \
  jq -e --arg expected "$SOURCE_SHA" \
  '.source_commit == $expected and \
   .sources.spot_stream_0.state == "live" and \
   .sources.spot_stream_1.state == "live" and \
   .sources.spot_stream_2.state == "live"'
curl --max-time 20 -sS -o /dev/null -w 'Readiness HTTP: %{http_code}\n' \
  https://api.fomobtc.com/api/ready
```

额外比较采集进度、队列和所有来源与迁移前基线。既有 Hyperliquid degraded 会导致 ready 503，必须如实记录：满足迁移的 SHA/现货要求不等于全来源 ready，也不因这次改名改变信源或监控规则。

服务器等待下一条自然消息，不发送测试新闻。行情通知的 price_notice 在公共列表中隐藏，因此从 SQLite 只读提取发送后回执，不误把 event 创建时间或 notification_sent 当作 message_id：

```bash
sudo -u fomobtc /opt/fomobtc/current/venv/bin/python - "$XIYU_STARTED_AT" <<'PY'
import json
import sqlite3
import sys
with sqlite3.connect('file:/var/lib/fomobtc/fomobtc.sqlite3?mode=ro', uri=True) as db:
    db.row_factory = sqlite3.Row
    rows = db.execute(
        "SELECT id,kind,source,sent,telegram_id FROM events "
        "WHERE status='sent' AND sent>=? AND telegram_id IS NOT NULL "
        "ORDER BY sent DESC LIMIT 5", (int(sys.argv[1]),),
    ).fetchall()
print(json.dumps([dict(row) for row in rows]))
PY
```

空列表表示还没有自然回执，不能标记交付验收通过；用户手机收件与 API 回执分别记录。既有看门狗至少观察两轮五分钟检查，确认没有新增异常告警，不清空 KV、不重新部署、不更换凭据。全部证据齐备后再由运营者把原 ohxiyu/fomobtc 归档为只读，不删除仓库。

### 6. 仅在确认回滚后：恢复原 release

回滚需要运营者授权；本清单只提供方法，不自动执行。保留当前数据库与已写回执，不把备份数据库覆盖回来，否则可能丢失新发送记录、导致重复。先核对 XIYU_PREVIOUS 是第 3 步记录的确切旧 release，且该目录仍有自身 venv。

```bash
test -x "$XIYU_PREVIOUS/venv/bin/python"
sudo systemctl stop fomobtc
sudoedit /etc/fomobtc.env
# 仅把 SOURCE_COMMIT 恢复为记录的旧完整 SHA，保留其他配置。
test ! -e /opt/fomobtc/current.xiyunews-rollback
test ! -L /opt/fomobtc/current.xiyunews-rollback
sudo ln -s "$XIYU_PREVIOUS" /opt/fomobtc/current.xiyunews-rollback
sudo mv -T /opt/fomobtc/current.xiyunews-rollback /opt/fomobtc/current
sudo systemctl start fomobtc
systemctl is-active fomobtc
```

重新核对旧 SHA、单进程、三个分片、自然消息与看门狗，不删除失败 release 或备份。把真实执行时间、源码 SHA、回执和基线降级写入本模块发布记录；没有执行时只记“操作清单已准备”。

## Backend: one Linux host, one sender

The generic fresh-install notes below are historical bootstrap guidance, not the
existing-host migration procedure above. Do not recreate users, proxy config,
services, chat targets or deliberate test alerts for this repository-only migration.

Requires Python 3.11/3.12, HTTPS access to Binance/OKX/Telegram, and a persistent
local disk. A 2 vCPU / 2 GB host is a validation starting point, not a measured
capacity guarantee. Keep API bound to 127.0.0.1 and expose it through a TLS proxy.
CORS is not authentication; these endpoints contain intentionally public market
and announcement data only. Restrict access at the proxy if the dashboard is private.

1. Record old source SHA, process manager, environment location and service state.
   Back up existing state. Do not copy secrets into git, logs or PRs.
2. Check out the reviewed main SHA under /opt/fomobtc/releases/<SHA>. Create venv
   and install `venv/bin/pip install --require-hashes -r requirements.lock`.
   Each release has its own venv (never link another release's venv).
3. Create user/group fomobtc and /var/lib/fomobtc owned by it. Put production env
   in /etc/fomobtc.env (root-owned 0600, read by systemd), using .env.example.
   Set FOMOBTC_DB=/var/lib/fomobtc/fomobtc.sqlite3, SOURCE_COMMIT=<full SHA>,
   Secrets remain server-side.
4. Stop the running service and back up SQLite with the backup API before switching.
5. Atomically point /opt/fomobtc/current to the release, install
   scripts/deploy/fomobtc.service, run systemctl daemon-reload and start fomobtc.
   Only one instance may run; the SQLite lock refuses a second process.
6. Configure the TLS proxy using scripts/deploy/nginx.conf with the actual API
   hostname. Only /api/* (read-only health and events) is routed; limit request
   rate at the proxy. Cap journal disk use on the host.
7. Verify /api/health source_commit matches the checked-out SHA. /api/ready must
   return 200 for full acceptance; blocked/degraded sources return 503.
8. Confirm a deliberate test alert in the destination chat, record message ID and
   operator receipt, then enable regular notifications. Do not confuse API 200
   with an actual device notification. API has no unauthenticated send endpoint.

## Announcement settings

Binance uses its official English WebSocket with HMAC credentials. There is no
replay endpoint in this adapter; downtime may lose announcements and must be
recorded. Never log signed URLs. See official docs linked in data-contract.md.
OKX polls first page at >=5 seconds, 6 by default; backlogs beyond the returned
page are not guaranteed. Use the correct regional domain.
Hyperliquid defaults to a public t.me preview every 15 seconds: limited history,
media-only content incomplete, no realtime guarantee.

## Rollback

Record the previous current symlink and source SHA before changing them. Stop
fomobtc, retain SQLite and env, restore the prior release and restart its manager.
Do not start two services. Re-check source SHA, process count, health and duplicate alerts.
Add an actual deploy-* evidence record only after a real deployment.

## Tokyo production host and domain

The production layout is the DNS-only backend `https://api.fomobtc.com` on the
Tokyo VPS; the web frontend at `fomobtc.com` was retired on 2026-09-25. Domain configuration
and acceptance state are recorded separately in the latest handoff.

- Keep `/etc/fomobtc.env` root-owned mode 0600; bind the app to loopback only.
- The 2 GB plan exposes about 1.6 GiB to Ubuntu. Install
  `scripts/deploy/resources.conf` as a systemd drop-in to cap the daemon at 1 GiB.
- Bootstrap nginx on port 80 with only `/.well-known/acme-challenge/` served from
  `/var/www/fomobtc-acme`. Point the API A record at the VPS; wait for public DNS.
- Certbot is isolated in `/opt/fomobtc-certbot`. Issue with `certbot certonly
  --webroot -w /var/www/fomobtc-acme -d api.fomobtc.com`; only then install the TLS
  nginx configuration. Check `nginx -t` before every reload.
- Install the certificate service/timer from scripts/deploy and enable
  `fomobtc-certbot.timer`. Verify a staging renewal with `certbot renew --dry-run`.
- nginx limits each IP to 5 requests/second with a burst of 20, five concurrent
  requests, and 80 total upstream requests.
- Keep Telegram disabled until credentials are configured and delivery is
  deliberately validated. Readiness 503 is expected while required sources are
  blocked; do not relabel it healthy to complete deployment.

2.4.0 起依赖含 Pillow：每个 release 在自身目录创建 venv 并 `pip install --require-hashes -r requirements.lock`，不再链接旧 release 的 venv；回退时旧 release 仍使用其原有 venv。

## Single host, DNS and watchdog

Everything that serves traffic runs on the Tokyo VPS. Cloudflare only hosts the DNS
zone (all records DNS-only, grey cloud) and the off-server watchdog.

- DNS: `fomobtc.com`, `www.fomobtc.com` and `api.fomobtc.com` are A records to
  47.79.36.171. Edit them in the Cloudflare dashboard (the wrangler login cannot).
- `fomobtc.com` / `www` serve no page: nginx (see nginx.conf) returns a 302 to the
  Telegram group invite link on every path. If the link is replaced, edit both
  `return 302` lines and reload nginx. Its certificate (`--cert-name fomobtc.com`)
  renews with the same certbot timer as the API certificate.
- Watchdog: `scripts/deploy/watchdog` is a Cloudflare Worker (`fomobtc-watchdog`,
  cron every 5 minutes, KV `STATE`) that reads `https://api.fomobtc.com/api/health`
  and privately messages the operator after two consecutive failing checks
  (no response, Telegram disabled, spot trades older than 5 minutes, a source in
  error/stale/blocked, or more than 30 queued notices), reminds every 2 hours and
  announces recovery. Deploy with `npx wrangler deploy` in that directory; secrets
  `TELEGRAM_BOT_TOKEN` and `ALERT_CHAT_ID` are set by `scripts/setup_watchdog.sh`.
