# 当前交接

## Current execution pointer
当前目标：Issue #9 第一轮监控优化已实现并上线，完成最终合并；随后继续 Issue #4 来源鉴权/推送验收。现货单独运行评估已完成，暂保留两市场。
任务 Issue / 负责人：[Issue #9](https://github.com/ohxiyu/fomobtc/issues/9)，[Issue #4](https://github.com/ohxiyu/fomobtc/issues/4) / Codex 实施，ohxiyu 认领。
工作分支 / 最后提交 / PR：feat/market-episodes / [PR #10](https://github.com/ohxiyu/fomobtc/pull/10)；后台源码135894380f2a745e63655c1648762f9196c0cab6，前端源码36665253345b9dab8d9c3dadcef8092bdaff0dbc；最终证据提交见PR head。
已经完成：2.1持续异动摘要、通知快照与冷却分离、反转/升级和60秒入队限制、分市场采集指标及网页心跳、前端突发刷新限频已上线；独立现货/合约开关已实现。真实LSK 10430次命中合并一条摘要，旧51条事件保留。
尚未完成：Telegram/Binance 公告凭据配置、真实推送回执与手机验收；Hyperliquid 当前为公共预览降级模式；24h 稳定性与峰值测试。Issue #4 保持开放。
已运行的验证及结果：41项Python测试、Ruff/Mypy/compileall、仓库契约、前端语法及10000消息突发刷新检查通过；PR #10初次四项CI通过；数据库备份副本迁移完整性通过；公网API/页面版本、真实摘要、采集计数、实时连接和390px无横向溢出检查通过。
尚未验证的内容：生产自动续期首次执行、24 小时稳定性、端到端 P95/P99、Binance 公告鉴权、Hyperliquid 客户端授权、Telegram API 回执及手机收件；不把本机判断延迟当作推送延迟。
线上版本 / 对应源码提交：后台 https://api.fomobtc.com / 2.1.0 / 135894380f2a745e63655c1648762f9196c0cab6；前端 https://fomobtc.com / 2.1.0 / 36665253345b9dab8d9c3dadcef8092bdaff0dbc / Worker c7d1c78e-205c-46e6-8824-fdee547a7ce1。SPOT_ENABLED/FUTURES_ENABLED均默认true。
阻塞与所需权限：SSH、合并部署、域名切换和停放记录删除均已授权并执行；仍缺 Telegram Bot/Chat、Binance 公告密钥及可选 Hyperliquid 会话的位置。配置放 /etc/fomobtc.env（root 0600），密钥不进聊天或仓库。
下一步具体动作：完成本轮PR #10合并后关闭#9；按spot-only-assessment.md取舍，用户尚未要求关闭合约；继续获取安全凭据位置并按deployment.md做真实通知验收。后续滚动180秒、增量订阅、分组缓冲和尖峰确认需独立验证，不混入本轮。

## 五项状态
- 代码完成：2.1监控优化完成。
- 测试通过：本地和远端 CI 已通过；本次公网与浏览器检查通过，记录见发布文档。
- PR 合并：#3/#5/#6/#7 已合并；本轮 #10 的最终合并状态以 GitHub 为准。
- 部署成功：东京后台、正式域名前端与 HTTPS API 已部署。
- 线上验收通过：页面、采集、API/SSE 通过；来源鉴权与 Telegram 推送未完成，readiness 503 保持真实状态。

历史证据：[首次前端](releases/deploy-20260914-frontend.md)、[东京后台](releases/deploy-20260914-tokyo.md)、[正式域名与 HTTPS](releases/deploy-20260914-domain.md)。

本轮证据：[2.1部署](releases/deploy-20260914-monitoring.md)、[仅现货评估](spot-only-assessment.md)。
