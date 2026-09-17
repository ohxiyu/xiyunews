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
