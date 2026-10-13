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
