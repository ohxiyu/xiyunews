# 当前交接

运营者新增授权解决迁移审计发现的全部问题，当前唯一编辑任务为 Issue181：修复私有仓后的公开页面、许可访问及抓取标识，之后按依赖顺序处理调度成本、后台和旧域跳转。阶段 3 的历史安全确认仍不可跳过；阶段 3–5 尚未完成。主站和独立调度器已上线，两仓私有，页面结构、实时阈值、来源、地址簿、数据库、systemd 和 Telegram 目标保持不变。

<!-- execution-pointer -->
```json
{
  "goal": "解决迁移审计发现的问题，当前先修复私有仓后的公开页面与许可访问",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/181",
  "owner": "Codex / 迁移唯一编辑及部署整合负责人",
  "branch": "agent/xiyunews-private-public-pages",
  "last_verified_commit": "d09677fcd7a1ccf0cf9fedac3a4c81c2145a0fe3",
  "pr": "Issue181 实施中；阶段 3 历史仍禁止推送，撤销状态待确认",
  "completed": [
    "阶段 1 PR169 与阶段 2 PR171 顺序全绿合并，主站与调度器已上线；PR174/176/178 后续修复也已合并",
    "ohxiyu/xiyunews 与 ohxiyu/fomobtc 均 private=true、archived=false，协作者仅 ohxiyu；私有 Git 集成 Pages 构建成功",
    "Dynadot NS 已保存并传播，Cloudflare xiyu.news active；新主域和 www.bmt.news 已绑定 Pages",
    "首页、中文日报、latest API、RSS、openapi、llms 等线上 200，title/canonical 是 xiyu.news",
    "PR176 XML 正常 Deploy Docs 与 Pages 成功，14:49 上海时间普通 sitemap 456 个 loc 和全部六个分类 feed 均 200、旧域引用为 0；不重跑 AI",
    "调度器 dd126dda health 指向新仓和新域，ready 的 actions:write 与 contents:read 通过；14:30 自然 workflow_dispatch 实际触发",
    "PR178 缓存修复首次自然采集 36849586444 整体 success，事件发布与缓存持久化步骤均成功，不 force 或扩大权限",
    "阶段 3 本地 unsquashed subtree、独立 CI、治理及新仓打包准备完毕；旧 main 为导入祖先，未上传历史"
  ],
  "unfinished": [
    "确认旧历史疑似 Telegram Token 已撤销后，同步最新 main、重新测试、推送阶段 3 PR 并用 merge commit 保留历史",
    "Access 仅保留新域同样六条路径，按运营者新决定取消旧域入口及 301，验证登录与 Quick Post",
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
    "新域 Access 登录与 Quick Post 管理操作；旧域 301 已被运营者取消，不再作为验收要求",
    "阶段 3 远端 CI、merge commit 历史祖先；服务器新仓完整 SHA、自然 message_id 和看门狗无新增告警",
    "私有仓公开页面修复尚未合并部署；公开联系入口指定 X @ohxiyu，不公布私人联系信息"
  ],
  "production": {
    "source_commit": "d115e7debbf70e8d4dfe6629592f283f5783e746",
    "artifact_commit": "09a14bf7c435a915f911c57e0b5f280331d446a9",
    "edition": "2026-10-01",
    "generated_at": "2026-09-30T23:28:59.968601Z",
    "worker_version": "dd126dda-3c13-4e8d-b582-e2550c08cb98（独立调度器）",
    "verified_at": "2026-10-01 06:49 UTC；主站和全部普通 XML 链接验证，后台/301/实时新部署未验收"
  },
  "blockers": [
    "旧历史两份已删除 README 含同一疑似 Telegram Token，未输出或调用，未推入新仓；保留历史前需确认已撤销",
    "仅确认两个文档中记载的 fomobtc_tokyo_config 路径不存在，尚不能推断本机没有私钥；原 SSH 配置路径待提供，未尝试不明连接",
    "Access 属云端访问权限修改，computer-use 技能要求操作时确认；已请求确认，尚未提交修改"
  ],
  "next_action": "先创建并合并 Issue181 页面修复 PR，通过正常 Actions 发布并回读，再顺序处理调度和后台。公开联系入口只用 X @ohxiyu；Access 按最新确认仅保留新域六路径，不启用旧域 301。旧 Token 撤销和原 SSH 路径已请求提供，不得跳过凭据安全确认。",
  "states": {
    "code": "complete",
    "tests": "complete",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-01-private-public-pages.md"
}
```

阶段 3 的唯一后续编辑入口是 /tmp/xiyunews-stage3，提交 1e6395f3a410233b817ce0c2ddaf9bd64fdf6f78，尚未上传。不要推送包含旧历史的 agent/xiyunews-realtime、agent/xiyunews-local-history-hold 或旧本地 dispatcher 分支，也不要使用 git push --all；两仓私有化不能替代撤销凭据，不擅自重写历史。

完整生产证据见 [部署回读记录](releases/2026-10-01-deployment-receipt.md)，步骤见 [域名迁移手册](brand-domain-migration.md)。realtime 文档尚不在远端 main，其入口目前仅在本地 realtime/docs/handoff.md 与 realtime/docs/deployment.md；不建立伪造链接，不继续其他未授权 PR。GitHub 当前私有仓套餐不支持分支保护或 CodeQL，未新增付费服务；合并仍手动核对同步 main、治理和全部可用 CI。
