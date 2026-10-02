# 2026-09-14 monitoring 2.1 deployment

部署状态：deployed
源码提交：135894380f2a745e63655c1648762f9196c0cab6
运行版本：后台2.1.0 / systemd；最终前端2.1.0 / 36665253345b9dab8d9c3dadcef8092bdaff0dbc / Worker c7d1c78e-205c-46e6-8824-fdee547a7ce1。
验收结果：41项Python测试、Ruff/Mypy/compileall、仓库契约、前端语法/突发刷新检查通过；迁移副本完整性与51条旧事件保留通过；真实线上摘要、采集计数、网页实时连接、移动宽度检查通过。Telegram未启用，未声称真实推送完成。
回退信息：先停服务并备份当前DB，保留新增历史；将新增price_notice的pending行标记failed再切回 /opt/fomobtc/releases/fe829b4b96002351c8237255bd96b02714d4d124 和对应SOURCE_COMMIT。不可覆盖已发送/送达未知回执；初始备份 /var/backups/fomobtc/pre-2.1-1789382407.sqlite3 仅为迁移前恢复材料。前端原版本641abf82-4aec-49c7-98ed-9ed7c73350b4。
授权记录：用户要求先落实建议的监控优化、随后评估仅现货；沿用本任务已确认的合并部署授权，保持现货+合约启用且未启用Telegram。

## Tests and migration

- New tests cover summary updates during cooldown, immutable notification content,
  successful higher-tier cooldown suppressing lower-tier repeats, reversal and
  escalation, 60-second enqueue guard, restart/unknown delivery guard, disabled
  delivery creating no cooldown, live/history ordering and buffered peak/hit counts.
- Frontend test injects 10,000 refresh messages twice; one pending refresh timer
  per batch, no per-message health requests. Feed fetches capped at 2/second;
  health remains 15-second polling, separate from backend detection/push speed.
- SQLite online backup mode0600, migration tested on a second copy; integrity_check
  ok and all51 original events retained. Production migration only adds tables.
- Stopped old daemon before changing release symlink; one systemd process restarted.
  New service NRestarts=0, MemoryCurrent51,421,184 bytes at observation; no warning
  journal entries in the checked five-minute interval.

## Real signals, not injected production test data

- LSKUSDT futures: 10,430 qualifying messages merged into one summary, peak+5.87%,
  latest qualifying change+4.79%, observed span26s. CVC futures483 hits and CVC spot7
  hits also merged. The three summaries retained counts and peak values.
- One snapshot: 10,920 threshold hits total, 19 committed summary decisions,
  zero buffered summaries remaining and no notification rows because Telegram is off.
- Browser displayed realtime connection, per-market receipt times/rates, valid
  calculations, threshold hits, notification decisions and live summary data.
- Mobile viewport390px: document scrollWidth390, monitor width354; no horizontal
  overflow. Viewport reset after test.
- API/backend source SHA and public frontend config verified separately.
- Frontend first 2.1 Worker561b45a4-8291-4e48-92f1-b06c01528593 was superseded by the
  final c7d1c78e version after bounding refresh requests and labeling price as the
  most recent qualifying trade price, not a continuously updated quote.

## Scope still open

Telegram/Binance announcement credentials and end-to-end device receipts remain
Issue#4. No 24h performance guarantee. Strict rolling180s, incremental subscription
updates, volume-group hysteresis and spike confirmation remain future work.
See [spot-only assessment](../spot-only-assessment.md); both market collectors stay on.
