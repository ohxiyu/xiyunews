# 当前交接

## Current execution pointer
当前目标：Issue #17 正文与简讯已上线，40条已有公告全部补全，完成 PR #18 交付。
前次目标：Issue #15 公告来源冲突已修复并上线，PR #16 完成交付。
上一轮目标：Issue #13 shadcn/ui 极紧凑数据展示已上线，完成 PR #14 交付；后续按用户反馈调整。
任务 Issue / 负责人：[Issue #13](https://github.com/ohxiyu/fomobtc/issues/13) / ohxiyu；此前 [Issue #11](https://github.com/ohxiyu/fomobtc/issues/11) / ohxiyu；此前 [Issue #9](https://github.com/ohxiyu/fomobtc/issues/9)，[Issue #4](https://github.com/ohxiyu/fomobtc/issues/4) / Codex 实施，ohxiyu 认领。
工作分支 / 最后提交 / PR：feat/announcement-briefs / 3ebdddd / [PR #18](https://github.com/ohxiyu/fomobtc/pull/18)，最终合并状态以 GitHub 为准。
已经完成：OKX官方详情正文抓取、已有正文提取简讯、持久化附加表、40条旧公告补全及前端两行简讯/展开正文。旧通知状态不变。
尚未完成：Telegram/Binance 公告凭据配置、真实推送回执与手机验收；Hyperliquid 当前为公共预览降级模式；24h 稳定性与峰值测试。Issue #4 保持开放。
已运行的验证及结果：43项测试、Ruff/Mypy、前端构建与回归、CI通过；线上OKX20条及Hyperliquid20条均ready且有简讯；正文展开已验收。
尚未验证的内容：生产自动续期首次执行、24 小时稳定性、端到端 P95/P99、Binance 公告鉴权、Hyperliquid 客户端授权、Telegram API 回执及手机收件；不把本机判断延迟当作推送延迟。
线上版本 / 对应源码提交：前后端3ebdddd08f13f8093824b15d4ec480028e1bf398 / https://fomobtc.com / Worker ed98cd61-a2d5-4e25-80bf-e666be70fa08。
阻塞与所需权限：SSH、合并部署、域名切换和停放记录删除均已授权并执行；仍缺 Telegram Bot/Chat、Binance 公告密钥及可选 Hyperliquid 会话的位置。配置放 /etc/fomobtc.env（root 0600），密钥不进聊天或仓库。
下一步具体动作：完成 PR #18 合并；Issue #4 仍需Binance公告凭据和实际Telegram验收。简讯当前为原文摘录，无翻译或AI改写。

## 五项状态
- 代码完成：2.1监控优化完成。
- 测试通过：本地和远端 CI 已通过；本次公网与浏览器检查通过，记录见发布文档。
- PR 合并：#3/#5/#6/#7 已合并；本轮 #10 的最终合并状态以 GitHub 为准。
- 部署成功：东京后台、正式域名前端与 HTTPS API 已部署。
- 线上验收通过：页面、采集、API/SSE 通过；来源鉴权与 Telegram 推送未完成，readiness 503 保持真实状态。

历史证据：[首次前端](releases/deploy-20260914-frontend.md)、[东京后台](releases/deploy-20260914-tokyo.md)、[正式域名与 HTTPS](releases/deploy-20260914-domain.md)。

本轮证据：[2.1部署](releases/deploy-20260914-monitoring.md)、[仅现货评估](spot-only-assessment.md)。

本轮证据：[shadcn 紧凑展示](releases/shadcn-compact.md)。

正文简讯证据：[发布记录](releases/announcement-content.md)。
