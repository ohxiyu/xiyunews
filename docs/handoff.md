# 当前交接

## Current execution pointer
当前目标：Issue #19 最新公告优先与官方中文已上线；等待翻译服务及Telegram安全配置位置完成剩余工作。
前次目标：Issue #17 正文与简讯已上线，40条已有公告全部补全，完成 PR #18 交付。
前次目标：Issue #15 公告来源冲突已修复并上线，PR #16 完成交付。
上一轮目标：Issue #13 shadcn/ui 极紧凑数据展示已上线，完成 PR #14 交付；后续按用户反馈调整。
任务 Issue / 负责人：[Issue #13](https://github.com/ohxiyu/fomobtc/issues/13) / ohxiyu；此前 [Issue #11](https://github.com/ohxiyu/fomobtc/issues/11) / ohxiyu；此前 [Issue #9](https://github.com/ohxiyu/fomobtc/issues/9)，[Issue #4](https://github.com/ohxiyu/fomobtc/issues/4) / Codex 实施，ohxiyu 认领。
工作分支 / 最后提交 / PR：feat/latest-chinese / 413f19d / [PR #20](https://github.com/ohxiyu/fomobtc/pull/20)，最终状态见GitHub。
已经完成：停止历史回填，新公告唤醒优先，OKX官方中文正文/标题/简讯，中文ready门槛，实时页只展示近24小时非基线公告。
尚未完成：无中文源的自动翻译（用户已选择，尚未提供服务和配置位置）；Telegram配置和真实发送；Binance凭据。#19/#4继续跟踪。
已运行的验证及结果：43项测试、Ruff/Mypy、前端构建与回归、CI通过；线上OKX20条及Hyperliquid20条均ready且有简讯；正文展开已验收。
尚未验证的内容：生产自动续期首次执行、24 小时稳定性、端到端 P95/P99、Binance 公告鉴权、Hyperliquid 客户端授权、Telegram API 回执及手机收件；不把本机判断延迟当作推送延迟。
线上版本 / 对应源码提交：前后端413f19d55a3647ecce1a115f5c09bdfc619b53f2；Worker41cdfaf3-56cb-4730-b14b-903f99253b90，https://fomobtc.com 。
阻塞与所需权限：SSH、合并部署、域名切换和停放记录删除均已授权并执行；仍缺 Telegram Bot/Chat、Binance 公告密钥及可选 Hyperliquid 会话的位置。配置放 /etc/fomobtc.env（root 0600），密钥不进聊天或仓库。
下一步具体动作：取得翻译服务名称/API地址/安全配置路径及Telegram配置位置，再实现翻译接入并验收真实中文推送。用户已授权优先官方中文、缺失自动翻译，尚无服务信息。

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

本轮证据：[最新中文公告](releases/latest-chinese.md)。
