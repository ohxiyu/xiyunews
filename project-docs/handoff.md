# 当前交接

当前任务为 Issue172：继续实时服务历史整合和部署准备。PR182/184/186/188 的既有线上修复保留，20:05 自然到期分发已经成功；阶段 3 完整历史仍只能保存在本地，疑似旧凭据撤销确认、原 SSH 配置和后台验证码登录尚缺。当前五阶段状态只描述未合并部署的阶段 3，不继承前序发布的完成状态。

<!-- execution-pointer -->
```json
{
  "goal": "阶段 3 同步最新 main、保留完整实时历史、完善新仓部署清单；确认旧凭据撤销后才能上传",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/172",
  "owner": "Codex / 迁移唯一编辑及部署整合负责人",
  "branch": "agent/xiyunews-realtime",
  "last_verified_commit": "99594ac28b5918f3192bc62501469bb01c66e802",
  "pr": "本地同步阶段 3；凭据撤销尚未确认，未推送历史、未建立 PR",
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
    "Access 已按操作时确认仅保护新域六路径，原单账号策略与 AUD 不变，匿名入口 302 登录页",
    "PR184 全绿合并并 keep-vars 部署 9774435b；19:00 上海时间自然 Cron 返回采集 fresh、广场 idle、X idle、日报 healthy",
    "公开联系页普通主域 200 且仅使用 X @ohxiyu，旧缓存已自然更新",
    "PR186 全绿合并后 Deploy Docs 36853256492 成功，gh-pages c74d9092 对应生产 Pages 216fd183，正式检查 success",
    "2026-10-01 11:12 UTC 普通新域主入口/日报/API/RSS/sitemap/openapi/llms/contact 200、canonical 新域；旧两域 26 路径全为 410，无 Location 且 no-store",
    "Pages 预览保留包含 * 并排除三状态分支；后续自然采集 36853175538 success，缓存 926e93c0 保留父提交且无 Pages check",
    "系统架构已进入 main，明确现有静态网站、Actions、边缘后台/调度与原实时服务，不把本地 subtree 当成上线",
    "实时完整历史仍保留；阶段 3 已合入最新 main 的网站/调度/许可/旧域停用代码，不回退此前修复",
    "2026-10-01 20:05 上海时间自然 dispatcher 触发 Square 36859488592，成功尝试一条，累计 sent=11、remaining=3、attention=0"
  ],
  "unfinished": [
    "确认旧历史疑似 Telegram Token 已撤销后，同步最新 main、重新测试、推送阶段 3 PR 并用 merge commit 保留历史",
    "阶段 4 从原 SSH 电脑备份、部署、检查新 SHA/三分片/自然回执/看门狗后，才归档旧仓",
    "阶段 5 完成 Telegram 品牌文案和运营者确认；不合并群/频道，不改 fomobtc.com nginx",
    "运营者完成新域验证码后验证 Quick Post；旧域 301 已取消，不再作为迁移验收要求",
    "同步后的完整主项目与 realtime 双 Python 离线验证，再确认未更改阈值、地址簿、systemd、nginx和依赖锁"
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
    "同步后的主/realtime 全量测试正在重新执行；Access 显示名仍待保存确认"
  ],
  "production": {
    "source_commit": "3b8f2b5cd82e257783c99501e6494e495bb20ca7",
    "artifact_commit": "c74d90926376852660aa8b56ab2deb35fc624c9e",
    "edition": "2026-10-01",
    "generated_at": "2026-09-30T23:28:59.968601Z",
    "worker_version": "9774435b-1c72-4dad-9552-0440e2ab574f（独立调度器）；Pages 216fd183-cd53-4140-a744-ff6b48ff1bd6（站点 Worker）",
    "verified_at": "2026-10-01 11:12 UTC；普通主域 200、新 canonical；旧两域 26 路径 410，无跳转"
  },
  "blockers": [
    "旧历史两份已删除 README 含同一疑似 Telegram Token，未输出或调用，未推入新仓；保留历史前需确认已撤销",
    "仅确认两个文档中记载的 fomobtc_tokyo_config 路径不存在，尚不能推断本机没有私钥；原 SSH 配置路径待提供，未尝试不明连接",
    "新域验证码登录待运营者完成，不绕过 Access，不发布生产测试消息"
  ],
  "next_action": "完成本地同步和部署操作清单及验证；等待旧凭据已撤销确认、原 SSH 配置、后台验证码登录。收到撤销确认后同步 main 推送阶段 3，CI 全绿后 merge commit 保留历史，再核对新仓部署。",
  "states": {
    "code": "complete",
    "tests": "pending",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-01-xiyunews-realtime.md"
}
```

阶段 3 的唯一后续编辑入口是 /tmp/xiyunews-stage3，提交 1e6395f3a410233b817ce0c2ddaf9bd64fdf6f78，尚未上传。不要推送包含旧历史的 agent/xiyunews-realtime、agent/xiyunews-local-history-hold 或旧本地 dispatcher 分支，也不要使用 git push --all；两仓私有化不能替代撤销凭据，不擅自重写历史。

实际运行边界见 [系统架构](system-architecture.md)。完整生产证据见 [部署回读记录](releases/2026-10-01-deployment-receipt.md)，步骤见 [域名迁移手册](brand-domain-migration.md)。realtime 文档尚不在远端 main，其入口目前仅在本地 realtime/docs/handoff.md 与 realtime/docs/deployment.md；不建立伪造链接，不继续其他未授权 PR。GitHub 当前私有仓套餐不支持分支保护或 CodeQL，未新增付费服务；合并仍手动核对同步 main、治理和全部可用 CI。
