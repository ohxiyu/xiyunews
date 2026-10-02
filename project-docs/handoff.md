# 当前交接

当前任务为运营者 2026-10-02 授权的旧资源清理 Issue193，不继续未经安全条件确认的历史上传。停用 Horizon Pages 已删除并回读，新站与现役调度、实时服务保留；旧域绑定与 DNS 区域已核验，浏览器删除等待操作时确认。运营者报告 Bot 已换且原频道已改名，但旧 Token 撤销尚未确认；不把换 Bot 当作撤销，不删除仍承担生产与恢复职责的旧 FomoBTC 仓、看门狗或域名。当前交接是唯一执行入口，历史阶段 3 作为后续依赖保留，不改提醒规则、账号权限或 UI。

<!-- execution-pointer -->
```json
{
  "goal": "清理已验证停用的旧资源，保留新站与实时生产依赖，准确记录 Telegram 更换及未完成迁移",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/193",
  "owner": "Codex / 迁移唯一编辑及部署整合负责人",
  "branch": "agent/legacy-resource-cleanup",
  "last_verified_commit": "ea2b43a9987dab1b61912e3e227548cfb798540c",
  "pr": "https://github.com/ohxiyu/xiyunews/pull/194；远端检查中，不包含阶段3完整历史或服务器部署",
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
    "20:05 Square 36859488592 workflow_dispatch success，真实新回执 372593244617888；attempted=1、sent=11、remaining=3、attention=0",
    "本地实时分支同步 main 并补齐操作清单，保存 a7edea4b1edfa34ba5fdb7abc3502ca3c1b873fc，完整历史仍未上传",
    "服务器迁移清单、Telegram 品牌草案写入主仓文档任务；命令语法验证通过，未执行服务器或社交变更",
    "运营者于 2026-10-01 确认 Telegram 展示名为 xiyu.news；2026-10-02 报告 Bot 已换且沿用原频道，频道已改名，未独立读取身份或自然回执",
    "本次核验生产Pages bmtnews与日报调度器均仍在用；旧bmtnews-standalone仅重定向同一主仓，不是可删除副本",
    "停用Horizon Pages无自定义域与现役依赖，保存配置及首页快照后删除horizon-ohxiyu，项目列表确认不存在；备份不含全部部署历史",
    "旧bmt.news区域仅三条CNAME，xiyu.news自身DNS独立；三个旧绑定与区域尚未删除，等待操作时确认",
    "原实时2.6.0首次三现货分片live、随后第三分片warming；旧仓、watchdog、fomobtc.com与API均仍有生产或恢复依赖，继续保留"
  ],
  "unfinished": [
    "操作时确认后删除bmt.news、www.bmt.news、next.bmt.news的Pages绑定与旧DNS区域，再回读新站和项目身份",
    "确认旧历史疑似 Telegram Token 已撤销后恢复Issue172，同步最新 main、重新测试、推送阶段 3 PR 并用 merge commit 保留历史",
    "阶段 4 从原 SSH 电脑备份、部署、检查新 SHA/三分片/自然回执/看门狗后，才归档旧仓",
    "频道改名已由运营者报告完成，不重复操作；简介、实时群实际元数据、看门狗标题和新Bot自然回执仍需验收，不合并群/频道，不改nginx",
    "运营者完成新域验证码后验证 Quick Post；旧域 301 已取消，不再作为迁移验收要求"
  ],
  "validation": [
    "主仓最新修复完整 937 项 pytest、治理、6 项真实本地裸仓缓存回归、bash 语法与 diff 检查通过；远端 CI 和 Pages 预览成功",
    "独立调度器 64 项测试、类型检查/dry-run、22 项后台 Node 和跳转测试已通过",
    "本地阶段 3 Python 3.11/3.12 各 61 项 pytest，ruff、mypy、compileall、治理、3 项看门狗 Node 通过；当时根 929 项通过，合并最新 main 后须再跑",
    "实时阈值、地址簿、requirements.lock、systemd、nginx 与原仓对应文件逐字一致；未真实调用 AI、X、Telegram 作为测试",
    "本阶段完整 942 项 pytest、84 项 Worker 测试、绑定类型、tsc 和 dry-run 通过",
    "同步后的 root 942 项和 realtime Python3.11/3.12 各 61 项、ruff/mypy/compileall/仓库契约/看门狗 3 项通过；8 个迁移 Bash 块及嵌入 Python 语法通过",
    "本次旧项目列表回读成功、新域latest为2026-10-02且14条、调度器指向新仓新域；实时首次三分片live、随后第三分片warming，不作为持续就绪验收",
    "编辑前942项pytest通过，编辑后品牌扫描内部资源文档导致1项失败；修正内部与公开边界并新增回归后完整943项、治理和diff检查通过，精确changed-range与远端检查随PR核验"
  ],
  "unverified": [
    "新域 Access 登录与 Quick Post 管理操作；旧域 301 已被运营者取消，不再作为验收要求",
    "阶段 3 远端 CI、merge commit 历史祖先；服务器新仓完整 SHA、自然 message_id 和看门狗无新增告警",
    "Access 应用显示名修改仍待操作时确认；旧域最终删除、新Bot自然回执、实时群资料及简介未独立核验"
  ],
  "production": {
    "source_commit": "2858290a6db7ec5f6eb38dc5fd30689bbfa90b14",
    "artifact_commit": "31a0cba37ae643962e26ee4c3d8497e88a0f2e1e",
    "edition": "2026-10-02",
    "generated_at": "2026-10-01T23:29:37.357545Z",
    "worker_version": "调度器9774435b-1c72-4dad-9552-0440e2ab574f；生产Pages07cdba23-711f-4172-92da-1862a24f6e65；本次未部署Worker",
    "verified_at": "2026-10-02，旧Horizon删除后项目列表、普通新域API、调度与实时健康分别回读"
  },
  "blockers": [
    "浏览器删除须操作时确认，已询问三个旧域绑定与bmt.news区域的精确范围，尚未收到回复",
    "旧历史两份已删除 README 含同一疑似 Telegram Token，未输出或调用，未推入新仓；保留历史前需确认已撤销，换Bot不能替代撤销",
    "仅确认两个文档中记载的 fomobtc_tokyo_config 路径不存在，尚不能推断本机没有私钥；原 SSH 配置路径待提供，未尝试不明连接",
    "新域验证码登录待运营者完成，不绕过 Access，不发布生产测试消息"
  ],
  "next_action": "先完成本次清理文档PR的同步、治理与远端检查；收到操作时删除确认后仅清理三个旧域绑定与bmt.news区域并回读，再通过文档PR记录结果。保留旧Fomo仓和看门狗；确认旧Token已撤销后才恢复Issue172的历史整合，原可信SSH入口恢复后才服务器备份部署。不重复改已改名频道，不改提醒规则或发生产测试消息。",
  "states": {
    "code": "complete",
    "tests": "complete",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-02-legacy-resource-cleanup.md"
}
```

