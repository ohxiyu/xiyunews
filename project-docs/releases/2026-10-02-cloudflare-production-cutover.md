# Cloudflare 单项目生产接管：进行中

Task: https://github.com/ohxiyu/xiyunews/issues/198
PR: https://github.com/ohxiyu/xiyunews/pull/199 （Draft，最终生产接管尚未实施）
Source commit: 基线 91fb5981cd09a51be7c3ef8c355eb6ee179f60fa，PR197 的实际 merge SHA。
Worker version: 统一项目未部署；现役调度器和看门狗版本见基础记录。
Deployment: pending；2026-10-03按确认提交部署令牌创建按钮，未读取创建后的页面或令牌值；运营者初次只读校验失败，修订后预检成功并隐藏输入配置两个部署Secret，名称和更新时间已回读。统一Worker未部署，未改主域、Cron、DO/KV或服务器配置。
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

## 群名称实际统一与验证

运营者此前明确确认 Telegram 名称为 xiyu.news，本次仅更正现役实时群实际大小写/格式。服务器进程 getMe 为 @xiyunewsbot，原群 administrator 且已有 can_change_info=true；核对新仓 SHA、原群/话题3/5/7之后调用 setChatTitle。2026-10-02T15:22:48.674197Z（上海23:22:48）getChat 回读为 xiyu.news，forum=true，简介逐值保持；不改成员权限、创建话题、重启服务、改 Token/配置或另发宣布/测试消息。Token始终留在服务器，不进入本机、Git 或日志；Telegram 自身可能生成改名服务记录，这不是业务测试推送。

## 本阶段离线及真实构建

主站完整 968 项、治理、实时独立61项/契约和看门狗3项通过。新增7项协调接口/工作流门槛与8项安全配置工具测试，全用模拟响应/假Token，不真实请求AI或发送消息。初次本机默认Ruby4缺少csv导致Jekyll失败，改用现有Ruby3.3.12，与CI配置一致；未因此改主项目Gemfile或提交本机生成的lock。233597f892c086e82d5cc13f3a7041448242424b的出版快照真实Jekyll渲染成功，prepare_edge_assets校验成功，统一Wrangler dry-run读取8364个资产、入口压缩22.72KiB；该结果不是Worker已发布。

关联：[当前交接](../handoff.md)、[切换清单](../cloudflare-single-project.md)、[基础记录](2026-10-02-cloudflare-unified-foundation.md)、[新 Bot 自然回执](../../realtime/docs/releases/deploy-20261002-xiyunews-bot.md)。
