# 当前交接

项目统一名为 `xiyunews`，网站为 https://xiyu.news，主仓为私有 `ohxiyu/xiyunews`。PR195 保留完整实时历史，PR199 已合并为 b2aeb97f；2026-10-03 已实际完成原状态迁入、主域接管和统一 Cron 启用，原两个 Worker 已停用，旧 Pages 不再绑定主域。首次自动部署和两轮自然看门狗通过；登录后的后台读取、下一次自然派发和旧资源退役继续分项验收，不能把网站 200 当全部完成。

<!-- execution-pointer -->
```json
{
  "goal": "记录并完成 xiyunews 统一 Cloudflare 生产接管验收，保留单调度、原状态与后台权限",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/201",
  "owner": "迁移唯一编辑及发布整合负责人，串行执行父任务 Issue198",
  "branch": "agent/xiyunews-cutover-verification",
  "last_verified_commit": "b2aeb97f8481bfad123277463c24bddac0895f8c",
  "pr": "部署后文档 PR 待创建；业务 PR199 已合并，父任务 Issue198 仍开放",
  "completed": [
    "PR195 完整实时历史已合并，旧 main 是主仓祖先；服务器已从新仓 d6a9d3f 发布，原路径、数据库、话题和规则不变",
    "GitHub 和 Cloudflare 运行凭据已隐藏配置，统一 Worker 8 个运行 Secret 名称独立回读；不再要求重复 Token 或 /start",
    "PR199 最终 head add3b206 的 CI37119954469 和 Pages 预览通过，正常合并为 b2aeb97f8481bfad123277463c24bddac0895f8c",
    "从当前生产出版快照 4f87497e 真实构建 8593 个资产，暂停预览部署14e88d14；源代码和出版完整 SHA 回读一致",
    "已给旧 dispatcher/watchdog 部署精确 true 停用保护并清空 Cron，版本1f2c4d8a/90b876b9；旧回调不继续访问网络、写状态或通知",
    "已在暂停配置下 transfer RecoveryGate，原 namespace d4f55a5a95624e7e9776bbf050cf1ee7 保持，本地归属 xiyunews；STATE KV469346950dfc4f36b8d9bf9997d960fa 保持",
    "运营者选择第1项具体确认后解除旧 Pages 的 xiyu.news 绑定与对应 CNAME，再由统一 Worker 接管 Custom Domain；没有删除项目、域名注册或数据",
    "正式域首页/API/RSS/sitemap/PWA/openapi/llms 正常，canonical=xiyu.news；后台原 Access 匿名302，预览后台 wrong-origin403",
    "实际部署最终配置f8c394e3，两个开关true、原三组Cron启用；XIYUNEWS_EDGE_ENABLED=true，首次纯部署工作流37122753609已启动"
  ],
  "unfinished": [
    "首次自动部署和两轮自然Cron通过；仍需下一次真正到期的自然dispatch，不能用手动运行冒充",
    "Safari 的后台 Access 需要运营者用原账号自行登录后，核验 Quick Post 读取；不索取或代填验证码",
    "旧 Pages/两个旧Worker/旧实时仓库仍保留，完成迁移验收并核对独有历史后再安排准确范围退役",
    "Access 应用显示名仍为 BMTNews Admin，发现于登录页；仅名称待统一，不擅自改变权限或认证方式"
  ],
  "validation": [
    "业务代码根完整1019项、边缘95项/type/audit0、watchdog4项及治理/dry-run通过；远端CI全部可用检查成功，私有套餐CodeQL跳过",
    "transfer实际版本de359776回读RecoveryGate namespace与STATE KV ID均等于原值，8个Secret保留、双开关false",
    "域接管暂停版本559c5ce3；首页/API/latest/feed/sitemap/PWA/openapi/llms200、旧日报链接自动重定向后200、不存在路径404",
    "正式域/s、/s/、/admin、/api/admin和/api/admin/quick-posts匿名302至原Access；未打开权限或发布测试内容",
    "首次GitHub部署37122753609=success，版本00b0f0f6-f6cf-4ba7-9b79-96644eb6c7dc正式域/绑定回读一致、原DO/KV/8Secret保留",
    "统一自然Cron计划2026-10-03T12:30:51Z及12:35:51Z均outcome=ok、watchdog:ok、exceptions=[]，采集fresh/not_due，x/square均idle；没有人为测试发送",
    "本轮根完整1019项、治理、实时repository契约与diff通过；旧独立仓仅main、无tags/开放PR，37个关闭PR均merged，旧main祖先已核验"
  ],
  "unverified": [
    "登录后的Quick Post读取和下一次真正到期的自然dispatch",
    "手机实际收件及看门狗实际私聊告警；没有故障时不人为制造告警或重放失败消息",
    "旧仓Git主历史已核对，但GitHub Issues/PR页面/设置等非Git内容没有完整备份，不将subtree视为可恢复全部资源"
  ],
  "production": {
    "source_commit": "b2aeb97f8481bfad123277463c24bddac0895f8c",
    "artifact_commit": "4f87497ecf068324e0a6211e9f4a38a7047f797e",
    "edition": "2026-10-03",
    "generated_at": "2026-10-02T23:29:27.197755Z",
    "worker_version": "00b0f0f6-f6cf-4ba7-9b79-96644eb6c7dc",
    "verified_at": "2026-10-03T12:36Z，正式域、版本/状态绑定及两轮自然Cron核验"
  },
  "blockers": [
    "后台需运营者自行完成原Access登录，助手不读取OTP或把业务Token用于绕过Access",
    "旧资源删除与Access显示名保存属于新的具体UI动作，准备目标后按电脑技能操作时确认；不据域解绑确认扩大范围"
  ],
  "next_action": "不再重跑隐藏凭据脚本或请求/start。首次自动部署与两轮自然watchdog已通过，等待运营者后台登录后只读Quick Post；继续核验下一次真正到期的自然dispatch，不手动采集或发消息冒充。旧仓Git历史已核对，具体确认旧边缘项目退役/旧仓只读归档并保留非Git审计；现用DO/KV、实时域/API/SQLite/env/备份必须保留。本次文档PR通过检查后按站立授权合并，不直接提交main。",
  "states": {
    "code": "complete",
    "tests": "complete",
    "pr_merged": "pending",
    "deployed": "not_required",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-03-cloudflare-production-verification.md"
}
```

本指针属于部署后文档与剩余验收任务，五状态不代替业务 PR199 已合并、生产已部署的事实；业务上线证据在上述 release 中独立记录。工作区复用 `/tmp/xiyunews-cloudflare`，仅一位所有者；当前分支从已核验 origin/main 创建，不继续编辑已合并任务分支。历史证据见 [前阶段记录](releases/2026-10-02-cloudflare-production-cutover.md)，架构见 [系统架构](system-architecture.md)，实时入口见 [实时交接](../realtime/docs/handoff.md)，操作边界见 [单项目清单](cloudflare-single-project.md)。
