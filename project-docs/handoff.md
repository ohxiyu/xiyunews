# 当前交接

运营者授权解决迁移审计全部问题，当前唯一编辑任务 Issue183：按私有队列到期派发，减少 Actions 空跑。PR182 已合并发布，后台仅保留新域；旧域 301 按最新决定取消。阶段 3 的凭据安全确认和后续实时部署仍不可跳过，不调整来源、阈值、地址簿或 UI 结构。

<!-- execution-pointer -->
```json
{
  "goal": "解决迁移审计问题，当前实施私有分发队列到期门控减少空跑",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/183",
  "owner": "Codex / 迁移唯一编辑及部署整合负责人",
  "branch": "agent/xiyunews-due-dispatch",
  "last_verified_commit": "21c96d4281e1cec771c7516d3722ea6ba6688c62",
  "pr": "Issue183 实施中；PR182 已合并，阶段 3 历史仍禁止推送",
  "completed": [
    "阶段 1 PR169 与阶段 2 PR171 顺序全绿合并，主站与调度器已上线；PR174/176/178 后续修复也已合并",
    "ohxiyu/xiyunews 与 ohxiyu/fomobtc 均 private=true、archived=false，协作者仅 ohxiyu；私有 Git 集成 Pages 构建成功",
    "Dynadot NS 已保存并传播，Cloudflare xiyu.news active；新主域和 www.bmt.news 已绑定 Pages",
    "首页、中文日报、latest API、RSS、openapi、llms 等线上 200，title/canonical 是 xiyu.news",
    "PR176 XML 正常 Deploy Docs 与 Pages 成功，14:49 上海时间普通 sitemap 456 个 loc 和全部六个分类 feed 均 200、旧域引用为 0；不重跑 AI",
    "调度器 dd126dda health 指向新仓和新域，ready 的 actions:write 与 contents:read 通过；14:30 自然 workflow_dispatch 实际触发",
    "PR178 缓存修复首次自然采集 36849586444 整体 success，事件发布与缓存持久化步骤均成功，不 force 或扩大权限",
    "阶段 3 本地 unsquashed subtree、独立 CI、治理及新仓打包准备完毕；旧 main 为导入祖先，未上传历史",
    "PR182 全绿合并并经 Deploy Docs 发布，站内许可入口 200，联系入口仅 X @ohxiyu，不公开私人信息",
    "Access 已按操作时确认仅保护新域六路径，原单账号策略与 AUD 不变，匿名入口 302 登录页"
  ],
  "unfinished": [
    "确认旧历史疑似 Telegram Token 已撤销后，同步最新 main、重新测试、推送阶段 3 PR 并用 merge commit 保留历史",
    "阶段 4 从原 SSH 电脑备份、部署、检查新 SHA/三分片/自然回执/看门狗后，才归档旧仓",
    "阶段 5 完成 Telegram 品牌文案和运营者确认；不合并群/频道，不改 fomobtc.com nginx",
    "运营者完成新域验证码后验证 Quick Post；旧域 301 已取消，不再作为迁移验收要求",
    "Issue183 同步 main、全绿合并、keep-vars 部署与真实 idle/到期回读"
  ],
  "validation": [
    "主仓最新修复完整 937 项 pytest、治理、6 项真实本地裸仓缓存回归、bash 语法与 diff 检查通过；远端 CI 和 Pages 预览成功",
    "独立调度器 64 项测试、类型检查/dry-run、22 项后台 Node 和跳转测试已通过",
    "本地阶段 3 Python 3.11/3.12 各 61 项 pytest，ruff、mypy、compileall、治理、3 项看门狗 Node 通过；当时根 929 项通过，合并最新 main 后须再跑",
    "实时阈值、地址簿、requirements.lock、systemd、nginx 与原仓对应文件逐字一致；未真实调用 AI、X、Telegram 作为测试",
    "本阶段完整 942 项 pytest、84 项 Worker 测试、绑定类型、tsc 和 dry-run 通过"
  ],
  "unverified": [
    "新域 Access 登录与 Quick Post 管理操作；旧域 301 已被运营者取消，不再作为验收要求",
    "阶段 3 远端 CI、merge commit 历史祖先；服务器新仓完整 SHA、自然 message_id 和看门狗无新增告警",
    "本阶段调度尚未合并部署；公开联系页普通主域缓存更新后回读"
  ],
  "production": {
    "source_commit": "21c96d4281e1cec771c7516d3722ea6ba6688c62",
    "artifact_commit": "d4958131d9066268eef025fb07f912b25ea2b54a",
    "edition": "2026-10-01",
    "generated_at": "2026-09-30T23:28:59.968601Z",
    "worker_version": "dd126dda-3c13-4e8d-b582-e2550c08cb98（独立调度器）",
    "verified_at": "2026-10-01 10:51 UTC；Pages 与 Actions success，普通许可 200，Access 匿名登录验证"
  },
  "blockers": [
    "旧历史两份已删除 README 含同一疑似 Telegram Token，未输出或调用，未推入新仓；保留历史前需确认已撤销",
    "仅确认两个文档中记载的 fomobtc_tokyo_config 路径不存在，尚不能推断本机没有私钥；原 SSH 配置路径待提供，未尝试不明连接",
    "新域验证码登录待运营者完成，不绕过 Access，不发布生产测试消息"
  ],
  "next_action": "完成 Issue183 治理与远端 CI，同步 main 合并后 keep-vars 部署，检查真实 idle/到期派发；回读 PR182 普通主域。旧 Token 撤销和原 SSH 路径仍待提供，不能跳过历史安全确认；旧域 301 取消。",
  "states": {
    "code": "complete",
    "tests": "complete",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-01-due-dispatch.md"
}
```

阶段 3 的唯一后续编辑入口是 /tmp/xiyunews-stage3，提交 1e6395f3a410233b817ce0c2ddaf9bd64fdf6f78，尚未上传。不要推送包含旧历史的 agent/xiyunews-realtime、agent/xiyunews-local-history-hold 或旧本地 dispatcher 分支，也不要使用 git push --all；两仓私有化不能替代撤销凭据，不擅自重写历史。

完整生产证据见 [部署回读记录](releases/2026-10-01-deployment-receipt.md)，步骤见 [域名迁移手册](brand-domain-migration.md)。realtime 文档尚不在远端 main，其入口目前仅在本地 realtime/docs/handoff.md 与 realtime/docs/deployment.md；不建立伪造链接，不继续其他未授权 PR。GitHub 当前私有仓套餐不支持分支保护或 CodeQL，未新增付费服务；合并仍手动核对同步 main、治理和全部可用 CI。
