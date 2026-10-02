# 发布与验证记录

[2.0.0 说明](2.0.0.md) · [平台验证](fomobtc-platform.md) · [1.0.0 基线](1.0.0.md) · [交接机制验证](agent-handoff.md) · [发布模板](template.md)

历史记录保留原始时间与证据，不改写成当前状态。仓库版本说明使用 `<VERSION>.md`，首行必须是 `# <VERSION>`。文档或 CI 修改不必增加应用版本。
每次应用 PR 增加或更新一份验证记录；实际部署另建 `deploy-YYYYMMDD-描述.md`，按模板填写，状态必须为 deployed 或 rolled-back，字段不能填 unknown/待填。计划与未知事项留在交接中。
后端记录 systemd/PM2 进程与 checkout SHA；前端记录 Cloudflare Worker 版本。前后端分别验收。进程在线不是业务验收。

- [2026-09-14 前端部署证据](deploy-20260914-frontend.md)

- [2026-09-14 东京后台部署与域名进度](deploy-20260914-tokyo.md)

- [2026-09-14 正式域名与 HTTPS 验收](deploy-20260914-domain.md)

- [2.1.0 监控优化](2.1.0.md) · [上线与真实摘要验证](deploy-20260914-monitoring.md)

- [突发与趋势预警重做（Issue #33）](burst-trend-alerts.md)

- [2026-09-17策略部署](deploy-burst-trend-20260917.md)

- [行情覆盖修复与 Telegram 大盘合并](universe-digest.md)

- [2026-09-24 覆盖修复部署](deploy-20260924-universe-digest.md)

- [2026-09-24 无成交 K 线补丁部署](deploy-20260924-trend-empty-bars.md)

- [币安公告只读 Key 配置](binance-announcement-setup.md)

- [币安官方公告流推送与去重](binance-stream-delivery.md)

- [2.2.0 多交易所公告与分类](2.2.0.md)

- [2026-09-24 2.2.0 部署](deploy-20260924-exchanges.md)

- [2.3.0 双语摘要与要点](2.3.0.md)

- [2.4.0 行情图片推送](2.4.0.md)

- [2.5.0 资金流向与 Telegram 话题](2.5.0.md)

- [2026-09-25 2.3.0–2.5.0 部署与群组话题](deploy-20260925-flows-topics.md) · [网页前端下线](remove-web-frontend.md)

- [2.5.1 精简为采集 + Telegram 推送](2.5.1.md)

- [fomobtc.com 跳转群组与成员只读](domain-redirect.md)

- [单机运行与看门狗](single-host-watchdog.md)

- [2.6.0 行情异动单一规则](2.6.0.md) · [部署与线上验收](deploy-20260925-simple-moves.md)
