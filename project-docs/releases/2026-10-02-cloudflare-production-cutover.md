# Cloudflare 单项目生产接管：进行中

Task: https://github.com/ohxiyu/xiyunews/issues/198
PR: https://github.com/ohxiyu/xiyunews/pull/199 （Draft，最终生产接管尚未实施）
Source commit: 基线 91fb5981cd09a51be7c3ef8c355eb6ee179f60fa，PR197 的实际 merge SHA。
Worker version: 暂停版本ae8f5365-8fa6-417e-9d43-0046e8219e94（运行Secret已补齐）；现役原项目版本切换前须再次回读。
Deployment: partial；2026-10-03两个仓库部署Secret与8个Worker运行Secret已安全保存，暂停站点真实发布。生产主域/自然调度未接管，原项目未停。新项目线上无Cron、双开关关闭、RecoveryGate仍外部绑定原namespace，STATE复用原KV，没有迁移DO归属或改服务器配置；分支最终配置仅dry-run，未上传。
Verification: 前序基础 99d2465e 的 CI37024644728 全部可用检查和 Pages 预览通过；CodeQL 跳过。当前阶段的新增回归结果随后追加，不沿用基础测试当本阶段全量验证。
Rollback: 当前阶段未生产切换；保留现役项目与服务器备份，不双调度、不擅自回滚或覆盖发送数据库。

## 顺序与边界

PR197 于 2026-10-02T15:09:10Z 合并，Issue196 基础关闭，当前负责人从新 main 建立 agent/xiyunews-edge-cutover，复用唯一干净工作区。生产接管不是基础合并的自动结果；网站 UI、采集窗口、实时阈值、话题和服务器部署方式不改。

新增协调入口受同一个 `XIYUNEWS_EDGE_ENABLED` 变量控制，迁移前仍走旧入口，启用后走 `https://xiyu.news/publication/check`。两条自动调用工作流都传递变量，只有小写精确 `true` 生效；新入口失败不回退旧入口，也不绕过共享锁直接派发，回归全部使用模拟响应和测试 Token。

Safari 现役 Worker 设置提供名称字段，官方 Workers Beta PATCH 也支持只更新 name、其他字段不变；这说明存在可评估的原地改名入口，不证明 DO、Cron、子域和 Secrets 已成功保留。当前未保存改名或改变配置。实际执行前必须回读不可变 Worker ID、DO namespace ID、Secret 名称和 Cron；失败不重置状态、不盲目继续。

自动发布令牌摘要为现役单账户 Workers Scripts 编辑、2027-01-01 到期，无 DNS/Access/账单权限。这类账户级权限仍能编辑同账户其他 Worker，已经向运营者说明，不宣称仅能编辑 xiyunews。运营者确认继续后于2026-10-03点击创建，随后不读取页面、截图或令牌值，交给运营者隐藏输入；不能据点击动作宣称GitHub配置完成。运行 Secret 的安全注入仍是实际阻塞，不用广权限 CLI 或 OAuth 凭据替代，不能导出旧加密值或添加明文接口。

发现基础工作流硬引用的xiyunews-production环境不存在，私有仓环境能力还受套餐限制，当前API没有返回plan。改为仓库级Secret路径，不要求购买或创建环境，main/可信源/成功/手动启用保护不变；新增离线回归检查，不移除任何现役环境保护。2026-10-03仓库部署凭据已经配置，但开关未启用，仍默认不发布。

准备 `scripts/configure_edge_deploy_token.py` 作为运营者确认后执行的隐藏输入工具：拒绝非交互输入与回显降级，Token 只在内存/stdin，固定 HTTPS API 且不跟随重定向，只读核验账户和调度器后加密写入两个仓库部署 Secret。错误不显示上游正文，部分失败不自动删除/重试，自动发布已启用时拒绝此初始配置流程；不读取旧 Secret、不启用生产、不创建 Token。所有新增测试采用假 Token 和模拟命令，不运行实际凭据写入。

