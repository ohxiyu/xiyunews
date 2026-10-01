# FomoBTC platform validation

Issue: [#4](https://github.com/ohxiyu/fomobtc/issues/4).
Source: feature PR head; base main 00c5c6c (handoff PR #3 merged).

## Local evidence, 2026-09-14
- Existing 15 application tests retained; new tests cover baseline/revision dedup,
  persistent pending reservation, confirmed cooldown, cancellation-safe SQLite,
  delayed retry isolation, parsing/escaping, invalid prices, stale/gapped trade
  suppression, read-only API and private chat redaction.
- First live smoke: 328 spot and 643 futures pairs discovered, OKX announcements
  and 20 Hyperliquid public preview messages persisted without notifications.
- Found a real compatibility issue: current futures trades require /market/ws;
  old /ws accepted the subscription but delivered no trades. Corrected after
  checking current official schema and probing the /market/ws endpoint.
- Dashboard opened against real local API; no fixture data presented as live.
- Final local checks: 34 pytest passed, Ruff and Mypy passed (17 modules),
  compileall and repository contract passed; frontend syntax/build/dry-run passed.
- Follow-up smoke snapshot saved in [JSON](smoke-20260914.json). All 8 market
  shards received trades; notifications disabled. This is not a capacity or
  end-to-end latency benchmark.
- Readiness now rejects stale market data, degraded gaps and blocked credentials;
  retired shards are excluded. Delivery worker failures propagate to supervision.
- CI and actual frontend deployment are recorded separately after merge.

## Not yet verified
VPS deployment and production SHA, actual Telegram delivery/phone receipt,
authenticated Binance announcement subscription, Hyperliquid client session,
24-hour stability, high-volatility peak traffic and server-specific latency.

No production deployment is claimed by these local checks.
