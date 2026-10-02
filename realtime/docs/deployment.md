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

完整逐条命令仅维护在 [服务器迁移清单](../../project-docs/realtime-server-migration.md)，包括原 SSH/主机指纹、完整 SHA、独立打包、备份、原子切换、健康与自然回执、看门狗及经授权回退。该清单已经准备并通过语法检查，但本次未执行服务器迁移；必须先完成阶段 3 历史安全确认和实际合并，再使用真实合并 SHA。

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
