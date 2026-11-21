# 当前交接

整站恢复基线改用 PR #306 的 `0291c7f`。恢复分支保留一个与基线 Git tree 完全一致的提交，随后单独记录依赖更新与生产启动开关。当前生产仍由 GitHub 托管任务、Cloudflare 私有 SQLite 及现有发送器运行。详见[恢复验证](releases/2026-11-21-pr306-tokyo-restore.md)。

<!-- execution-pointer -->
```json
{
  "goal": "以 PR #306 恢复前后端和东京生产执行方式，接续现行出版与发送状态",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/389",
  "owner": "当前 Codex 聊天",
  "branch": "agent/october-tokyo-restore",
  "last_verified_commit": "ac498f5dc428bb59ac1140347160c8b85d5c5820",
  "pr": "https://github.com/ohxiyu/xiyunews/pull/390",
  "completed": [
    "恢复提交的 Git tree 与 PR #306 合并提交一致",
    "更新 Soup Sieve 锁定版本，维持公开仓库 CI 的 GitHub 托管执行",
    "已用 11/21 归档通过旧版整站演练，保留现行 Cloudflare 私有状态接口"
  ],
  "unfinished": [
    "核对两套库与现有工作流日志中的逐期渠道回执，验证旧发送器的持久去重",
    "重新注册东京执行器并执行实时服务同机容量验收",
    "完成受控发布和生产回读"
  ],
  "validation": [
    "修复后 Python 1120 项通过、4 项既有跳过，Worker 140 项及网页 118 项通过",
    "Python all-extras 与 Node 依赖复审均零已知漏洞",
    "现行 Cloudflare SQLite 校验 44869611115 通过，东京旧库 quick_check 通过"
  ],
  "unverified": [
    "东京新执行器负载和旧 DeepSeek 凭据可用性",
    "旧工作流对当前私有库及所有发送回执的接续"
  ],
  "production": {
    "source_commit": "155cf1f7e5e489e060187f72986949a76a6784ce",
    "artifact_commit": "70979f0ce64ceceb0b1a7b33ec20bb06570c7f7c",
    "edition": "2026-11-21",
    "generated_at": "2026-11-21T07:30:29.999714+08:00",
    "worker_version": "见现行生产部署 44837387186",
    "verified_at": "2026-11-21 北京时间，/health 和当期 API 回读"
  },
  "blockers": [
    "东京 459–494 MiB 可用内存低于原安装脚本的 600 MiB 门槛，且 GitHub 当前注册数为零",
    "Cloudflare 与东京旧库的 Telegram 回执行数分别为 1 和 5，且 11/19–21 的发布日志均记录发送成功"
  ],
  "next_action": "分期核对发送记录，保持同一权威账本；完成归档验收和专用 Runner 容量检查后才允许接管生产。",
  "states": {
    "code": "pending",
    "tests": "pending",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-11-21-pr306-tokyo-restore.md"
}
```
