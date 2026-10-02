# 当前交接

项目统一名为 `xiyunews`，网页和 Telegram 展示名为 `xiyu.news`。PR195 已将实时服务以 unsquashed subtree 完整历史并入 `realtime/` 并按 merge commit 合并，旧 Token 撤销已获运营者明确确认。当前执行 Issue196 的 Cloudflare 单项目迁移基础；生产仍使用原三个边缘项目，实时服务器仍是旧部署，不将代码合并描述为部署完成。

<!-- execution-pointer -->
```json
{
  "goal": "将网站、日报调度和实时看门狗整合为单个Cloudflare项目xiyunews，先完成安全迁移基础",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/196",
  "owner": "迁移唯一编辑及发布整合负责人",
  "branch": "agent/xiyunews-cloudflare",
  "last_verified_commit": "d6a9d3f29ef93c138842342c973b3049fb7bc252",
  "pr": "https://github.com/ohxiyu/xiyunews/pull/197（Draft；前序PR195已合并）",
  "completed": [
    "PR195以merge commit合并，旧实时main7807126d8c7cdb51e18f0b91ba27f500271f9f08是origin/main祖先，远端realtime目录存在",
    "阶段3主站943项、实时Python3.11/3.12各61项、治理和看门狗3项通过；远端全部可用CI与Pages预览通过，CodeQL因私有套餐跳过",
    "运营者确认旧Bot Token已撤销，完整历史安全上传门槛解除；运营者报告新Bot仍在原频道，频道已改名，不改目标ID",
    "操作时确认后删除bmt.news DNS区域和bmt.news/www.bmt.news/next.bmt.news三个Pages绑定，回读旧区不存在、生产绑定只剩xiyu.news；不删除注册",
    "旧Horizon已删除；bmtnews-standalone仅是同一主仓的旧别名，禁止据此删除主仓",
    "已复用原网站鉴权/API/缓存、调度和看门狗准备新入口xiyunews，默认无Cron且双开关关闭，不修改UI或实时规则",
    "已准备固定出版SHA构建和默认关闭的自动发布工作流，补充真实静态构建CI与免AI部署恢复路径"
  ],
  "unfinished": [
    "本任务远端CI和真实Jekyll/dry-run验证；保留迁移基础PR与准确下一步",
    "安全补齐新Worker配置、最小权限自动部署凭据及原可信SSH入口，取得对应部署/配置授权后完成切换",
    "停旧Cron、迁移原RecoveryGate归属、保持STATE KV、迁域、自然调度与后台验收；最终切换配置须另一个串行PR",
    "服务器按新仓完整SHA重新发布、三现货分片和自然message_id验收后退役旧fomobtc仓库",
    "现有Node开发工具链7项依赖告警需单独修复和复测，未强制升级"
  ],
  "validation": [
    "新入口与原dispatcher共94项边缘测试通过、tsc通过，看门狗3项Node通过",
    "根完整951项Python测试、原后台及公开路由51项Node通过，新增资产8项单独通过；实时3.11的61项/ruff/mypy/compileall/契约通过",
    "新域最新2026-10-02共14条；实时health仍是2.6.0/b226b625cf3875b6693e0768d75d88d50b33c08d，Telegram启用，三个spot分片live",
    "只读取GitHub和Worker Secrets名称；未复制加密值、未新增Token、未改密钥或发真实测试消息"
  ],
  "unverified": [
    "统一Worker真实部署/流量切换/DO迁入及自然调度；当前配置为过渡状态而非最终单项目",
    "新域Access登录后的Quick Post操作、新Bot自然回执和实时群简介",
    "实时新仓服务器部署、进程与SQLite、自然message_id和看门狗两次自然检查"
  ],
  "production": {
    "source_commit": "2858290a6db7ec5f6eb38dc5fd30689bbfa90b14",
    "artifact_commit": "31a0cba37ae643962e26ee4c3d8497e88a0f2e1e",
    "edition": "2026-10-02",
    "generated_at": "2026-10-01T23:29:37.357545Z",
    "worker_version": "调度器9774435b-1c72-4dad-9552-0440e2ab574f；既有Pages07cdba23-711f-4172-92da-1862a24f6e65；统一Worker未部署",
    "verified_at": "2026-10-02，普通latest API与实时health回读；旧区和旧域绑定面板回读"
  },
  "blockers": [
    "原可信SSH配置路径待提供；两个已知路径不存在不代表本机没有私钥，不猜用密钥或关闭指纹校验",
    "现有仓库没有Cloudflare自动部署Secrets和启用变量；旧Worker加密Secrets不可通过名称列表恢复，需运营者既有安全注入方式",
    "Worker部署/密钥/DNS和最终删资源需要对应授权；当前只完成明确确认的旧区与三绑定清理"
  ],
  "next_action": "保存迁移基础PR并完成真实构建CI；安全配置与可信SSH恢复后，用串行切换PR迁移原状态和域名并做自然验收，最后删旧资源，不提前启用双Cron。",
  "states": {
    "code": "pending",
    "tests": "pending",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-02-cloudflare-unified-foundation.md"
}
```

当前唯一编辑工作区是 `/tmp/xiyunews-cloudflare`；前序阶段3合并和历史祖先已有实际证据，不再沿用旧Token待撤销或远端无realtime的说明。总体实际架构见 [系统架构](system-architecture.md)，最终边缘切换顺序见 [单项目清单](cloudflare-single-project.md)，服务器步骤见 [实时服务器迁移](realtime-server-migration.md)，运行和测试入口见 [实时交接](../realtime/docs/handoff.md)。历史 release 保留原样，本指针不授权执行旧 backlog。
