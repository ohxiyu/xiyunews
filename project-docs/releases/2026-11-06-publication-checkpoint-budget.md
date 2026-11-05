# 2026-11-06 网页发布检查点时限

[Issue322](https://github.com/ohxiyu/xiyunews/issues/322)，当前会话为唯一编辑/生产整合负责人，复用work/xiyunews-edition-continuity，agent/publication-checkpoint-budget分支。前置[PR320](https://github.com/ohxiyu/xiyunews/pull/320)已合并；[历史恢复记录](2026-11-05-edition-continuity.md)的最终证据另由Issue321归档。

## 已确认的问题与修复

Deploy Docs42074503443连续两次在精确检查点ACK时达到20分钟总时限。第一次job127410971001于2026-11-05T17:26:30Z启动、17:46:56Z结束；第二次job127423543248于17:47:46Z启动、18:08:16Z结束。两次Deploy to GitHub Pages均已成功，取消步骤均为Confirm exact published state checkpoint。第一次17:40:11Z已导入3日14条并补齐五份入口，ai_calls=0/channel_calls=0；出版快照c23e9014ee7ea3bde869e5066aa82e0628dce65b完整保留原稿和新刊期日志，第二次失败没有丢掉它。

现有流程需要应用代码checkout、当前出版checkout和publisher内部clone，当前下载耗时挤占了最后检查点预算。仅将Deploy Docs总时限20改为30分钟，与既有edge-build和统一Cloudflare发布的上限一致，仍然有界。保留全部步骤、检查点校验、成功门控、正常分支推送和原并发策略；不修改服务器CPU/内存限制、Secrets、费用、来源、Cron或渠道，也不重新调用历史AI或手写生产分支。不把现时下载超时倒推为11月3日首次发布的底层错误。

## 五阶段

- 代码：完成，仅工作流时限及交接记录。
- 测试：既有预算测试对应期望值同步为30；完整本地Python回归、治理与差异检查通过，最终head163b90eef77ec1be2af0abbd7676af24fa9a80f1的[CI42082248062](https://github.com/ohxiyu/xiyunews/actions/runs/42082248062)全部必需检查通过，包括Python、web、edge-build及realtime双Python；没有跳过任何检查。
- 合并：[PR323](https://github.com/ohxiyu/xiyunews/pull/323)于2026-11-05T18:58:35Z正常合并dca841fd0e112cbec3917f382682acb41fb800bf，已确认合并树与检查head相同且为origin/main祖先。
- 部署：新main自动[Deploy Docs42089412376](https://github.com/ohxiyu/xiyunews/actions/runs/42089412376)已成功，精确检查点已确认；后续自动统一Cloudflare42093318854也成功。此前统一Cloudflare42078138315已正常上线恢复内容，没有取消正常任务。
- 生产验收：正常发布检查点、实际重复恢复幂等、最新日报及消息回执不变，以及自动统一发布后的最终普通URL/四组浏览器验收均通过，五阶段完成。

Source commit: dca841fd0e112cbec3917f382682acb41fb800bf；基线88da72c5465a223160a51c805a7d3ce7ec4fbae8。

Application PR: [PR323](https://github.com/ohxiyu/xiyunews/pull/323)。

Worker version: 最终05b8d129-2253-4759-b4ef-441bc6bc9708；首次恢复54193230-bff2-4ab9-bfb9-c049a64aa83a。本改动不更改Worker代码或绑定。

Deployment: 仅通过正常Actions；不手动执行生产ACK、不改生成分支。

Verification: 新30分钟正常任务已完整执行到精确ACK成功，自动统一发布后的最终普通URL、四组浏览器、持久日志和回执保护复核也通过，详见下文。

## 正常发布闭环

42089412376的job127463202701于2026-11-05T18:58:41Z开始、19:22:46Z成功结束，共24分05秒，超过旧20分钟上限且在新30分钟预算内。19:11:21Z补缺步骤返回repaired=[]、imported=[]、ai_calls=0、channel_calls=0，确认已有3日14条直接复用。19:22:36Z精确ACK回读确认events，出版提交82929893a36f9e1a4dfde5c9b6df2f8048df3cb9；没有手工确认数据库或将本地相等视作已发布。

之后只读核对主库/备份完整性均ok，刊期日志3日14条/5日13条校验和正确；daily、event_urls、events及X/Square均clean且与已确认源摘要相同。daily/X/Square三份JSON与恢复前备份逐字节一致。staging保持既有primary缓存的dirty标记：load_staging_state使用primary=True，正常staging持久化独立于本次网页ACK；没有为制造全clean结果清理缓存或回执。

## 最终自动统一发布

[Cloudflare42093318854](https://github.com/ohxiyu/xiyunews/actions/runs/42093318854)于2026-11-05T19:22:52Z开始、19:42:50Z成功结束，完全由前述正常publisher成功触发。普通/health回读source dca841fd0e112cbec3917f382682acb41fb800bf、artifact 82929893a36f9e1a4dfde5c9b6df2f8048df3cb9、Worker05b8d129-2253-4759-b4ef-441bc6bc9708、build key956185e6393c9632747c22cd3912daf9b3f2d818caeadc8119b493bc7781d669；dispatcher_enabled与realtime_watchdog_enabled均true，/ready状态ready。

新版本再次完整验证2026-10-23至11-05共14期普通JSON/中英文片段和条数；3日14条、12个事件引用及HTML节点，中英×1440/390日期切换/加载更早仍为14条，无横向溢出或脚本错误。最新5日仍13条，items紧凑JSON摘要5e77c2ddb424adb444b6e8f660f26798822d234dfe4d6271b795f293b61ec080不变。出版82929893与前一df4161dd中的latest.json、3日整组JSON/片段和刊期日志逐字节一致，只更新派生追踪归类/索引；最终再次只读核对数据库完整性、刊期摘要与daily/X/Square不变。没有触发历史AI、消息补发、手动生产ACK或分支写入。

Rollback: 不自动回滚或恢复整库；原稿日志和Git历史保留，后续合并与部署按现有授权流程。