2026-10-03运营者回报“GitHub只读校验失败，没有修改Secrets”；助手对同一变量接口只读请求成功、仓库权限admin=true，去除Token环境变量后也成功，两个部署Secret名称回读仍为空。该证据不能确定运营者终端是PATH、认证还是网络问题。补充 `--check-github` 无令牌只读诊断、输入前预检、Homebrew既有CLI路径回退和固定错误分类；不会输出原始错误正文、自动登录、改代理或扩大权限。运营者须在发生失败的终端执行诊断，不要求重新创建令牌。本阶段安全工具20项离线回归及助手终端只读预检通过，生产仍未接管。

该修订主站完整980项测试、scripts/check_governance.py及git diff --check通过；没有用真实Token进行配置写入，PR199保持Draft，不合并未完成生产接管的代码。

## 部署凭据配置实际完成（2026-10-03）

运营者在同一终端只读预检通过后，使用隐藏输入脚本配置两个仓库Secret并报告名称回读成功；助手随后独立 `gh secret list` 只取名称和updatedAt，确认CLOUDFLARE_ACCOUNT_ID为2026-10-02T16:31:00Z、CLOUDFLARE_API_TOKEN为16:31:01Z（上海2026-10-03 00:31）。没有读取密钥值，不能把名称存在当作真实Worker上传验收。XIYUNEWS_EDGE_ENABLED仍不存在，运行Secret、域名/状态/Cron迁移未完成。下一步隔离预览Worker部署已提出具体确认，尚未执行；不据此次Secret授权扩展为启用调度或删除旧资源。

4668f4d63437f95d445072bba38f63ce8663f35f的远端CI37034229414全部可用检查成功，Pages预览40613c7a-15e2-4e8b-a236-38a4610317e5成功，CodeQL跳过。原调度器三运行Secret名称保持；第一次部署列表因网络失败，随后只读重试成功，现役版本仍9774435b-1c72-4dad-9552-0440e2ab574f，没有借此升级工具或部署。主域latest为2026-10-02、14条，此时未到新日07:26；实时source_commit仍d6a9d3f完整SHA，active/MainPID235825/NRestarts0、新Bot管理员、群名和话题保持；切换后30条sent、14条按规则archived，最新资金流1271、公告1270、行情1269，无失败状态。未发送测试消息或读取Token，没有验证手机/私聊实际告警。

初次回读实时服务器三类自然消息 1251/1250/1249，共 11 条 sent；后续只读核验增长到 18 条 sent、9 条按规则 archived，最新资金流向 1258、公告 1257、行情 1254，无失败状态。原群话题保留，手机收件及看门狗私聊实际告警仍未独立验证，不制造告警或重放旧消息。旧 Cloudflare 资源仍承担业务，不能先删除。

## 生产接管明确授权与安全验证待办（2026-10-03）

运营者随后明确要求直接在生产环境完成全部剩余工作，作为本阶段Worker部署、业务配置和受控切换的授权，不再把隔离预览部署确认列为阻塞。删除或创建持久访问的浏览器动作仍遵循操作时安全确认；不扩大到无关项目、付费服务或绕过身份认证。现役dispatcher版本的只读资源核验确认RECOVERY_GATE原namespace_id为d4f55a5a95624e7e9776bbf050cf1ee7，三个运行Secret名称存在；看门狗ALERT_CHAT_ID及TELEGRAM_BOT_TOKEN名称存在，未读值或迁移状态。

统一后台需要私有仓Contents写权限，调度需要Actions写权限；Cloudflare上传令牌不能充当这类业务认证。已使用Safari打开GitHub单仓库运行令牌配置页，身份为@ohxiyu；进入设置前触发sudo模式再认证，已按页面发起GitHub Mobile安全验证，需运营者本人批准。没有创建新GitHub Token、读取密钥、保存新权限或改动生产域/Cron/Secrets；先补安全配置再接管，不以代理依赖旧项目冒充单项目。手机验证不是创建Token的最终确认，后续权限摘要还要核对。

## GitHub 运行令牌与暂停预览（2026-10-03）

运营者报告完成 GitHub Mobile 验证，随后在权限摘要具体确认：xiyunews-edge-runtime仅选ohxiyu/xiyunews，Contents和Actions读写、Metadata只读、账户权限0，2027-01-01到期；已解释Contents写不只限新闻。按确认点击Generate token一次，创建后的AX/截图和秘密值均未读取，因此记录为已提交创建动作，不能宣称令牌已存入Cloudflare。运营者须从GitHub页面自行复制到隐藏输入，不重复生成或从本机广权限认证替代。

