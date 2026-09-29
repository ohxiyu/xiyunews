# 当前交接

当前目标：[Issue152](https://github.com/ohxiyu/bmtnews-standalone/issues/152) 追踪优化（事件合并、生命周期、重点追踪）。上一任务 [Issue150](https://github.com/ohxiyu/bmtnews-standalone/issues/150) X 模板帖截断已由 PR151 合并，记录见 [2026-09-29-x-template-truncation.md](releases/2026-09-29-x-template-truncation.md)。

<!-- execution-pointer -->
```json
{
  "goal": "同一事件不再被拆开；追踪事件按时间过期；追踪页与首页突出最重要的事件",
  "issue": "https://github.com/ohxiyu/bmtnews-standalone/issues/152",
  "owner": "Claude Code / event-focus",
  "branch": "agent/event-focus",
  "last_verified_commit": "46c6402b76177c867632607c368922aaf7f9c971",
  "pr": "pending: PR for agent/event-focus",
  "completed": [
    "多重高置信匹配归入进展最多的事件，不再另开新事件",
    "按主体分组的合并审查（每次最多 3 次调用），同阶段报道并为一个节点，旧事件页跳转",
    "生命周期：活跃 7 天 / 沉寂 30 天 / 归档；热度排序",
    "追踪页重点追踪 + 紧凑列表 + 折叠沉寂与归档；首页重点追踪入口",
    "PR151 已合并（46c6402）"
  ],
  "unfinished": [
    "Telegram 候选频道调整等待维护者决定",
    "2026-10-05 周报推送验收"
  ],
  "validation": [
    "uv run pytest 全部通过；治理检查通过；生产目录离线模拟；Liquid 严格渲染与截图"
  ],
  "unverified": [
    "真实模型的事件分组质量与合并后中文补译",
    "上线后追踪页、首页入口与旧事件页跳转"
  ],
  "production": {
    "source_commit": "46c6402b76177c867632607c368922aaf7f9c971 (this change not merged)",
    "artifact_commit": "gh-pages 7cf19ad (Daily Summary 2026-09-29)",
    "edition": "2026-09-29",
    "generated_at": "2026-09-29T07:31:02+08:00",
    "worker_version": "not changed",
    "verified_at": "2026-09-29; offline simulation on the production event catalog"
  },
  "blockers": [],
  "next_action": "CI 通过后合并；下一次 Feed Collection 后核对 event_merge 指标、Bitget 合并结果与追踪页",
  "states": {
    "code": "complete",
    "tests": "complete",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-09-29-event-focus.md"
}
```
