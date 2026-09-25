# FomoBTC deployment and rollback

## Backend: one Linux host, one sender

Requires Python 3.11/3.12, HTTPS access to Binance/OKX/Telegram, and a persistent
local disk. A 2 vCPU / 2 GB host is a validation starting point, not a measured
capacity guarantee. Keep API bound to 127.0.0.1 and expose it through a TLS proxy.
CORS is not authentication; these endpoints contain intentionally public market
and announcement data only. Restrict access at the proxy if the dashboard is private.

1. Record old source SHA, process manager, environment location and service state.
   Back up existing state. Do not copy secrets into git, logs or PRs.
2. Check out the reviewed main SHA under /opt/fomobtc/releases/<SHA>. Create venv
   and install `venv/bin/pip install --require-hashes -r requirements.lock`.
   Client mode additionally needs `venv/bin/pip install -r requirements-telegram.txt`.
3. Create user/group fomobtc and /var/lib/fomobtc owned by it. Put production env
   in /etc/fomobtc.env (root-owned 0600, read by systemd), using .env.example.
   Set FOMOBTC_DB=/var/lib/fomobtc/fomobtc.sqlite3, SOURCE_COMMIT=<full SHA>,
   FRONTEND_ORIGIN may stay empty (no web frontend). Secrets remain server-side.
4. Stop the old CoinSignal service before migration. If its Redis has active
   cooldowns, run `venv/bin/python -m scripts.import_cooldowns --database
   /var/lib/fomobtc/fomobtc.sqlite3` from the release with Redis variables present.
   This reads legacy coinsignal:alert_cooldowns and leaves old state unchanged.
   Restore fomobtc ownership after importing. If old Redis is unavailable, record
   cooldown discontinuity and allow a deliberate warm-up period before notifications.
5. Atomically point /opt/fomobtc/current to the release, install
   scripts/deploy/fomobtc.service, run systemctl daemon-reload and start fomobtc.
   Enable boot startup only after verifying the service. Never run PM2 and systemd
   against the same instance. The SQLite lock catches duplicate new processes,
   but cannot stop an unmodified old CoinSignal process; explicitly stop it.
6. Configure the TLS proxy using scripts/deploy/nginx.conf (production) or
   scripts/deploy/Caddyfile (alternative) with the actual API hostname. Only /api/* is routed. Limit request rate and concurrent streams at
   the proxy; application SSE limit is 100. Cap journal disk use on the host.
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
media-only content incomplete, no realtime guarantee. Client mode requires an
already authorized Telegram session file in /var/lib/fomobtc and API ID/hash.
Do not log in interactively from the daemon. Session and DB must be writable by
fomobtc and excluded from git. No credential means no authenticated acceptance.

## Rollback

Record the previous current symlink and source SHA before changing them. Stop
fomobtc, retain SQLite and env, restore the prior release and restart its manager.
If reverting to legacy CoinSignal, account for cooldowns created after migration:
legacy Redis was preserved but does not include newly sent FomoBTC alerts. Do not
start both services. Re-check source SHA, process count, health and duplicate alerts.
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
  requests, and 80 total upstream requests/streams. Buffering is disabled for SSE.
- Keep Telegram disabled until credentials are configured and delivery is
  deliberately validated. Readiness 503 is expected while required sources are
  blocked; do not relabel it healthy to complete deployment.

2.4.0 起依赖含 Pillow：每个 release 在自身目录创建 venv 并 `pip install --require-hashes -r requirements.lock`，不再链接旧 release 的 venv；回退时旧 release 仍使用其原有 venv。
