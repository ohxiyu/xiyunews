# 当前交接

当前 Issue236：修复双话题推送的 Workers 请求兼容性并记录验收。PR235 已部署，自然 Cron 安全拦住发送；workerd 不支持 redirect:error，改用 manual 并显式拒绝 3xx，准备修正版 CI/合并/部署。两个话题与绑定保留，不补历史、不发测试；原频道、实时话题、服务、运行密钥、来源和 Cron 未改动。

<!-- execution-pointer -->
```json
{
  "goal": "修复 Workers Telegram 请求兼容性，验收自然 Cron 并记录真实发送边界",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/236",
  "owner": "当前 Codex 会话，唯一编辑与发布整合负责人",
  "branch": "agent/telegram-group-deployment-record",
  "last_verified_commit": "ed6211c53b15467e72e92eb9f6c28fd90d326f53",
  "pr": "修正版 PR 待创建；应用 PR235 已合并",
  "completed": [
    "独立 worktree，保留原工作区未提交文件",
    "基于出版数据的只读消息准备：固定日期、完整条目拆分、同一重点事件索引及原证据",
    "专用初始化脚本已仅创建两个批准话题，服务器私有回执不含 Token",
    "严格 SSH 主机核验与 Bot/群/权限回读通过，can_manage_topics=true",
    "复用现有 Worker、KV 与独立命名 Durable Object；持久化回执、未知结果不自动重发、两个目的地故障隔离",
    "同日 API/首页/不可变快照一致后才准备一次每日任务；初次概览及后续实质节点增量",
    "私有 KV 绑定回读通过，启用日 2026-10-13；应用 PR235 CI 全通过并合并",
    "统一 Worker 部署 38276156648 成功；线上 source/artifact/版本匹配，首页/API/追踪均 200，内部快照 404"
  ],
  "unfinished": [
    "修正版 CI、合并、同功能授权部署与自然 Cron 私有身份状态回读",
    "2026-10-13 自然日报发布后两话题真实消息回执与客户端展示"
  ],
  "validation": [
    "身份、群与管理话题权限只读核验及两个创建回执通过",
    "Worker audit 无漏洞、类型检查及 123 项测试、dispatcher dry-run 通过",
    "主项目完整 pytest 1063 passed、4 skipped；治理与 diff 检查通过",
    "兼容性修正版 audit/typecheck/124 项 Worker 测试与 dry-run 通过，mock 先构造真实 Request",
    "实际 gh-pages 消息离线准备通过；历史退役 URL 桩不伪造状态/时间；UTF-16 安全拆分测试通过"
  ],
  "unverified": [
    "PR235 的自然 Cron bot_verified=false；请求模式兼容性修正版尚未部署",
    "没有真实消息发送回执；不把话题创建与离线测试算作消息送达"
  ],
  "production": {
    "source_commit": "ed6211c53b15467e72e92eb9f6c28fd90d326f53",
    "artifact_commit": "d5a1b6da90305d132dcf7157183d082d2f60169a",
    "edition": "2026-10-12",
    "generated_at": "本任务未生成新闻，仅读取已出版内容",
    "worker_version": "313f00fb-1f53-4d3a-ab5f-ea1b30bc8273",
    "verified_at": "2026-10-13 00:18 Asia/Shanghai，health 与公开 URL 回读"
  },
  "blockers": ["现役版本请求 redirect:error 被 workerd 拒绝，没有任何新闻送达；修正不需变更 Token"],
  "next_action": "修正版通过 CI、同步 main 后合并并部署，核验自然 Cron bot_verified=true；今日自然日报发布后再只读核验两话题 message_id/客户端内容。",
  "states": {
    "code": "complete",
    "tests": "complete",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-12-telegram-group-topics.md"
}
```

上一项重点事件 UI 发布与验收已完成，见 [发布记录](releases/2026-10-09-focused-tracking.md)；网页版式保持不变。现行数据规则见 [数据契约](data-contract.md)，原频道与实时群继续独立。
