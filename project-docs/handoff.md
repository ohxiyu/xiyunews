# 当前交接

本次仅迁移实时 API 域名及看门狗目标。主站 https://xiyu.news 已迁入统一 Worker；此前实时接口仍用旧域，这是品牌迁移遗漏，不是采集停服。

<!-- execution-pointer -->
```json
{
  "goal": "将实时 API 迁到 api.xiyu.news，保留旧接口并更新统一看门狗",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/216",
  "owner": "当前 Codex 会话，唯一编辑和生产整合负责人；串行部署",
  "branch": "agent/realtime-api-domain",
  "last_verified_commit": "744791f5f6eab5dddc5a6f0ccd62aaa682018fe3",
  "pr": "待创建；独立任务分支已建立，不编辑旧工作区",
  "completed": [
    "确认原监控和 nginx 仍使用 api.fomobtc.com；新域原来命中通配符且健康522",
    "用户明确授权 DNS、证书、nginx 和监控 Worker 部署，旧接口过渡保留",
    "新增 api.xiyu.news A 47.79.36.171 DNS-only；Google/Cloudflare DoH 已回读",
    "mock 监控新URL/异常路径7项、根pytest1044项、Worker102项、typecheck/audit0已通过"
  ],
  "unfinished": [
    "新域 TLS/只读边界与旧接口验证",
    "业务PR检查合并、现有统一Worker流程部署及自然Cron核验",
    "上线后通过文档PR更新最终证据"
  ],
  "validation": [
    "uv sync --frozen --extra dev 成功",
    "uv run pytest：1044 passed，1条既有依赖弃用warning",
    "Node watchdog：7 passed；Worker：102 passed；npm typecheck/audit0成功"
  ],
  "unverified": [
    "证书与新HTTPS尚在迁移中",
    "新代码尚未合并或部署；自然watchdog和Telegram恢复通知尚未核验",
    "先前 Quick Post 真实AI/Access验收仍未执行，不因本任务补做"
  ],
  "production": {
    "source_commit": "744791f5f6eab5dddc5a6f0ccd62aaa682018fe3",
    "artifact_commit": "3670b9beeba36078fe0b47343070e6f073da76c0",
    "edition": "not changed：本任务不出刊",
    "generated_at": "not changed：本任务不重建内容",
    "worker_version": "496f3131-144e-4a25-ae59-44f5b47b6b34",
    "verified_at": "2026-10-05 迁移前公开 /health 与东京 systemd 只读核对"
  },
  "blockers": [],
  "next_action": "先完成独立证书与只读TLS新接口，再同步main、重跑验证、提交PR并待CI全绿合并；按本次明确授权部署统一Worker，观察自然Cron，不重置STATE或制造Telegram测试消息。已授权仅此DNS/接口/监控迁移；不改主域/www/通配符、发送服务/env/数据库/队列、费用和旧资源。",
  "states": {
    "code": "complete",
    "tests": "complete",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-05-realtime-api-domain.md"
}
```

代码、测试、合并、部署、线上验收分开记录。原东京应用 d6a9d3f29ef93c138842342c973b3049fb7bc252/systemd fomobtc 不重启，密钥/SQLite/Telegram 话题和自然发送保持。旧 api.fomobtc.com 作为过渡接口，未获删除授权。此前 Quick Post 的部署及未验证边界见[原记录](releases/2026-10-04-quick-post-batches.md)，不继续旧任务或补刊。
