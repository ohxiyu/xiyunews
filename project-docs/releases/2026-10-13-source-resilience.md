# 优化1：受限RSS的同源索引恢复

Issue: https://github.com/ohxiyu/xiyunews/issues/258 ，总任务Issue257。当前会话唯一编辑/整合负责人，agent/source-resilience，基线3128d5c3d9ad5da315f0cbc4c4fa10abe33e1795。用户明确授权九项全部实施部署。

原RSS保留，失败才复用现有Google News采集器作同publisher域过滤、日期过滤、原链接解析，最多20条。四个来源启用替代，条目记录原媒体/原feed/获取方法/原错误，并强制headline-only，不能凭长索引HTML确认事件进展。原入口恢复则不调用替代；200的HTML挑战不能伪装空RSS成功。报告记录每feed原失败与替代条数，依然保留degraded/warning，不把替代叫原站恢复。

Source commit: pending，基线3128d5c3d9ad5da315f0cbc4c4fa10abe33e1795。
Worker version: not changed yet，现役afd40c2f-e05f-4aeb-91a4-ab59b2640c5c。
Deployment: pending，待当前CI全部通过并同步main后合并，经既有自动链路部署。
Verification: 东京The Block Google News公开索引200/100条解析，含2026-10-13报道；The Defiant/Tether替代官方订阅仍403，未解挑战。四源正式逻辑/离线测试/合并部署与完整流程仍待验证，不提前宣称其余八项完成。
Rollback: 先获批准，不重刊日报、清缓存、改发送状态、强推或删资源。来源配置本轮已明确授权。

当前全部后续步骤维护在[九项计划](../server-optimization-plan.md)。

本地完整1074项应用回归通过/4 skipped，相关来源/事件/报告55项与治理/diff通过。补充回归保证全部原RSS受限但替代取回内容时仍为partial_failure，不能误判all_failed停止其他内容；最终CI与东京实际四源脚本检查待完成。

最终head97da5503e00229824e75e84d9e7b60ce5c7b4b2b的CI38381934730全部适用检查通过（应用3m1s、整站3m57s、治理/路径14s）；PR259于上海18:22:19同步main后合并23192f361256f53823fd6617850286ca1e3f1901。东京同代码独立受限无AI检查成功：72h四源分别20/20/20/6、合计66项，四替代status success、全部headline-only；20.264秒/15.5MiB峰值，无原进程重启或发送。首次审查归档缺README导致本地editable安装失败，补齐原README/LICENSE后通过，应用代码没有因此变更。原RSS四个403仍正确degraded，未宣称原站解除限制。

正式正常采集38382903277已启动，源码读取新main；缓存、产物及出版验收待回读。后续第2项开始时补本记录，不再留旧未合并指针。
