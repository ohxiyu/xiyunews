# 2026-11-06 网页发布检查点时限

[Issue322](https://github.com/ohxiyu/xiyunews/issues/322)，当前会话为唯一编辑/生产整合负责人，复用work/xiyunews-edition-continuity，agent/publication-checkpoint-budget分支。前置[PR320](https://github.com/ohxiyu/xiyunews/pull/320)已合并；[历史恢复记录](2026-11-05-edition-continuity.md)的最终证据另由Issue321归档。

## 已确认的问题与修复

Deploy Docs42074503443连续两次在精确检查点ACK时达到20分钟总时限。第一次job127410971001于2026-11-05T17:26:30Z启动、17:46:56Z结束；第二次job127423543248于17:47:46Z启动、18:08:16Z结束。两次Deploy to GitHub Pages均已成功，取消步骤均为Confirm exact published state checkpoint。第一次17:40:11Z已导入3日14条并补齐五份入口，ai_calls=0/channel_calls=0；出版快照c23e9014ee7ea3bde869e5066aa82e0628dce65b完整保留原稿和新刊期日志，第二次失败没有丢掉它。

现有流程需要应用代码checkout、当前出版checkout和publisher内部clone，当前下载耗时挤占了最后检查点预算。仅将Deploy Docs总时限20改为30分钟，与既有edge-build和统一Cloudflare发布的上限一致，仍然有界。保留全部步骤、检查点校验、成功门控、正常分支推送和原并发策略；不修改服务器CPU/内存限制、Secrets、费用、来源、Cron或渠道，也不重新调用历史AI或手写生产分支。不把现时下载超时倒推为11月3日首次发布的底层错误。

## 五阶段

- 代码：完成，仅工作流时限及交接记录。
- 测试：既有预算测试对应期望值同步为30；完整本地Python回归、治理与差异检查通过，完整远端CI待完成，不跳过任何检查。
- 合并：待同步main、检查通过后正常合并。
- 部署：待新main自动触发正常Deploy Docs并完整确认检查点，已有统一Cloudflare42078138315继续执行，不取消它。
- 生产验收：待检查点成功、已恢复刊期幂等、最新日报/消息回执不变与普通正式页面验证。

Source commit: 基线88da72c5465a223160a51c805a7d3ce7ec4fbae8；本修复合并待记录。

Application PR: [PR323](https://github.com/ohxiyu/xiyunews/pull/323)。

Worker version: 待现有统一Cloudflare42078138315完成回读；本改动不更改Worker代码或绑定。

Deployment: 仅通过正常Actions；不手动执行生产ACK、不改生成分支。

Verification: 当前仅确认两次20分钟任务均在ACK取消，不能宣称已经完成正常发布闭环。

Rollback: 不自动回滚或恢复整库；原稿日志和Git历史保留，后续合并与部署按现有授权流程。
