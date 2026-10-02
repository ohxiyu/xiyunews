# 当前交接

项目统一名为 `xiyunews`，网页展示名为 `xiyu.news`，Telegram名称按运营者报告已调整。PR195 已将实时服务以 unsquashed subtree 完整历史并入 `realtime/` 并按 merge commit 合并，旧 Token 撤销已获运营者明确确认。当前执行 Issue196 的 Cloudflare 单项目迁移基础；生产仍使用原三个边缘项目。实时服务器已于2026-10-02切换到新仓d6a9d3f完整SHA，三现货分片live，但自然推送被Telegram拒绝，不能写成业务验收完成。

<!-- execution-pointer -->
```json
{
  "goal": "将网站、日报调度和实时看门狗整合为单个Cloudflare项目xiyunews，先完成安全迁移基础",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/196",
  "owner": "迁移唯一编辑及发布整合负责人",
  "branch": "agent/xiyunews-cloudflare",
  "last_verified_commit": "02600b04020a79cc1e13355c42064cdc8aa35cc8",
  "pr": "https://github.com/ohxiyu/xiyunews/pull/197（Draft；前序PR195已合并）",
  "completed": [
    "PR195以merge commit合并，旧实时main7807126d8c7cdb51e18f0b91ba27f500271f9f08是origin/main祖先，远端realtime目录存在",
    "阶段3主站943项、实时Python3.11/3.12各61项、治理和看门狗3项通过；远端全部可用CI与Pages预览通过，CodeQL因私有套餐跳过",
    "运营者确认旧Bot Token已撤销，完整历史安全上传门槛解除；运营者报告新Bot仍在原频道，频道已改名，不改目标ID",
    "操作时确认后删除bmt.news DNS区域和bmt.news/www.bmt.news/next.bmt.news三个Pages绑定，回读旧区不存在、生产绑定只剩xiyu.news；不删除注册",
    "旧Horizon已删除；bmtnews-standalone仅是同一主仓的旧别名，禁止据此删除主仓",
    "已复用原网站鉴权/API/缓存、调度和看门狗准备新入口xiyunews，默认无Cron且双开关关闭，不修改UI或实时规则",
    "已准备固定出版SHA构建和默认关闭的自动发布工作流，补充真实静态构建CI与免AI部署恢复路径",
    "PR197的a7a4fe76全部可用远端检查通过：真实Jekyll渲染/资产校验/统一Worker dry-run、治理、主站和实时双版本；CodeQL跳过，未部署",
    "GitHub主仓名xiyunews、描述统一稀有News及实时快讯、主页链接改为https://xiyu.news，private保持true",
    "在同一Issue196/PR197独立提交工具链安全修复：Vitest4.1.11、Wrangler4.131.0、配套类型、Undici7.29.1/Sharp0.35.4覆盖；完整npm audit从7项到0，94项边缘回归通过",
    "统一自动部署仅允许main手动派发或可信main出版成功；部署前执行完整审计，新增两项离线门槛回归，纠正服务器清单仍称历史未合并的过时说明",
    "02600b04全部可用远端CI与Pages预览通过，CodeQL因私有套餐跳过；仍未生产切换",
    "运营者操作时确认后创建本机xiyunews专用SSH密钥；通过已登录阿里云核对主机指纹并追加公钥，保留原两把公钥及服务器备份；19:55严格指纹SSH登录与sudo -n验证成功，该连接恢复步骤未重启服务",
    "按此前服务器部署授权，20:01:45切换到新仓合并d6a9d3f29ef93c138842342c973b3049fb7bc252；独立venv哈希安装、pip check和停机SQLite备份通过，仅改SOURCE_COMMIT，原release保留；新MainPID233683/NRestarts0，三现货分片live"
  ],
  "unfinished": [
    "迁移基础PR保留Draft，最终域名/状态/Cron切换尚未实施，不能把全绿dry-run当成生产",
    "通过安全渠道补齐新Worker配置及最小权限自动部署凭据；可信SSH入口已恢复，不再等待旧配置路径",
    "停旧Cron、迁移原RecoveryGate归属、保持STATE KV、迁域、自然调度与后台验收；最终切换配置须另一个串行PR",
    "实时新仓版本已部署，仍需解决自然Telegram拒绝并取得message_id、看门狗自然验收后退役旧fomobtc仓库；不补发失败消息",
    "本轮连接交接文档提交后核验其远端CI；基础仍默认关闭，不能据此启用新Cron或删除现役服务"
  ],
  "validation": [
    "新入口与原dispatcher共94项边缘测试通过、tsc通过，看门狗3项Node通过",
    "本轮根完整953项Python测试通过、治理与实时契约通过；原后台及公开路由51项Node通过，资产及发布门槛10项单独通过；实时3.11的61项/ruff/mypy/compileall基线通过",
    "今日网页此前回读2026-10-02共14条；实时health现为2.6.0/d6a9d3f29ef93c138842342c973b3049fb7bc252，Telegram启用，三个spot分片live，既有Hyperliquid degraded未隐藏",
    "只读取GitHub和Worker Secrets名称；未复制加密值或新增Token，SSH公钥已按明确授权追加，业务密钥未变化，未发真实测试消息",
    "Vitest4.1.11与原Cloudflare测试池兼容：94项通过，完整审计0、types:check/tsc/原Wrangler dry-run通过；新增资产与发布门槛共10项、后台公开路由51项、看门狗3项通过",
    "2026-10-02 19:55上海时间：专用SSH以admin登录、sudo -n成功；原两公钥与新公钥均存在，目录0700和文件0600；当时旧服务未重启；随后服务器版本切换证据另记",
    "部署后首条自然行情price_notice为telegram_rejected、telegram_id为空；getMe200且Bot有效，目标为只读话题群，但getChatMember返回member而非administrator；迁移前已有43条同类失败，不把开关开启当送达。主站953项、实时61项与ruff/mypy、治理和看门狗3项复测通过"
  ],
  "unverified": [
    "统一Worker真实部署/流量切换/DO迁入及自然调度；当前配置为过渡状态而非最终单项目",
    "新域Access登录后的Quick Post操作、新Bot自然回执和实时群简介",
    "实时自然message_id、手机收件和看门狗两次自然检查；新仓服务器SHA、进程和备份已经验证，不再列为未执行"
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
    "现有仓库没有Cloudflare自动部署Secrets和启用变量；旧Worker加密Secrets不可通过名称列表恢复，需运营者既有安全注入方式",
    "实时Bot有效但在只读群中仅为member，目标消息被拒绝；恢复管理员发消息权限需群管理员操作或针对该权限变更确认，不能改目标群或盲目重发",
    "SSH新增持久访问已经操作时确认并完成；Cloudflare新增持久权限、秘密值注入及后续浏览器删除仍须各自安全流程，不从SSH确认扩大权限，不重复询问已完成旧区与三绑定删除"
  ],
  "next_action": "提交SSH及服务器部署证据并核验PR197当前head检查；请求运营者恢复实时Bot在原只读群的管理员发消息权限，再观察新的自然回执，不补发失败/未知消息。保留Draft等待Cloudflare安全配置；边缘缺口补齐后按串行切换PR迁移状态和域名，自然验收后再退役旧资源，不双Cron。",
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
