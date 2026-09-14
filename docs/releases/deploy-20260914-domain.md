# 2026-09-14 fomobtc.com deployment

部署状态：deployed
源码提交：5f652bf9b1e32c2bc0bd4603fefec17864acb1b7
运行版本：前端 2.0.0 / Cloudflare Worker 641abf82-4aec-49c7-98ed-9ed7c73350b4；后台 2.0.0 / fe829b4b96002351c8237255bd96b02714d4d124。
验收结果：fomobtc.com 与 api.fomobtc.com HTTPS 可用；前端 config.js 版本与 API_ORIGIN 正确；真实事件、筛选、服务状态及 SSE 刷新/心跳通过；模拟证书续期成功。Telegram 与 Binance 公告凭据缺失，完整业务 readiness 503，未宣称推送验收。
回退信息：前端上个 Worker f1ae7fad-3b5e-449e-ada4-054fb57c2b62 不带 API 配置，恢复时需单独核对域名路由；保留 api DNS/证书、SQLite 和 env。后端首次部署回退为停止服务并保留状态；不要恢复停放解析作为应用回退。
授权记录：用户明确要求继续部署、合并及使用 fomobtc.com；本轮确认填写 Cloudflare 名称服务器并删除 3 条停放解析。

## DNS and TLS

- Dynadot nameservers saved: ignat.ns.cloudflare.com / shaz.ns.cloudflare.com.
  Cloudflare zone a628deb274b1d3d6b7aced7573a7cf9f became active on Free plan.
- API A record: api.fomobtc.com -> 47.79.36.171, DNS-only. Root domain routes to
  the static Worker through its custom-domain configuration.
- Removed the three imported parking A records after explicit confirmation.
  No changes to fomobtc.co or other domains.
- Let's Encrypt certificate for api.fomobtc.com issued, expires 2026-12-13.
  Stored under /etc/letsencrypt/live/api.fomobtc.com; private key not in repository.
- nginx configuration passed syntax check and was reloaded with the real cert.
  HTTP redirects to HTTPS (308); POST /api/events rejected (403).
- fomobtc-certbot.timer enabled. certbot renew --dry-run passed. A scheduled
  production renewal has not occurred yet; simulated renewal is not its proof.
- Backend FRONTEND_ORIGIN is exactly https://fomobtc.com. CORS response verified.
- Old workers.dev route is disabled by custom-domain deployment default. The
  canonical frontend link is https://fomobtc.com.

## Public acceptance

- Local computer and Tokyo VPS fetched the same config.js over verified HTTPS:
  apiOrigin=https://api.fomobtc.com, revision=5f652bf9b1e32c2bc0bd4603fefec17864acb1b7.
- Frontend HTTP 200; CSP, nosniff, referrer policy and frame denial present.
- API health/events HTTP 200; exact CORS origin and no-store present.
- SSE returned event: refresh and the 15-second heartbeat. Test intentionally
  ended at 18 seconds; curl timeout was the bounded stream test ending.
- In-app browser on fomobtc.com displayed 实时连接, 45 real stored events,
  11/13 source components, and real price-change events. Market-only filtering
  removed announcements. Service page correctly displayed Binance blocked,
  Hyperliquid degraded, Telegram disabled, and separate backend/frontend SHAs.
- Counts and timings are observations, not fixed expectations. No mobile-device
  push receipt, 24-hour stability or end-to-end P95/P99 is claimed.

## Remaining business acceptance

Telegram Bot/Chat and Binance announcement credentials are still required.
Hyperliquid uses public preview fallback. Issue #4 stays open for authenticated
sources, deliberate Telegram delivery and longer-running validation.
