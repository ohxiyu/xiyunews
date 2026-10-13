# 当前交接

当前Issue250：网站每日必须运行，将现有工作流改为可选东京专用自托管执行器，避免耗尽的GitHub托管分钟。原UI折叠PR249已完整验证但受额度阻塞，保留独立分支，基础执行方案完成后再同步main并恢复其验证发布。本次不把旧Telegram自然收件或旧资源清理带入。

<!-- execution-pointer -->
```json
{
  "goal": "迁移工作流计算到现有东京服务器，保障每日采集发布",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/250",
  "owner": "当前会话唯一编辑与生产整合负责人",
  "branch": "agent/self-hosted-runtime",
  "last_verified_commit": "36cc79258b196146fcf74e23137ff076db7c7515",
  "pr": "https://github.com/ohxiyu/xiyunews/pull/251",
  "completed": ["东京Ubuntu24.04/2CPU/1613MiB与实时进程只读核验，严格SSH身份通过", "现有工作流可配置执行器、可信PR守卫、受限安装/注册/服务及手册已准备"],
  "unfinished": ["服务器安装/注册进行中，实际自托管CI、合并及正常采集/部署验证", "独立UI PR249随后同步新main并验证合并上线"],
  "validation": ["服务器available846MiB、磁盘34GB可用，实时MemoryCurrent约300MiB/NRestarts0，无现有runner", "完整Python1064passed/4skipped，串行Worker130passed、audit0/types/tsc/dry-run、治理/diff、bash语法/Python编译通过", "Ubuntu所需依赖可用、安装目标路径均不存在，原fomobtc仍active", "已核对SHA256的actionlint1.7.12对全部工作流验证通过，旧Pages预览通过，GitHub托管CI38348135782因额度在步骤前失败"],
  "unverified": ["实际运行峰值、注册/在线和当前PR的自托管CI、采集及发布均未验证", "下一次自然日报与四小时采集需分别验收"],
  "production": {"source_commit": "305701a18aca68c91b0945d3a873c09571e740c3", "artifact_commit": "5b72a32067c87b6110e8ab22476f50b89bcbc13e", "edition": "2026-10-13", "generated_at": "本轮尚未重建，不改原资讯", "worker_version": "c49f4b21-cb47-46c2-acfc-afb9a73defff", "verified_at": "2026-10-13只读，主站/实时健康与服务器原进程核对"},
  "blockers": ["GitHub托管2000分钟已用完，预算0且达限停用；当前PR未切换runner"],
  "next_action": "运营者2026-10-13明确要求按准备方案直接改完上线并优化服务器运行，新增服务/注册/切换授权已取得，按手册继续安装，在线后选择标签、真正CI通过同步main才合并，再验证正常自动发布与采集；不再重复问本方案授权，不买升级、不改业务秘密/DNS/Access/Cron、原实时进程或手工状态。",
  "states": {"code": "complete", "tests": "complete", "pr_merged": "pending", "deployed": "pending", "production_verified": "pending"},
  "evidence": "project-docs/releases/2026-10-13-self-hosted-runtime.md"
}
```

执行见[自托管手册](self-hosted-runner.md)、[当前记录](releases/2026-10-13-self-hosted-runtime.md)；待恢复UI见[PR249](https://github.com/ohxiyu/xiyunews/pull/249)，本地1064Python/33Node及整站构建通过，未上线。历史架构仍标原实际执行位置，切换验收后更新[架构](system-architecture.md)。