明确生产授权下，采用新项目受控transfer路径，原地改名候选未执行。基于已合并main91fb5981未改的统一入口和配置，固定新出版快照aa09cbc80c082bb83b519d578ac8b83db19d7ca1真实Jekyll渲染44.587秒，校验并上传8528个公开资产；本机生成的Gemfile.lock移至仓库外保留，不写gh-pages。Wrangler4.131.0实际上传统一入口，版本8b365058-fc4b-46db-9a52-0bc3e156f81b、预览https://xiyunews.drminutes.workers.dev，绑定原RecoveryGate外部类和同一STATE KV，无Cron、无主域、双开关false。

独立公网/health回读project/service=xiyunews、repository=ohxiyu/xiyunews、两个固定source/artifact SHA及两个false开关，与部署版本一致。health中的schedule_crons_utc是代码声明的目标排程，不是已激活Cron证据；实际上传配置triggers为空。此步仅隔离部署，不把HTTP健康称为单项目生产验收，原Cron/网站/看门狗均未改。

预览首页、/api/latest.json、/feed-zh.xml、/sitemap.xml、manifest及service-worker均200，随机不存在路径404；最新出版date2026-10-03共14条、generated_at2026-10-02T23:29:27.197755Z。/s/和/api/admin/quick-posts因缺运行/Access配置503闭锁，未绕过鉴权、扩大白名单或发表测试新闻。正式域接管及登录后台仍待后续步骤。

新增scripts/configure_edge_runtime_token.py先校验固定目标、自动发布关闭和目标Secret尚不存在，getpass禁止回显降级，Token只经内存和curl/Wrangler stdin；只写ADMIN_GITHUB_TOKEN/GITHUB_DISPATCH_TOKEN，不用真实内容或dispatch探测写权限，不写凭据文件/命令参数/聊天/日志，错误固定脱敏，部分写入不重试。19项假Token离线测试通过，本机--check-only实际预检通过；真实运行Secrets仍待运营者隐藏输入。根全量999项、治理和diff检查通过；后续明确固定Wrangler --name=xiyunews避免配置文件改名造成错写，19项及治理再次通过。预览canonical为https://xiyu.news/、Secret名称列表为空，没有读取秘密值。前一docs提交2ebb1b9c的CI37036099831全部可用检查及Pages5cbda61a通过，CodeQL跳过；本次远端CI仍需核验，PR199保持Draft。

## 运行凭据实际补齐与最终配置（2026-10-03 19:25）

运营者报告隐藏输入GitHub运行Token配置成功；助手独立回读ADMIN_GITHUB_TOKEN/GITHUB_DISPATCH_TOKEN两个名称，/ready返回ready及Actions写/Contents读可访问，没有复制CLI认证。该运行Token对应的发布为e5b2ff37-038c-4ece-9e75-1638624226e7，Secret变更部署于2026-10-03T11:14:15.269159Z；创建后没有读取一次性Token页面/截图或值，不能根据ready声称已发布业务内容。

新安全工具先核验目标暂停、两个已配置Secret、暂存恢复Key不存在。官方Wrangler pages download config读取原项目plaintext设置，只选ADMIN_ACCESS_ISSUER/AUD/ALLOWED_EMAIL，保持原单账号、文件在仓库外0700目录且toml0600，未导出Pages密文。严格主机校验SSH只读现役/root0600配置与进程，验证源码d6a9d3f和话题3/5/7不变、Bot=xiyunewsbot，全部话题切换前备份中唯一positive私聊ID且getChat为private；目标来源与历史setup_watchdog.sh一致，但原CF加密ALERT_CHAT_ID仍不能直接比对。

依照生产配置授权，选定的Telegram字段只在受保护子进程内存/stdin传给新Worker；未改服务器、旧Worker、群、话题或白名单，未发送消息或读取Token给模型。新随机恢复密钥同时写新Worker RECOVERY_CHECK_TOKEN及仓库XIYUNEWS_RECOVERY_CHECK_TOKEN；旧仓库RECOVERY_CHECK_TOKEN保留，自动发布变量不变。8个Secret名称和新仓库Secret名称回读成功，暂停版本ae8f5365、source91fb5981/artifactaa09cbc8、双开关false独立health回读通过；/s/现在因预览wrong-origin403闭锁，不扩大Access。

