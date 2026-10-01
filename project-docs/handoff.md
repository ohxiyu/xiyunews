# 当前交接

当前目标：按五阶段迁移提示词改为稀有News / xiyu.news，当前执行阶段 1。保持页面结构、内部包名、提醒规则、来源配置与服务器运行路径不变；后续阶段必须从本阶段合并后的 main 顺序执行。

<!-- execution-pointer -->
```json
{
  "goal": "阶段 1：品牌与域名迁移，随后顺序推进阶段 2–5",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/168",
  "owner": "Codex / 迁移唯一编辑及部署整合负责人",
  "branch": "agent/xiyunews-brand-domain",
  "last_verified_commit": "de180b0cf4ef99699374d606137c750b897a2428",
  "pr": "https://github.com/ohxiyu/xiyunews/pull/169（待最终 CI；已配置过渡开关）",
  "completed": ["完整阅读两仓规则、交接、部署手册与发布记录", "主仓库已改名 ohxiyu/xiyunews；运营者授权后两仓均已核验为私有", "Cloudflare xiyu.news 免费 zone 已创建；Dynadot 已回读保存后的两条 Cloudflare NS", "阶段 1 已推送并建立 Draft PR169；本地完整检查通过，e8155eab 的远端 CI/CodeQL/Pages 预览全部通过"],
  "unfinished": ["阶段 1 合并、生产发布与新旧域验收", "DNS、Pages 新域与后台 Access 验收", "阶段 2 调度器引用及部署", "阶段 3–5 实时服务并入、部署与 Telegram 品牌"],
  "validation": ["GitHub API 确认新仓库名", "独立 worktree 从 origin/main 建立，不覆盖用户修改", "Python 3.13 本地完整 929 项 pytest 通过；模板安全与页面输出子集通过", "Node 全部 76 项前端/Worker 测试通过，其中新增 15 项旧域精确跳转检查", "独立调度器 61 项测试、类型、部署 dry-run 通过；未改其配置或部署", "Jekyll 本地 github-pages 232 / Ruby 3.3 构建通过；未改变仓库 Gemfile，远端 Pages 构建待检查", "治理与 git diff --check 通过；原 v1/v2 媒体包及历史证据未修改"],
  "unverified": ["新域 HTTP、旧域 301、后台登录及 Quick Post", "新仓库实时服务 SHA、三个分片与自然回执"],
  "production": {
    "source_commit": "fa50a0fd95619db4ccd46cc056105925df294466（迁移前记录）",
    "artifact_commit": "62cf58765e6edd92f1007e32375165a1ba5137cb（迁移前记录）",
    "edition": "2026-10-01（迁移前记录）",
    "generated_at": "2026-09-30T23:28:59.968601Z（迁移前记录）",
    "worker_version": "本轮未部署或验收",
    "verified_at": "尚未完成迁移后生产验收"
  },
  "blockers": ["注册商已保存 NS，但 DNS 查询尚未更新；待 Cloudflare active 后绑定 Pages", "本机不存在既有 fomobtc_tokyo_config；阶段 4 服务器部署仍需持有原 SSH 配置的运营者电脑"],
  "next_action": "已回读生产 LEGACY_REDIRECT_ENABLED=false，最终 CI 全绿后合并发布品牌，再从新 main 顺序执行阶段 2；新域/HTTPS/Access 就绪后开启 301 并完成阶段 1 验收；两仓私有后才允许导入完整历史",
  "states": {"code": "complete", "tests": "complete", "pr_merged": "pending", "deployed": "pending", "production_verified": "pending"},
  "evidence": "project-docs/releases/2026-10-01-xiyunews-brand-domain.md"
}
```

上轮交付见 [Logo 记录](releases/2026-10-01-brand-v3.md) 与 [Python 安全记录](releases/2026-10-01-security-deps.md)。本轮不改 Logo 图形、不恢复漏洞版本，也不继续历史待办或其他人的 PR。迁移操作见 [运行手册](brand-domain-migration.md)；realtime 尚未并入，因此暂不伪造其交接链接。
