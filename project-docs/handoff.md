# 当前交接

项目统一名为 `xiyunews`，网页展示名为 `xiyu.news`。PR195 已保留完整实时历史，PR197 的迁移基础于 2026-10-02 23:09:10（上海时间）合并为 91fb5981；当前串行执行 Issue198 的生产接管，生产仍由原三个 Cloudflare 项目承担，独立 xiyunews 暂停预览已部署为8b365058。2026-10-03 00:31已通过运营者隐藏输入保存两个仓库部署Secret并回读名称/更新时间，自动发布开关仍未启用；后续单仓库GitHub运行Token已按具体确认提交生成，秘密值未读，待隐藏输入保存。实时服务器运行新仓 d6a9d3f 完整 SHA，@xiyunewsbot 在原话题 3/5/7 最新已核验30条自然成功回执，群名为xiyu.news。API回执、手机收件和看门狗私聊实际告警分别验收，不提前删除现役项目。

<!-- execution-pointer -->
```json
{
  "goal": "完成xiyunews单个Cloudflare项目生产接管及剩余品牌统一，保留状态、单调度和后台权限",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/198",
  "owner": "迁移唯一编辑及发布整合负责人",
  "branch": "agent/xiyunews-edge-cutover",
  "last_verified_commit": "4668f4d63437f95d445072bba38f63ce8663f35f",
  "pr": "https://github.com/ohxiyu/xiyunews/pull/199（Draft，生产配置与验收未完成；前序PR197已合并）",
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
    "按此前服务器部署授权，20:01:45切换到新仓合并d6a9d3f29ef93c138842342c973b3049fb7bc252；独立venv哈希安装、pip check和停机SQLite备份通过，仅改SOURCE_COMMIT，原release保留；当时MainPID233683/NRestarts0，三现货分片live",
    "运营者明确指定@xiyunewsbot、确认已为管理员并要求保留原话题，通过本机隐藏输入提供Token；21:03:05配置备份和单服务重启，21:03:11现役看门狗Secret Change发布，保留原ALERT_CHAT_ID/Cron/KV，无测试消息或历史补发",
    "运营者报告已向新Bot发送/start；21:24核验新Bot收到切换后私聊/start且私聊可读取，不再要求重复/start；没有发测试消息，未取得实际告警送达证明",
    "32a838fb的CI37012988502全部可用检查与Pages预览成功，CodeQL跳过；新Bot切换后11条自然事件sent、最新telegram_id1251，覆盖行情/公告/资金流向，原群话题和配置未改",
    "99d2465e的CI37024644728全部可用检查和Pages预览成功，CodeQL跳过；PR197正常merge为91fb5981并删除任务分支，Issue196基础任务关闭，生产接管转Issue198",
    "运营者确认继续配置后，2026-10-03按原摘要提交Cloudflare令牌创建按钮：仅现役账户Workers Scripts编辑、2027-01-01到期，无DNS/Access/账单权限，创建后的页面和令牌值未读取。初次GitHub校验失败，修订工具后运营者预检成功并隐藏输入配置；回读CLOUDFLARE_ACCOUNT_ID更新于2026-10-02T16:31:00Z、CLOUDFLARE_API_TOKEN更新于16:31:01Z，仅验证名称/时间，未启用自动发布",
    "已准备统一项目启用后使用正式域协调接口；迁移前默认旧端点，新端点失败不回退补发，两条自动调用工作流共享同一启用变量",
    "本阶段主站968项和治理通过，实时61项/契约与看门狗3项通过；用Ruby3.3构建233597f8出版快照并校验8364个资产，统一Wrangler dry-run成功，无实际部署",
    "按运营者既有Telegram名称确认，核对新Bot管理员及can_change_info权限后仅把原群xiyuNews改为xiyu.news；2026-10-02T15:22:48Z回读名称正确，简介和话题保持，没有改变权限/规则或手工发送测试消息",
    "2026-10-03运营者完成GitHub Mobile并具体确认后提交单仓库运行Token生成，未读取秘密页面；隐藏输入工具19项离线回归和实际只读预检通过，真实配置待运营者执行",
    "统一暂停预览8b365058-fc4b-46db-9a52-0bc3e156f81b实际部署，main91fb5981和出版aa09cbc8固定SHA、8528资产；公网health确认两个开关false，首页/API/RSS/sitemap/PWA200、404正常，后台缺配置503闭锁；不接管主域或启动Cron"
  ],
  "unfinished": [
    "基础PR已合并，暂停预览8b365058已部署；最终域名/状态/Cron切换尚未实施，不能把预览健康当成生产",
    "GitHub自动部署凭据已配置，仍须安全补齐统一Worker业务运行Secret；可信SSH入口已恢复，不再等待旧配置路径或重复创建部署Token",
    "停旧Cron、迁移原RecoveryGate归属、保持STATE KV、迁域、自然调度与后台验收；最终切换配置须另一个串行PR",
    "实时新仓版本及新Bot已部署并取得三类自然回执；手机收件和看门狗实际私聊告警仍未独立验收，不补发失败消息、不提前删除恢复资源",
    "本阶段PR199仍Draft；已选择新项目受控transfer路径并部署独立暂停入口，不再把旧项目改为已占用的xiyunews同名；仍不能启用新Cron或删除现役服务"
  ],
  "validation": [
    "4668f4d6本机完整980项/治理通过，CI37034229414全部可用检查及Pages预览40613c7a通过，CodeQL跳过；部署Secret只读名称/更新时间已确认，XIYUNEWS_EDGE_ENABLED不存在",
    "2ebb1b9c的CI37036099831全部可用检查及Pages5cbda61a通过，CodeQL跳过；新运行工具19项通过、根999项全量/治理/diff通过，--check-only实际通过；暂停预览latest为2026-10-03、14条、generated_at2026-10-02T23:29:27.197755Z，canonical为xiyu.news；本次远端CI结果待补",
    "2026-10-03只读核验：原dispatcher仍是9774435b-1c72-4dad-9552-0440e2ab574f，三运行Secret名称保留；第一次版本列表网络失败后只读重试成功，没有部署。主域latest仍2026-10-02共14条（此时未到新日07:26），服务器active/MainPID235825/NRestarts0、新Bot管理员、话题3/5/7和群名未变；自然事件30sent/14archived，最新资金1271、公告1270、行情1269，无切换后失败状态",
    "新入口与原dispatcher共94项边缘测试通过、tsc通过，看门狗3项Node通过",
    "本轮根完整953项Python测试通过、治理与实时契约通过；原后台及公开路由51项Node通过，资产及发布门槛10项单独通过；实时3.11的61项/ruff/mypy/compileall基线通过",
    "今日网页此前回读2026-10-02共14条；实时health现为2.6.0/d6a9d3f29ef93c138842342c973b3049fb7bc252，Telegram启用，三个spot分片live，既有Hyperliquid degraded未隐藏",
    "SSH恢复和新仓版本迁移时只读取GitHub和Worker Secrets名称；当时未复制加密值或更换业务密钥，后续21:03按单独确认切换Bot；全部阶段均未发真实测试消息",
    "Vitest4.1.11与原Cloudflare测试池兼容：94项通过，完整审计0、types:check/tsc/原Wrangler dry-run通过；新增资产与发布门槛共10项、后台公开路由51项、看门狗3项通过",
    "2026-10-02 19:55上海时间：专用SSH以admin登录、sudo -n成功；原两公钥与新公钥均存在，目录0700和文件0600；当时旧服务未重启；随后服务器版本切换证据另记",
    "部署后首条自然行情price_notice为telegram_rejected、telegram_id为空；getMe200且Bot有效，目标为只读话题群，但getChatMember返回member而非administrator；迁移前已有43条同类失败，不把开关开启当送达。主站953项、实时61项与ruff/mypy、治理和看门狗3项复测通过",
    "8dad631f远端全部可用CI和Pages预览通过，CodeQL跳过；现役看门狗20:10:23和20:15:23两轮自然Cron均outcome=ok，但不覆盖Bot群权限；20:15最终公网新仓SHA与三个spot分片live再次确认",
    "a54665c5的CI37005750396与Pages预览全部可用检查成功，CodeQL跳过；21:06只读getMe为xiyunewsbot、getChatMember为administrator，进程Token与配置一致，排除Token后全部配置与切换备份相同；MainPID235825/NRestarts0、三spot分片live，watchdog版本a5330597-ee57-4a61-91f0-9a34cb431676，KV无告警；该时点没有切换后新事件",
    "新看门狗版本计划21:10:23的真实Cron于21:10:32.765执行，outcome=ok、日志watchdog: ok、exceptions为空；21:11服务配置和管理员身份再次通过，备份0700/0600、SQLite integrity_check=ok；本轮根完整Python回归、治理、实时61项和实时契约通过",
    "358807bc的CI37011428036与Pages预览全部可用检查成功，CodeQL跳过；第二轮新看门狗计划21:15:23、实际21:15:37.068也ok；21:24新Bot私聊/start与私聊可访问已核验，原群管理员和话题3/5/7未变，当时尚无切换后新自然事件",
    "后续只读SQLite验收：切换后11条sent、6条按规则archived，无失败记录；最新自然行情1251、Bitget公告1250、资金流向1249；MainPID235825/NRestarts0、Token仅在服务器进程内使用，原话题3/5/7不变"
  ],
  "unverified": [
    "统一Worker暂停预览已实际部署，生产流量切换/DO迁入及自然调度未验收；当前配置为过渡状态而非最终单项目",
    "新域Access登录后的Quick Post操作、实时群建议简介尚未确认，不擅自更改",
    "手机收件、看门狗实际告警送达；自然message_id已核验，私聊/start也已核验，但未把其chat.id与加密ALERT_CHAT_ID直接比对，未发送测试告警"
  ],
  "production": {
    "source_commit": "2858290a6db7ec5f6eb38dc5fd30689bbfa90b14",
    "artifact_commit": "31a0cba37ae643962e26ee4c3d8497e88a0f2e1e",
    "edition": "2026-10-02",
    "generated_at": "2026-10-01T23:29:37.357545Z",
    "worker_version": "现生产调度器9774435b-1c72-4dad-9552-0440e2ab574f；既有Pages版本待最新回读；统一暂停预览8b365058-fc4b-46db-9a52-0bc3e156f81b不是主域生产",
    "verified_at": "2026-10-02，普通latest API与实时health回读；旧区和旧域绑定面板回读"
  },
  "blockers": [
    "GitHub部署Secrets已完成，统一Worker业务运行凭据尚未补齐、自动发布变量未启用；旧Worker加密Secrets不能从名称列表恢复，需安全注入或经验证的保留路径",
    "旧Bot普通member问题已通过授权换为管理员@xiyunewsbot解决，私聊/start和三类自然回执已确认；看门狗实际私聊告警仍未验证，不人为制造故障或重放旧消息",
    "SSH新增持久访问已经操作时确认并完成；Cloudflare新增持久权限、秘密值注入及后续浏览器删除仍须各自安全流程，不从SSH确认扩大权限，不重复询问已完成旧区与三绑定删除"
  ],
  "next_action": "GitHub Mobile已验证，运营者具体确认后已点击单仓库运行Token生成，未读取秘密页面/值。统一xiyunews暂停预览已实际部署，两个false开关与固定source/artifact SHA回读通过。运营者从GitHub页面复制Token到scripts/configure_edge_runtime_token.py交互隐藏输入（--check-only已实际通过），只写暂停Worker两个运行Secrets，助手不得读取页面或用广权限CLI凭据替代。剩余Recovery/Telegram/Access安全配置、停旧Cron、DO迁入、主域切换与自然验收继续串行；自动发布仍不启用，现役Cron/域保持，部署Token不重复输入，旧资源不能先删。",
  "states": {
    "code": "pending",
    "tests": "pending",
    "pr_merged": "pending",
    "deployed": "pending",
    "production_verified": "pending"
  },
  "evidence": "project-docs/releases/2026-10-02-cloudflare-production-cutover.md"
}
```

当前唯一编辑工作区复用 `/tmp/xiyunews-cloudflare`，已从最新 origin/main 切换为 `agent/xiyunews-edge-cutover`，没有并行所有者；基础的远端和本地任务分支均已删除。前序合并、历史祖先和自然回执已有证据，不重复旧 Token 撤销或 /start。总体实际架构见 [系统架构](system-architecture.md)，最终切换见 [单项目清单](cloudflare-single-project.md)，实时入口见 [实时交接](../realtime/docs/handoff.md)。历史 release 保留，本指针不授权执行旧 backlog。