初次调用micromamba旧Python缺tomllib，在import阶段退出且未写任何配置；改用项目现有uv Python3.11+，没有安装额外依赖。18项安全来源工具/19项运行Token工具的模拟测试通过，实际inspect-only来源检查通过后才执行写入；工具失败不显示异常正文或自动重复轮换，存在初始Key时拒绝重跑。

本分支补齐最终transfer migration/local binding、保留原STATE KV/三组Cron、正式Custom Domain及运行开关；源码为最终配置不代表线上已启用。两条恢复工作流同时传递旧/新Secret，Python仅精确true切换新端点/新Key，新Key缺失时不回退旧值、不派发。最终配置dry-run、根完整1019项/治理/diff、94项边缘/type/audit0通过，b3fcbb6c前一head的CI37101633052/Pages82bb422f全部可用检查通过，CodeQL跳过；本轮代码仍需新head远端CI后才合并。

已请求运营者先把Safari切离一次性Token页面，电脑工具未激活前不能跳过get_app_state，因而未读取该页或进行浏览器域名变更。主域仍Pages、旧Cron仍运行，部署Secrets/8个业务Secret都已完成，不再等待重复输入。最终代码通过CI可按站立授权合并，但原域绑定解除需要操作时确认；生产切换和自然验收分别记录，旧资源不能先删。

## 旧 Cron 传播延迟的停用保护（准备，未部署）

复查[官方Cron说明](https://developers.cloudflare.com/workers/configuration/cron-triggers/)发现撤销/变更最多15分钟传播，仅清空旧Cron不足以证明旧回调停止。为旧dispatcher和watchdog入口增加精确true的XIYUNEWS_LEGACY_DISABLED保护，默认未设置不改现生产；启用时scheduled不访问上游/KV、不推送，旧协调入口503 retired，health提供只读停用标识。该变量只用于旧项目，不注入新统一项目，不重写RecoveryGate逻辑或重置数据库。

新增离线dispatcher及watchdog回归模拟旧回调，断言无网络/状态写入或通知；当前旧项目仍未部署保护、仍运行原Cron。实际切换时先发布经main核验的保护与旧停用变量并清空Cron，等在途调用结束和回读正确后才启新调度。新代码完成与旧服务已停止是两种状态，不以此提前宣布单项目接管。

加入此保护后根完整1019项再次通过，边缘完整95项/tsc/types/audit0通过、原dispatcher dry-run通过；watchdog Node 4项通过，治理和diff通过。没有实际部署旧保护、暂停服务或发送消息，当前head新远端CI还需核验。

## 群名称实际统一与验证

运营者此前明确确认 Telegram 名称为 xiyu.news，本次仅更正现役实时群实际大小写/格式。服务器进程 getMe 为 @xiyunewsbot，原群 administrator 且已有 can_change_info=true；核对新仓 SHA、原群/话题3/5/7之后调用 setChatTitle。2026-10-02T15:22:48.674197Z（上海23:22:48）getChat 回读为 xiyu.news，forum=true，简介逐值保持；不改成员权限、创建话题、重启服务、改 Token/配置或另发宣布/测试消息。Token始终留在服务器，不进入本机、Git 或日志；Telegram 自身可能生成改名服务记录，这不是业务测试推送。

## 本阶段离线及真实构建

主站完整 968 项、治理、实时独立61项/契约和看门狗3项通过。新增7项协调接口/工作流门槛与8项安全配置工具测试，全用模拟响应/假Token，不真实请求AI或发送消息。初次本机默认Ruby4缺少csv导致Jekyll失败，改用现有Ruby3.3.12，与CI配置一致；未因此改主项目Gemfile或提交本机生成的lock。233597f892c086e82d5cc13f3a7041448242424b的出版快照真实Jekyll渲染成功，prepare_edge_assets校验成功，统一Wrangler dry-run读取8364个资产、入口压缩22.72KiB；该结果不是Worker已发布。

关联：[当前交接](../handoff.md)、[切换清单](../cloudflare-single-project.md)、[基础记录](2026-10-02-cloudflare-unified-foundation.md)、[新 Bot 自然回执](../../realtime/docs/releases/deploy-20261002-xiyunews-bot.md)。
