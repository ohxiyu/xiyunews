# 当前交接

当前唯一下一步是阶段 3 的历史安全确认，而不是重新修改网站或继续其他 backlog。主站 https://xiyu.news 和独立调度器已经上线，两仓均为私有；阶段 3–5 尚未完成，旧域 301 和新域后台登录也仍待验收。页面结构、实时阈值、来源、地址簿、数据库、systemd 和 Telegram 目标保持不变。

<!-- execution-pointer -->
```json
{
  "goal": "稀有News 迁移阶段 3：安全确认后并入 realtime 完整历史；其余未完成项按依赖推进",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/172",
  "owner": "Codex / 迁移唯一编辑及部署整合负责人",
  "branch": "agent/xiyunews-realtime",
  "last_verified_commit": "1e6395f3a410233b817ce0c2ddaf9bd64fdf6f78",
  "pr": "未上传阶段 3 PR；历史疑似凭据撤销状态未确认，禁止推送历史",
  "completed": [
    "阶段 1 PR169 与阶段 2 PR171 顺序全绿合并，主站与调度器已上线；PR174/176/178 后续修复也已合并",
    "ohxiyu/xiyunews 与 ohxiyu/fomobtc 均 private=true、archived=false，协作者仅 ohxiyu；私有 Git 集成 Pages 构建成功",
    "Dynadot NS 已保存并传播，Cloudflare xiyu.news active；新主域和 www.bmt.news 已绑定 Pages",
    "首页、中文日报、latest API、RSS、openapi、llms 等线上 200，title/canonical 是 xiyu.news",
    "PR176 XML 正常 Deploy Docs 与 Pages 成功，产物 sitemap 的 456 个 loc 和分类 feed 元数据已迁移新域；不重跑 AI",
    "调度器 dd126dda health 指向新仓和新域，ready 的 actions:write 与 contents:read 通过；14:30 自然 workflow_dispatch 实际触发",
    "自然采集运行的采集/事件发布成功但缓存推送失败；PR178 修复为保留缓存父历史的仅数据提交，不 force 或扩大权限",
    "阶段 3 本地 unsquashed subtree、独立 CI、治理及新仓打包准备完毕；旧 main 为导入祖先，未上传历史"
  ],
  "unfinished": [
    "确认旧历史疑似 Telegram Token 已撤销后，同步最新 main、重新测试、推送阶段 3 PR 并用 merge commit 保留历史",
    "新域增加既有 Access 保护的同样六条路径并验证登录和 Quick Post；之后才开启旧域 301",
    "等待缓存修复后的首次自然运行成功，不能把调度触发或离线测试当作全链路成功",
    "阶段 4 从原 SSH 电脑备份、部署、检查新 SHA/三分片/自然回执/看门狗后，才归档旧仓",
    "阶段 5 完成 Telegram 品牌文案和运营者确认；不合并群/频道，不改 fomobtc.com nginx"
  ],
  "validation": [
    "主仓最新修复完整 937 项 pytest、治理、6 项真实本地裸仓缓存回归、bash 语法与 diff 检查通过；远端 CI 和 Pages 预览成功",
    "独立调度器 64 项测试、类型检查/dry-run、22 项后台 Node 和跳转测试已通过",
    "本地阶段 3 Python 3.11/3.12 各 61 项 pytest，ruff、mypy、compileall、治理、3 项看门狗 Node 通过；当时根 929 项通过，合并最新 main 后须再跑",
    "实时阈值、地址簿、requirements.lock、systemd、nginx 与原仓对应文件逐字一致；未真实调用 AI、X、Telegram 作为测试"
  ],
  "unverified": [
    "XML 普通无查询链接的旧边缘缓存过期后的最终回读；新部署带校验查询和部署地址均已是新品牌",
    "新域 Access 登录、Quick Post 管理操作与旧域各类路径 301",
    "阶段 3 远端 CI、merge commit 历史祖先；服务器新仓完整 SHA、自然 message_id 和看门狗无新增告警",
    "缓存修复后下一次自然运行成功持久化；现有运行 36825148528 整体 failure，不能标 success"
  ],
  "production": {
    "source_commit": "d115e7debbf70e8d4dfe6629592f283f5783e746",
    "artifact_commit": "09a14bf7c435a915f911c57e0b5f280331d446a9",
    "edition": "2026-10-01",
    "generated_at": "2026-09-30T23:28:59.968601Z",
    "worker_version": "dd126dda-3c13-4e8d-b582-e2550c08cb98（独立调度器）",
    "verified_at": "2026-10-01 06:43 UTC；主站与新部署 XML 验证，后台/301/实时新部署未验收"
  },
  "blockers": [
    "旧历史两份已删除 README 含同一疑似 Telegram Token，未输出或调用，未推入新仓；保留历史前需确认已撤销",
    "本机未找到既有 fomobtc_tokyo_config，原服务器私钥不在此电脑，未尝试 SSH 部署",
    "Access 属云端访问权限修改，computer-use 技能要求操作时确认；已请求确认，尚未提交修改"
  ],
  "next_action": "先等待运营者确认旧 Token 已撤销，再在 /tmp/xiyunews-stage3 同步 origin/main 并重新验证；阶段 3 用 merge commit，不 squash/rebase。Access 确认后保留原策略追加新域六路径，登录验收后开启旧域跳转。服务器部署须使用原 SSH 电脑，三阶段依赖不得跳过。",
  "states": {
    "code": "complete",
    "tests": "complete",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-01-deployment-receipt.md"
}
```

阶段 3 的唯一后续编辑入口是 /tmp/xiyunews-stage3，提交 1e6395f3a410233b817ce0c2ddaf9bd64fdf6f78，尚未上传。不要推送包含旧历史的 agent/xiyunews-realtime、agent/xiyunews-local-history-hold 或旧本地 dispatcher 分支，也不要使用 git push --all；两仓私有化不能替代撤销凭据，不擅自重写历史。

完整生产证据见 [部署回读记录](releases/2026-10-01-deployment-receipt.md)，步骤见 [域名迁移手册](brand-domain-migration.md)。realtime 文档尚不在远端 main，其入口目前仅在本地 realtime/docs/handoff.md 与 realtime/docs/deployment.md；不建立伪造链接，不继续其他未授权 PR。GitHub 当前私有仓套餐不支持分支保护或 CodeQL，未新增付费服务；合并仍手动核对同步 main、治理和全部可用 CI。
