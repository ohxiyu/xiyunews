# 2026-09-14 Tokyo backend deployment

部署状态：deployed
源码提交：fe829b4b96002351c8237255bd96b02714d4d124
运行版本：FomoBTC 2.0.0 / systemd fomobtc.service；前端仍为 Worker f1ae7fad-3b5e-449e-ada4-054fb57c2b62（源码 206c616aa56971f9331f8b1c84f7d52b6deec4ef）。
验收结果：服务器本地健康 API 200、8 个行情分片 live、OKX polling、Hyperliquid degraded、Binance 公告 blocked；Telegram 禁用；公网域名、TLS、推送与端到端延迟未验收。
回退信息：本机首次后台部署，无旧 CoinSignal 实例；停止 fomobtc.service，保留 /var/lib/fomobtc 与 /etc/fomobtc.env。前端保持原 Worker 版本，未切换 API_ORIGIN；DNS 迁移尚未提交至 Dynadot。
授权记录：用户明确授权 SSH 公钥配置、服务部署、上线、仓库合并与改名；后续指定 fomobtc.com，继续沿用免费边界。

## Verified server facts

- Aliyun Tokyo, Ubuntu 24.04 x86_64, Python 3.12.3; 2 vCPU / 2 GB plan,
  about 1613 MiB visible RAM, about 35 GB free disk before deployment.
- Dedicated SSH key installed for admin after explicit confirmation; host key
  verified independently through the Aliyun command agent. Private keys remain
  outside the repository. No password login changes were made.
- `/opt/fomobtc/current` points to `/opt/fomobtc/releases/fe829b4b96002351c8237255bd96b02714d4d124`.
  Dependencies installed in its venv using the hash-locked requirements.
- App runs as fomobtc, SQLite under `/var/lib/fomobtc`; root-owned env mode 0600.
  API listens on loopback only. Boot startup enabled; NRestarts=0 at observation.
- At uptime 443 seconds: 372,013 market messages, 329 spot / 646 futures pairs,
  eight live WebSocket shards with zero reported gaps, ingestion queue 0,
  two archived events and 40 announcement baseline entries.
- MemoryCurrent 51,765,248 bytes at that observation. Decision P99 0.2013 ms
  over the latest 5,000 samples measures local decision processing only, not
  source publication, network, Telegram delivery or device notification latency.
- Server REST probes: spot 200 (~95 ms), futures 200 (~94 ms), OKX 200 (~151 ms),
  Telegram root 302 (~699 ms). These are single samples, not latency guarantees.
- Aliyun firewall already allows TCP 22/80/443; no firewall expansion performed.
- nginx and Certbot 5.8 installed. Port 80 serves only the ACME challenge path for
  api.fomobtc.com; no public API proxy is active yet. The TLS nginx template passed
  `nginx -t` using a temporary local test certificate; no test certificate was
  deployed. Renewal systemd units passed `systemd-analyze verify`.

## Domain and unfinished work

- fomobtc.com is registered at Dynadot and was using Dynadot Parking.
- Added fomobtc.com to Cloudflare Free; assigned nameservers
  ignat.ns.cloudflare.com and shaz.ns.cloudflare.com.
- Added DNS-only A api -> 47.79.36.171 in the pending Cloudflare zone.
- Scan imported three parking A records (@, www, *) -> 185.53.179.128.
  Removal is awaiting the user confirmation requested by the browser operation
  policy. No parking records have been deleted.
- Dynadot nameservers have NOT been changed. The browser control tool cannot
  target the DNS menu reliably; user was asked to open the DNS settings form.
- After DNS activation: obtain a real certificate, install nginx TLS config,
  enable and test renewal, bind frontend custom domain, build API_ORIGIN,
  set exact CORS origin, deploy and verify public API/SSE/browser behavior.
- Telegram and Binance announcement credentials have not been supplied.
  Hyperliquid is using public preview fallback. Readiness remains 503.
- No real Telegram receipt or phone notification, 24-hour stability, full
  announcement coverage, or end-to-end P95/P99 was observed.
