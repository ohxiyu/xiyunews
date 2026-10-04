# 当前交接

主仓为私有 `ohxiyu/xiyunews`，正式域 https://xiyu.news。10月4日日报调度故障已经修复，12条已上线；当前只处理 Telegram 明确403后的安全补推。原迁移 Issue203、后台 Access 和东京实时服务均不并入本任务。

<!-- execution-pointer -->
```json
{
  "goal": "运营者确认机器人已加入频道后，核验日报频道权限并安全补推已发布的10月4日日报",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/208",
  "owner": "当前 Codex 会话，唯一编辑和整合负责人",
  "branch": "agent/telegram-daily-recovery",
  "last_verified_commit": "97241d5c95eca4eb68a14b792f5721e963a3c5db",
  "pr": "待创建，目标main",
  "completed": [
    "核验最新main、干净独立worktree、开放Issue/PR和正式域health；PR205/207已合并，生产仍为source71b3b168/artifactf9b9fb3f/Worker1b668bd4",
    "确认普通publish遇已发布刊期会直接返回，force_publish重建也刻意不发Telegram；不能以重新出刊补推",
    "新增Telegram-only main手动工作流，只读原始日报报告和gh-pages刊期，无AI、采集、出刊或队列写入",
    "仅允许报告明确bot-not-member403且零发送、同刊期/同原始启动时间/同条目数，预检必须为频道和日报Bot管理员发帖权限",
    "send默认关闭；按刊期串行；有任何历史send调用即拒绝再次发送，包含失败/超时和rerun；发送前写unknown检查点，成功保留message_id脱敏回执",
    "保持既有每日自动Telegram发送与紧凑消息样式不变，不部署Worker、不修改Secret、权限、X或币安广场队列"
  ],
  "unfinished": ["远端PR检查与合并", "真实权限核验及一次安全补推"],
  "validation": ["uv frozen dev通过；完整pytest1040项通过（1条既有google-genai/Python3.14弃用警告）；Telegram发送与恢复mock测试35项通过；治理及diff检查通过，不调用真实服务"],
  "unverified": ["日报Bot真实频道管理员发帖权限尚待安全检查", "今日Telegram补推回执及手机收件尚未验收", "明日07:26自然主触发尚未发生"],
  "production": {
    "source_commit": "71b3b16881999fa3578dc988f0066c785c772252",
    "artifact_commit": "f9b9fb3fe6f8fbbd3f9a237bb39f3b2b672148aa",
    "edition": "2026-10-04",
    "generated_at": "2026-10-04T03:43:17.666677Z",
    "worker_version": "1b668bd4-ebfd-4bdb-b944-03a408a6a905",
    "verified_at": "2026-10-04正式域health身份及既有部署版本回读；网站12条验收见前次发布记录"
  },
  "blockers": ["原Telegram失败明确403；运营者已报告加入频道，但代码不能将该报告视为权限验收"],
  "next_action": "完整mock测试、治理及远端CI通过后按长期授权合并；在main执行Telegram Recovery send=false，权限通过再send=true一次补推2026-10-04，原始日报run37174775715。不触发日报/force_publish/Worker或其他渠道。记录安全回执，真实手机收件另由用户确认。Crypto6/9与EN脉络缺失仍是独立质量事项。",
  "states": {"code": "complete", "tests": "complete", "pr_merged": "pending", "deployed": "pending", "production_verified": "pending"},
  "evidence": "project-docs/releases/2026-10-04-telegram-recovery.md"
}
```

本任务目录 `work/xiyunews-telegram-recovery`。前次调度修复和网站自然补刊证据见[10月4日恢复](releases/2026-10-04-daily-delay-recovery.md)；业务PR205和部署后文档PR207均已合并。不把网站成功等同于Telegram送达，不用历史任务作为新操作授权。
