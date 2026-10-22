# 当前交接

当前任务：[Issue295](https://github.com/ohxiyu/xiyunews/issues/295) 修复发布后边缘缓存跨版本复用。原 [Issue293](https://github.com/ohxiyu/xiyunews/issues/293) 的依赖修复 PR294 已合并并部署：首页已恢复为 22/21 日各 14 条，普通 latest API 仍命中 20 日旧缓存，加查询参数为 22 日。现将缓存与可信 SITE_BUILD_KEY 绑定，防止跨部署混用内容；不更改 TTL、业务状态或发送记录。架构入口为[系统架构](system-architecture.md)。访问统计的公开令牌仍待运营者提供，原记录保留在[访问统计发布记录](releases/2026-10-18-web-analytics.md)。

<!-- execution-pointer -->
```json
{
  "goal": "修复发布后边缘缓存跨版本复用，并完成网站恢复验收",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/295",
  "owner": "当前会话唯一编辑与生产整合负责人",
  "branch": "agent/publication-cache-version",
  "last_verified_commit": "d4d89453e4f7504397e46d5043ecd6b909af8d94",
  "pr": "PR294 已合并部署；缓存修复 PR 待创建",
  "completed": [
    "核对生产 API 为 2026-10-20，gh-pages 最新为 2026-10-22 的 14 条",
    "确认 21、22 日 Daily Edition 成功，中英文刊期在归档中存在",
    "PR294 与 CI39722103810 通过，统一部署 39722786056 成功",
    "公网中英首页为 22/21 日各 14 条；发现普通 latest API 跨部署旧缓存"
  ],
  "unfinished": ["缓存版本隔离回归及 CI", "缓存修复 PR 合并并正常部署", "普通公网首页/API/详情一致性验收及证据归档"],
  "validation": ["只读核对 Actions、gh-pages、生产 health/API 与东京服务器磁盘和服务", "npm 安全审计 0 漏洞，135 项 Worker / 117 项网页 Node 测试、类型与 dry-run 通过；治理通过"],
  "unverified": ["缓存版本修复的远端 CI、部署和公网一致性尚未验证"],
  "production": {
    "source_commit": "d4d89453e4f7504397e46d5043ecd6b909af8d94",
    "artifact_commit": "14cee6f84b30567b95f6d07dee5d787320f8e79f",
    "edition": "首页 2026-10-22，普通 API 暂为 20 日旧缓存",
    "generated_at": "2026-10-21T23:30:37.441584Z",
    "worker_version": "ece1c144-636e-4910-bec9-c77b2f943b7c",
    "verified_at": "2026-10-22 12:36 上海，主域首页、health、普通及新查询 API 回读"
  },
  "blockers": ["缓存一致性修复待 CI 与部署"],
  "next_action": "验证同 URL 跨部署不会复用旧缓存；合并缓存修复并正常部署，完成普通地址验收",
  "states": {
    "code": "complete",
    "tests": "complete",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-22-publication-recovery.md"
}
```
