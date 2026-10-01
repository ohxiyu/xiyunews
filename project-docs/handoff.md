# 当前交接

当前目标：按五阶段迁移提示词改为稀有News / xiyu.news，当前执行阶段 2。PR169 已合并，Deploy Docs 36823514928 成功；两仓均私有，旧域暂保留 200。保持页面结构、内部包名、提醒规则、来源配置与服务器运行路径不变。

<!-- execution-pointer -->
```json
{
  "goal": "阶段 2：新仓库调度、私有内容读取与 Worker 部署",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/170",
  "owner": "Codex / 迁移唯一编辑及部署整合负责人",
  "branch": "agent/xiyunews-dispatcher",
  "last_verified_commit": "e12179905981ed2ff5c31811db41f4c5f7b259d1",
  "pr": "待建立阶段 2 PR",
  "completed": ["阶段 1 PR169 检查通过后合并，自动发布成功", "两仓均私有，Dynadot 保存 NS；生产跳转开关 false 防止传播期间断站", "阶段 2 修正调度仓库、健康字段、Contents API 鉴权及不跟随认证跳转"],
  "unfinished": ["阶段 2 验证、合并与部署回读", "新域绑定、HTTPS、Access、旧域 301 验收", "阶段 3–5 实时服务并入、部署与 Telegram 品牌"],
  "validation": ["阶段 1 Python 929 项和 Node 78 项通过，远端 CI/Pages 全通过；私有 CodeQL 无付费许可证时跳过", "阶段 2 检查正在执行，最终结果见 PR 和本阶段记录"],
  "unverified": ["新域 HTTP、旧域 301、后台登录及 Quick Post", "私有 PAT 的 Contents 读取权限", "新仓库实时服务 SHA、三个分片与自然回执"],
  "production": {
    "source_commit": "fa50a0fd95619db4ccd46cc056105925df294466（迁移前记录）",
    "artifact_commit": "62cf58765e6edd92f1007e32375165a1ba5137cb（迁移前记录）",
    "edition": "2026-10-01（迁移前记录）",
    "generated_at": "2026-09-30T23:28:59.968601Z（迁移前记录）",
    "worker_version": "本轮未部署或验收",
    "verified_at": "尚未完成迁移后生产验收"
  },
  "blockers": ["注册商已保存 NS，但 DNS 查询尚未更新；待 Cloudflare active 后绑定 Pages", "本机不存在既有 fomobtc_tokyo_config；阶段 4 服务器部署仍需持有原 SSH 配置的运营者电脑"],
  "next_action": "阶段 2 全绿后合并并部署 --keep-vars，回读 health/ready；新域传播期间显式保留旧公共检查地址，随后顺序导入 realtime 历史",
  "states": {"code": "complete", "tests": "pending", "pr_merged": "pending", "deployed": "pending", "production_verified": "pending"},
  "evidence": "project-docs/releases/2026-10-01-xiyunews-dispatcher.md"
}
```

上轮交付见 [Logo 记录](releases/2026-10-01-brand-v3.md) 与 [Python 安全记录](releases/2026-10-01-security-deps.md)。本轮不改 Logo 图形、不恢复漏洞版本，也不继续历史待办或其他人的 PR。迁移操作见 [运行手册](brand-domain-migration.md)；realtime 尚未并入，因此暂不伪造其交接链接。
