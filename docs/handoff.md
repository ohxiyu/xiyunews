# 当前交接

## Current execution pointer
当前目标：Issue #11 实时数据库表已上线，完成 PR #12 交付；后续 UI 调整等待用户指定。
任务 Issue / 负责人：[Issue #11](https://github.com/ohxiyu/fomobtc/issues/11) / ohxiyu；此前 [Issue #9](https://github.com/ohxiyu/fomobtc/issues/9)，[Issue #4](https://github.com/ohxiyu/fomobtc/issues/4) / Codex 实施，ohxiyu 认领。
工作分支 / 最后提交 / PR：feat/live-data-table / f7c1721 / [PR #12](https://github.com/ohxiyu/fomobtc/pull/12)；最终合并状态以 GitHub 为准。
已经完成：#9/#10 监控优化已合并；本轮紧凑数据表、公开数据库记录展开、自动更新暂停/恢复、展开状态保持和手机容器滚动已上线。采集与通知策略保持。
尚未完成：Telegram/Binance 公告凭据配置、真实推送回执与手机验收；Hyperliquid 当前为公共预览降级模式；24h 稳定性与峰值测试。Issue #4 保持开放。
已运行的验证及结果：前端语法、10000 消息突发限频、暂停恢复、仓库检查通过；真实生产表格展示、活动时间更新、390px 页面无外溢验证通过。最终 CI 见 PR #12。
尚未验证的内容：生产自动续期首次执行、24 小时稳定性、端到端 P95/P99、Binance 公告鉴权、Hyperliquid 客户端授权、Telegram API 回执及手机收件；不把本机判断延迟当作推送延迟。
线上版本 / 对应源码提交：后台 2.1.0 / 135894380f2a745e63655c1648762f9196c0cab6；前端 https://fomobtc.com / f7c1721 / Worker 67048b93-3b60-4f80-8018-42daba9fe31d。
阻塞与所需权限：SSH、合并部署、域名切换和停放记录删除均已授权并执行；仍缺 Telegram Bot/Chat、Binance 公告密钥及可选 Hyperliquid 会话的位置。配置放 /etc/fomobtc.env（root 0600），密钥不进聊天或仓库。
下一步具体动作：核对 PR #12 合并；按用户后续意见调整 UI。Issue #4 继续处理安全凭据配置及真实推送验收。现货/合约仍同时启用。

## 五项状态
- 代码完成：2.1监控优化完成。
- 测试通过：本地和远端 CI 已通过；本次公网与浏览器检查通过，记录见发布文档。
- PR 合并：#3/#5/#6/#7 已合并；本轮 #10 的最终合并状态以 GitHub 为准。
- 部署成功：东京后台、正式域名前端与 HTTPS API 已部署。
- 线上验收通过：页面、采集、API/SSE 通过；来源鉴权与 Telegram 推送未完成，readiness 503 保持真实状态。

历史证据：[首次前端](releases/deploy-20260914-frontend.md)、[东京后台](releases/deploy-20260914-tokyo.md)、[正式域名与 HTTPS](releases/deploy-20260914-domain.md)。

本轮证据：[2.1部署](releases/deploy-20260914-monitoring.md)、[仅现货评估](spot-only-assessment.md)。
