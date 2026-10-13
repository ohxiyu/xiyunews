# 迁移执行位置以解除托管分钟限制

Issue: https://github.com/ohxiyu/xiyunews/issues/250。当前会话唯一编辑/整合负责人，agent/self-hosted-runtime，基于main36cc79258b196146fcf74e23137ff076db7c7515；当前UI PR249保持独立，随后需同步新main、回归与合并，不能丢弃。

PR: https://github.com/ohxiyu/xiyunews/pull/251（Draft）。

运营者要求网站每天运行并避免GitHub托管分钟限制。已在Safari实时核对Free/2000分钟全部用完、Actions实际费用0、预算0且达限停止；不存在已确认的14.27美元欠款，它是已抵扣用量。官方当前说明self-hosted执行免费，不升级预算、套餐或新购主机。选用现有东京Ubuntu24.04、2CPU/1613MiB、磁盘34GB可用、MemAvailable846MiB，实时MemoryCurrent304132096/NRestarts0。来源和成本不以这次运行位置迁移改变。

## 实现与权限

所有20处job执行标签改为非秘密变量显式选择，缺省保留原Ubuntu托管。安装脚本、固定仓注册器与systemd服务已准备；单个专用runner串行、768MiB/0.75CPU上限、可信同仓PR守卫、实时目录不可见，Vitest按环境串行。部署须在运营者确认新服务器服务与仓库runner注册后执行；不修改业务Secrets、主域/DNS/Access/Cron、实时进程或队列规则，不手工写状态分支、不发送测试或历史消息。完整可执行步骤见[手册](../self-hosted-runner.md)。

Source commit: pending；开工main36cc79258b196146fcf74e23137ff076db7c7515。
Worker version: not changed；c49f4b21-cb47-46c2-acfc-afb9a73defff。
Deployment: pending，服务器安装/仓库注册和runner选择尚未执行，不宣称已切换。
Verification: 仅完成严格SSH只读主机/容量/原进程检查及GitHub私有仓admin权限、无现有runner核对；代码/实际CI/采集/部署与自然日报待验证。
Rollback: 先获批准；只恢复runner变量或停新服务，原实时服务与状态不变，不自动回滚/删资源。

本地完整Python1064passed/4skipped；串行Worker130passed，npm audit0、types/tsc/dry-run和治理/diff通过，脚本bash语法及Python编译通过。服务器只读确认所需Ubuntu包可用，目标路径不存在，原fomobtc仍active。本轮没有改前端/模板，不重复其视觉测试；下一步实际runner安装/注册和资源峰值不能由本地通过代替。

已验证SHA256的actionlint1.7.12对全部工作流检查通过。GitHub托管CI38348135782仍在步骤前因账户额度失败，旧非生产Pages预览通过；未将其当实际runner验收。已向运营者请求新服务器常驻服务及仓库机器运行凭据注册/部署的确认（根AGENTS.md要求凭据/新增外部认证先批准），未收到答案，尚未安装或注册，不以任务代码准备或时间经过当授权。

2026-10-13运营者明确回复“可以你帮我直接改完上线。既然换到了服务器，其实很多事情可以再优化一下了”，授权已准备方案的新增服务/机器注册/运行切换与生产发布。严格SSH复查原MainPID235825/NRestarts0、MemoryCurrent304128000、available840MiB，安装目录此前不存在；开始按手册安装。此时尚未注册/切换，不将授权或安装进行中当完成。

12:56安装并注册成功，GitHub runner id21/xiyunews-tokyo-1，online；非秘密标签变量精确self-hosted/Linux/X64/xiyunews-tokyo。现有Secrets未改，注册Token走stdin，无明文导出。第一轮真实CI38349010751开始执行，realtime-paths成功、Python/依赖审计阶段通过，但Worker单进程累计内存触发软线回收，2项5秒测试超时及2项pool启动超时（78passed），未写成功；主动取消本轮自有CI后修改受限测试执行方式。

调优仍单任务串行、内存硬768MiB，软704MiB、CPU1核、Node堆256MiB；每个Worker测试文件用新进程，保留全部130项。不调整模型/来源或生产规则。原fomobtc MainPID235825/NRestarts0始终不变，无OOM，峰值741068800字节；维护timer每周日上海04:10加最多20分钟，仅旧执行日志/uv无用包缓存，dry-run0、实际Resultsuccess。优化后全量CI与业务验收尚待完成。

第二轮38350259461治理通过，Python/审计完成，缓存命中后的npm11.19依赖安装触及768MiB硬线并持续回收，主动取消该自有CI调优。重启新runner释放内存（一次服务stop90秒后SIGKILL清理取消测试，原fomobtc PID235825/NRestarts0及三分片/Telegram/队列不变），GitHub旧session短时冲突待重连，不宣称CI通过。加入原生解压单线程/npm连接2、固定npm11.11.1及专用512MiB磁盘缓冲，root0600、独立开机服务，执行器swap上限512MiB，物理内存硬上限不增；不购买升级或停原提醒。Ubuntu官方gh2.45已补齐，安装脚本/完整重建手册同步。仍需优化后全量CI和生产验证。

服务器原vm.swappiness=0，缓冲启用后仍不换页；已按本轮优化授权改20并保存专用sysctl.d配置，原值保留证据。第三轮38351366705整站构建success（Jekyll120.716秒，缓存依赖安装2分钟，npm11.11.1），治理/路径success；完整应用/Worker步骤已通过、正在post缓存，实时两套环境尚待完成。物理峰值741953536、缓冲一度约229MiB后回落；原PID235825/NRestarts0。最终完整配置补入仓库后重新核对实际head CI，未经全通过不合并。

## 最终执行方案验收

最终head7391c8ca64f84e79d0cf9752412753e6b452a6e1的CI38352364252全部适用任务通过：edge-build3m43s、应用2m46s、治理/路径与实时Python3.11/3.12通过；CodeQL按原私有免费授权条件跳过，未购买升级。PR251于上海13:46:54合并7388457ae407ebf68d00a4c1d9b519c354052cf6。

Source commit: 7388457ae407ebf68d00a4c1d9b519c354052cf6（执行方案首次生产快照）。
Worker version: f4bf4bd7-8e7b-4ed3-a353-8b4ba0bee0ae（随后UI/兼容修复独立发布）。
Deployment: Deploy Docs38353164281及统一Worker38353244993均success，真实runner为xiyunews-tokyo-1，产物db8e866244912b5a964920c45e5a6cdcb0ce46c3。
Verification: 上海约13:54回读/health status=ok且source/artifact/version一致；实时PID235825/NRestarts0、三个现货分片live、队列0，执行器内存峰值741953536字节、无OOM。维护timer已启用且首次Resultsuccess；AI/产物/队列/原实时数据不清理。
Rollback: 仅经批准恢复runner变量/停新服务；托管额度仍耗尽、预算0，旧执行位置不是可用备用，不自动回滚/删资源。

第一次正常采集38353543010及X恢复出版状态时暴露持久checkout旧浅层ref，Square门控38354408915暴露初始化前缺少python。均在AI/发送前失败，未以首次静态上线当业务链路成功。已独立PR254实际CI38355573706全通过后合并b5abadb2b44708533bc2db2f2f01b44d4c6cf857；日报恢复38356746499真实服务器success并返回healthy HTTP200，不重复日报。正常采集和最终版出版证据见[兼容修复记录](2026-10-13-persistent-checkout.md)。服务器仍单实例，未来自然日报单独验收。
