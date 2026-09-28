# 当前交接

当前目标：[Issue136](https://github.com/ohxiyu/bmtnews-standalone/issues/136) 修复项目审查确认的 P0 问题并给聚合信源降噪。上一任务（Issue131 X 先计划后发送）已完成并验收，记录见 [2026-09-26-x-plan-send.md](releases/2026-09-26-x-plan-send.md)。

<!-- execution-pointer -->
```json
{
  "goal": "修复审查确认的 P0 问题（sitemap 覆盖、去重单条组停刊、Google News 标题与链接、pip-audit 重试）并给聚合信源降噪",
  "issue": "https://github.com/ohxiyu/bmtnews-standalone/issues/136",
  "owner": "Claude Code / p0-fixes",
  "branch": "agent/p0-fixes",
  "last_verified_commit": "3fabce220f11cf9c2c17841f0182f6e17fc93c9c",
  "pr": "pending: PR for agent/p0-fixes",
  "completed": [
    "删除提交的 docs/sitemap.xml 并忽略，只由日报生成",
    "去重忽略不含合并决定的单条组；其他格式错误仍失败关闭",
    "Google News 去除标题媒体尾巴、在线解析跳转链接（失败保留原链接）",
    "pip-audit 只在 PyPI 故障时重试",
    "Google News 黑名单 + GDELT 白名单；本地 871 项测试通过"
  ],
  "unfinished": [
    "PR 检查与合并（合并需维护者确认）；上线后观察链接解析率、入选来源和 sitemap"
  ],
  "validation": [
    "uv run pytest 871 项通过；pip-audit 重试脚本本地模拟四种情况符合预期；治理检查通过"
  ],
  "unverified": [
    "Google News 在线解析未做真实请求（本环境无法访问 news.google.com）",
    "域名过滤对入选质量的影响"
  ],
  "production": {
    "source_commit": "3fabce2 (current main; change not merged)",
    "artifact_commit": "not changed by this branch",
    "edition": "2026-09-28, 12 items",
    "generated_at": "2026-09-27T23:26:33.795069Z",
    "worker_version": "not changed",
    "verified_at": "2026-09-28; offline tests only"
  },
  "blockers": [
    "合并与上线需维护者确认"
  ],
  "next_action": "开 PR；合并后看下一次 Feed Collection 的解析率日志和下一期日报后的 sitemap",
  "states": {
    "code": "complete",
    "tests": "complete",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-09-28-p0-fixes.md"
}
```