本任务唯一编辑入口为 `/tmp/xiyunews-stage2`、分支 `agent/legacy-resource-cleanup`，只修改过程文档。精确资源身份、删除结果和恢复限制见 [旧资源清单](legacy-resources.md)。文档通过并合并不代表旧域删除、历史导入或服务器发布全部完成。

阶段 3 为后续依赖 [Issue172](https://github.com/ohxiyu/xiyunews/issues/172)，唯一后续编辑入口是 /tmp/xiyunews-stage3，提交 a7edea4b1edfa34ba5fdb7abc3502ca3c1b873fc，尚未上传。不要推送包含旧历史的 agent/xiyunews-realtime、agent/xiyunews-local-history-hold 或旧本地 dispatcher 分支，也不要使用 git push --all；两仓私有化不能替代撤销凭据，不擅自重写历史。

实际运行边界见 [系统架构](system-architecture.md)，逐条命令见 [服务器迁移清单](realtime-server-migration.md)，确认文案见 [Telegram 品牌草案](telegram-brand-migration.md)。完整生产证据见 [部署回读记录](releases/2026-10-01-deployment-receipt.md)，步骤见 [域名迁移手册](brand-domain-migration.md)。realtime 文档尚不在远端 main，其入口目前仅在本地 realtime/docs/handoff.md 与 realtime/docs/deployment.md；不建立伪造链接，不继续其他未授权 PR。GitHub 当前私有仓套餐不支持分支保护或 CodeQL，未新增付费服务；合并仍手动核对同步 main、治理和全部可用 CI。
