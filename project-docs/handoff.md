# 当前交接

当前在修复品牌验收发现的存量 sitemap/分类 feed XML；阶段 3 继续暂停历史推送。前台品牌和调度器已合并部署，不能将其等同于五阶段迁移全部完成。页面结构、实时规则、来源、数据库和 Telegram 目标未改变。

<!-- execution-pointer -->
```json
{
  "goal": "品牌验收补充：迁移存量 sitemap 与分类订阅 XML；阶段 3 历史迁移继续暂停",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/175",
  "owner": "Codex / 迁移唯一编辑及部署整合负责人",
  "branch": "agent/xiyunews-brand-xml",
  "last_verified_commit": "d12dfb1e355206f462d7e6752989a82dcbb72f3a",
  "pr": "待建立本修复 PR，最终检查与合并以远端为准",
  "completed": [
    "PR169、PR171 全绿后顺序合并；两仓已确认私有，协作者目前均仅 ohxiyu",
    "Dynadot NS 保存并传播；Cloudflare active，xiyu.news 与 www.bmt.news 均已绑定 Pages",
    "xiyu.news HTTPS 首页、中文日报、latest API、RSS、sitemap 和 quick-posts API 均 200，title/canonical 为新域",
    "调度器已部署 dd126dda，health 指新仓和新域，ready 验证 actions:write 与 contents:read",
    "阶段 3 本地 unsquashed subtree 历史、独立 CI、治理和打包准备完毕；未推送",
    "PR174 纯文档已合并，记录实时历史安全阻塞；XML 存量迁移修复已实现，不修改新闻正文"
  ],
  "unfinished": [
    "XML 修复验证、合并、正常发布与实际 sitemap/feed 内容验收",
    "确认旧历史疑似 Telegram Token 已撤销后，才能推送并合并阶段 3",
    "新域既有 Access 保护迁移和登录验收；旧域 301 仍暂停",
    "阶段 4 从运营者原 SSH 电脑部署并验证自然回执，之后才归档旧仓",
    "阶段 5 准备 Telegram 文案并由运营者确认/改名"
  ],
  "validation": [
    "阶段 1–2 完整 929 项 pytest、64 项调度器、22 项后台 Node、类型/治理/dry-run 与远端 CI/Pages 通过",
    "本地 realtime Python 3.11/3.12 各 61 项 pytest、ruff、mypy、compileall、契约和 3 项看门狗 Node 通过；根 929 项重新通过",
    "原阈值、地址簿、requirements.lock、systemd 与 nginx 完整保持；旧 main 是本地导入提交祖先",
    "XML 精确 URL、频道元数据、幂等和无效输入测试执行中，最终结果见 PR"
  ],
  "unverified": [
    "sitemap 与分类 feed 的新域链接/署名，当前存量线上仍有旧值",
    "阶段 3 远端 CI 和合并祖先验证；新仓服务器 SHA 与自然 message_id",
    "新域后台实际登录、Quick Post 管理列表；旧域 301",
    "调度器下一次自然 workflow_dispatch"
  ],
  "production": {
    "source_commit": "d5360740bb571c6bf95d3fcb631a54ac00634e9f",
    "artifact_commit": "a0f1608927767690964ed734b99d74fc8008829d",
    "edition": "2026-10-01",
    "generated_at": "2026-09-30T23:28:59.968601Z",
    "worker_version": "dd126dda-3c13-4e8d-b582-e2550c08cb98（独立调度器）",
    "verified_at": "2026-10-01 06:25 UTC；前台200、调度ready；后台/301/实时新部署未验收"
  },
  "blockers": [
    "旧历史两份已删除 README 含同一疑似 Telegram Token，非明显占位符，未输出或调用，未推入新仓；保留历史前需确认已撤销",
    "本机未找到既有 fomobtc_tokyo_config，原服务器私钥不在此电脑",
    "Access 云端访问配置变更需操作时确认，已提出确认请求，未提交修改"
  ],
  "next_action": "本 XML 修复全绿后合并并等待 Deploy Docs/Pages，线上确认 sitemap loc 与分类 feed title/self/id 新域；此任务完成后只在旧 Token 已撤销确认和 Access 操作确认到达时恢复阶段 3，不误推本地历史。",
  "states": {
    "code": "complete",
    "tests": "pending",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-01-brand-xml.md"
}
```

阶段 3 的本地分支位于 /tmp/xiyunews-stage3，提交 1e6395f3a410233b817ce0c2ddaf9bd64fdf6f78，尚未上传；这是唯一后续编辑入口。旧历史扫描发现疑似凭据，不读取或输出其值；不要推送包含该历史的 agent/xiyunews-realtime、agent/xiyunews-local-history-hold 或旧本地 dispatcher 分支。两个仓库保持私有，历史不擅自重写，不能以私有化替代撤销凭据。

本轮已上线证据见 [迁移交接记录](releases/2026-10-01-migration-handoff.md)，主站配置见 [迁移手册](brand-domain-migration.md)。realtime 文档尚未在远端 main，因此这里只说明本地 realtime/docs/handoff.md 和 realtime/docs/deployment.md，不建立伪造链接。不要继续历史 backlog 或别人的 PR。
