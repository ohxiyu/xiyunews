# 当前交接

实时 API 与看门狗已完成迁移到 https://api.xiyu.news。业务PR217的代码、测试、合并、部署与自然线上验收均已完成；此指针只用于文档证据PR，不再次部署或重复运行生产任务。

<!-- execution-pointer -->
```json
{
  "goal": "记录已完成的 api.xiyu.news 接口迁移、Worker 发布和自然看门狗验收",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/218",
  "owner": "当前 Codex 会话，唯一编辑和生产整合负责人；串行部署",
  "branch": "agent/realtime-api-evidence",
  "last_verified_commit": "4e3862117671db962798fc305622a476f07e5ec7",
  "pr": "本次仅验收文档PR待创建；业务PR217已合并且完成部署",
  "completed": [
    "业务PR217所有必需检查成功后合并为4e3862117671db962798fc305622a476f07e5ec7；CodeQL analyze因现有私有授权跳过，未绕过失败检查",
    "专用api.xiyu.news DNS-only A到47.79.36.171，独立证书已签发且原certbot timer active/enabled",
    "新旧API HTTPS health200、ready503（原HL降级）、未知路径404、POST403、HTTP308、no-store均验证；同一d6a9d3f应用/MainPID235825/NRestarts0未变",
    "统一部署37329563017成功；Worker fb50c31c-7ca6-4339-b1f6-9929bd12ae74，source4e386211、artifact3670b9be保持，主站/watchdog开关正常",
    "2026-10-05T15:05:32Z自然五分钟Cron为新Worker版本，outcome ok/无exceptions/watchdog:ok；采集not_due、X/Square idle",
    "STATE只读为failing0/alertedfalse/lastAlert0，未清空或重置；没有人工消息、真实AI、发送服务重启或队列修改"
  ],
  "unfinished": [
    "本次仅验收文档PR检查合并，之后不再次部署",
    "手机告警/恢复通知实际收件由运营者确认；此前Quick Post真实AI/Access验收仍未执行"
  ],
  "validation": [
    "业务uv frozen dev成功；根pytest1044 passed，1条既有依赖弃用warning",
    "Node watchdog7/Worker102通过，typecheck/audit0；远端realtime Python3.11/3.12各61项及ruff/mypy/仓库检查通过",
    "业务CI37329100332 test/edge-build/governance/realtime及Pages通过；CodeQL按现有私有套餐跳过",
    "文档分支uv frozen dev/根pytest1044/治理通过；提交前再次检查修改后的指针和链接"
  ],
  "unverified": [
    "Telegram手机实际告警或恢复通知未独立证明；自然watchdog无异常不等同收件验收",
    "既有Hyperliquid degraded保留，ready503不是本次迁移故障",
    "本任务不验证旧域退役或此前Quick Post真实AI/Access操作"
  ],
  "production": {
    "source_commit": "4e3862117671db962798fc305622a476f07e5ec7",
    "artifact_commit": "3670b9beeba36078fe0b47343070e6f073da76c0",
    "edition": "not changed：本任务不出刊",
    "generated_at": "not changed：本任务不重建内容",
    "worker_version": "fb50c31c-7ca6-4339-b1f6-9929bd12ae74",
    "verified_at": "2026-10-05T15:05:32Z自然Cron及随后public health/STATE只读验收"
  },
  "blockers": [],
  "next_action": "文档PR全绿后按长期授权合并并清理本次已合并任务分支/worktree；不再部署。业务迁移五阶段已完成，旧API/证书过渡保留；旧资源删除、回滚、Secret/目的地调整仍需单独授权。收到运营者手机通知确认后可补录，不造故障、不重置STATE。不继续旧Quick Post任务。",
  "states": {
    "code": "complete",
    "tests": "complete",
    "pr_merged": "pending",
    "deployed": "not_required",
    "production_verified": "not_required"
  },
  "evidence": "project-docs/releases/2026-10-05-realtime-api-domain.md"
}
```

东京采集发送应用仍为 d6a9d3f29ef93c138842342c973b3049fb7bc252/systemd fomobtc；仅 nginx 代理变更。旧 api.fomobtc.com 与证书过渡保留，未获删除授权。真实Telegram收件与自然健康日志分开记录；此前 Quick Post 未验证边界见[原记录](releases/2026-10-04-quick-post-batches.md)。
