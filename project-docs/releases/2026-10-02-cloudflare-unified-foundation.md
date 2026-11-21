# 单项目迁移基础与旧域清理回读

Task: https://github.com/ohxiyu/xiyunews/issues/196
Source commit: 基线d6a9d3f29ef93c138842342c973b3049fb7bc252；最终head见本任务PR。
Worker version: 统一Worker未部署、调度器9774435b-1c72-4dad-9552-0440e2ab574f未改；现役看门狗新Bot Secret Change版本a5330597-ee57-4a61-91f0-9a34cb431676于21:03:11.654生效，业务代码未再部署。
Deployment: 统一边缘Worker未部署；实时服务器2026-10-02 20:01:45已切换到新仓PR195合并SHA，自然Telegram送达验收未通过，详情见本记录末尾。
Verification: 2026-10-02，旧历史祖先、区域/绑定面板、普通latest与实时health回读、离线回归；02600b04真实Jekyll/资产校验/统一Worker dry-run及全部可用远端CI通过，见36969119354；19:55专用SSH严格身份登录及未重启服务验证成功。连接交接追加提交的检查以PR197当前head为准。
Rollback: 边缘无生产切换，不擅自恢复第二Cron；实时上一版release与备份保留，服务器回滚另需授权，不覆盖数据库。

## 本轮证据

运营者明确确认旧Token撤销后阶段3正常推送为PR195；主站、治理、实时双版本和Pages检查通过后，以merge commit合并为d6a9d3f29ef93c138842342c973b3049fb7bc252。已核验旧main7807126d8c7cdb51e18f0b91ba27f500271f9f08为origin/main祖先，远端有realtime/；无squash/强推，CodeQL因套餐跳过。

按本轮操作时确认删除旧DNS区与三个旧Pages绑定；Safari列表没有bmt.news，仍有xiyu.news及fomobtc.com，生产Pages域绑定只剩xiyu.news。新域latest为2026-10-02、14条；实时仍是旧2.6.0/b226b625cf3875b6693e0768d75d88d50b33c08d、三现货分片live。未删除注册，旧设置不会自动恢复；本机三记录快照不是完整DNS备份。

统一Worker基础默认不开Cron，复用原鉴权/公开路由/dispatcher/watchdog，原DO及KV不重置；准备固定出版SHA构建与默认关闭自动部署，恢复仅重建产物不用AI。94项边缘测试/tsc、看门狗3项、主站951项、原后台和路由51项、资产8项通过；实时3.11初次共享文档夹具缺两条链接导致60通过1失败，复制完整共享文档后61项/ruff/mypy/compileall/契约通过，未绕过检查。治理精确base/head通过；真实Jekyll/dry-run与双版本远端CI以[PR197](https://github.com/ohxiyu/xiyunews/pull/197)为准。

## 未完成

远端[CI36963560959](https://github.com/ohxiyu/xiyunews/actions/runs/36963560959)核验a7a4fe76847dee984a0ad8439fc1f8ea8539deff：真实Jekyll构建和统一Worker dry-run、主站测试、实时3.11/3.12、治理全部成功，Pages预览89775190也成功；CodeQL因套餐跳过。GitHub主仓描述与主页已改为统一项目和https://xiyu.news，私有状态不变。最后普通首页/RSS/sitemap均200，缺口仍是实际安全配置与生产切换，不是测试失败。

无新Worker/域名/Cron/DO/服务器切换、自然回执或统一生产证据。仍缺安全Secrets注入和自动部署配置；可信SSH入口已按下节操作时授权恢复。未新增收费服务或发送真实测试消息。准确切换与验收见 [单项目清单](../cloudflare-single-project.md)。

## 继续执行：工具链安全与发布门槛

运营者要求一次执行此前讨论的全部步骤。同一负责人在Issue196明确补充独立安全提交，仍用本分支/PR197，不建立并行修改核心模块的任务。更新Vitest到4.1.11、Wrangler到4.131.0、workers-types到5.20260910.1；保持测试池0.22.0，覆盖其传递依赖Undici为7.29.1、Sharp为0.35.4。初次安装发现类型包peer范围不匹配，修正类型版本后正常npm安装成功，没有force或legacy-peer-deps。

完整npm audit从7项告警降到0；npm ci、types:check、tsc、94项边缘测试及原调度器dry-run均成功。新增部署前完整审计和main手动执行限制，完整Python953项通过，10项资产/发布门槛测试、51项原后台/公开路由及3项看门狗测试通过，根治理与实时仓库契约通过。统一真实静态构建及新Wrangler的最终dry-run等待本轮远端CI，不拿测试夹具代替网站产物。

安全修复时只读确认默认SSH别名未解析为东京主机、known_hosts无目标IP已知条目，GitHub无Cloudflare自动发布凭据；没有猜密钥或复制Wrangler OAuth。公网latest仍2026-10-02/14条，实时health仍旧2.6.0/b226b625cf3875b6693e0768d75d88d50b33c08d、三个现货分片live。该时点的SSH缺口已在下节解决，Cloudflare凭据缺口仍保留；源码/测试推进不能算一次迁移全部完成。纠正服务器操作清单关于realtime尚未进入main的陈旧说明，旧Token撤销门槛不再重复询问。

## 专用 SSH 恢复与最终安全检查回读

[CI36969119354](https://github.com/ohxiyu/xiyunews/actions/runs/36969119354)对应02600b04020a79cc1e13355c42064cdc8aa35cc8：主站、治理、实时3.11/3.12、真实静态构建及统一Worker dry-run全部成功，Pages预览也通过；CodeQL跳过，不写成成功。PR197仍Draft，生产未切换。

运营者操作时明确确认新增本机专用SSH访问后，通过已登录阿里云命令助手核对服务器主机名及ED25519指纹，并追加仅公钥。原两把公钥完整保留，服务器保存追加前备份；新密钥的私钥未离开本机，且未进入Git。2026-10-02 19:55上海时间，严格主机校验下admin登录及sudo -n验证成功，systemd active/running、MainPID219051、NRestarts0，旧release路径未变化，公网三现货分片live。该授权仅恢复SSH，不扩大为Cloudflare新权限、密码更改或提前删除旧资源。完整证据见 [实时连接记录](../../realtime/docs/releases/ssh-access-20261002.md)。

## 新仓服务器切换与发现的 Telegram 权限问题

按运营者此前的服务器部署授权，从新仓PR195实际合并SHA打包独立realtime模块。确认业务src、config与依赖锁与旧release完全一致，独立venv哈希安装和pip check通过；停原服务后SQLite备份integrity_check=ok，环境除SOURCE_COMMIT外逐字节未改。20:01:45原子切换到d6a9d3f29ef93c138842342c973b3049fb7bc252，原systemd单实例MainPID233683/NRestarts0，三个现货分片预热后live；旧release和root-only备份均保留，没有改nginx、Worker或目标群。

实际自然提醒出现telegram_rejected，无message_id。只读getMe200，Bot有效；getChat显示只读forum群xiyuNews，getChatMember显示Bot仅member，群默认文字/图片发送权限关闭。迁移前已有43条同类失败，因此不声称本次切换引起该权限问题，也不将Telegram启用当作送达证据。管理员发消息权限恢复、自然回执和看门狗观察待完成，不补发旧消息；见 [实际部署记录](../../realtime/docs/releases/deploy-20261002-xiyunews-repository.md)。

共享治理测试夹具原先只复制两个实时入口文件，新连接记录的跨模块链接导致第一次完整测试952通过1失败；补齐复制realtime/docs后953项通过，没有弱化链接检查。实时61项、ruff/mypy、两套治理与看门狗3项复测通过。本次连接/部署文档最终CI仍以PR197当前head为准。

现役看门狗20:10:23和20:15:23两轮自然Cron均outcome=ok、日志watchdog: ok，KV无告警。其规则不检查Bot群权限，因此“无告警”不能代替Telegram自然回执；该观察不解除业务验收阻塞。20:15最终公网回读新仓SHA正确且三个spot分片live。[CI37005429902](https://github.com/ohxiyu/xiyunews/actions/runs/37005429902)对应8dad631fd69f406172eb4e16acd49916729cd781，全部可用检查和Pages预览成功，CodeQL跳过；追加本段冻结记录后检查以PR当前head为准。

## 后续授权：新 Bot 保留原话题

运营者明确指定@xiyunewsbot，确认已是管理员并保留原话题，通过本机隐藏输入提供Token。21:03:05备份环境与SQLite后仅更新实时Token并重启原systemd，21:03:11.654同步更新现役看门狗Token；不改群、话题3/5/7、ALERT_CHAT_ID、Cron、KV、信源或提醒规则。21:06只读回读新Bot身份、原群administrator、进程与配置Token一致，排除Token后所有配置与备份相同；MainPID235825/NRestarts0，三个spot分片live。管理员问题不再列为未解决，但截至该时点无切换后新自然触发回执，手机收件及新Bot看门狗私聊未验证，不能提前删除旧恢复资源。详见 [新Bot切换证据](../../realtime/docs/releases/deploy-20261002-xiyunews-bot.md)。

前序a54665c5的[CI37005750396](https://github.com/ohxiyu/xiyunews/actions/runs/37005750396)与Pages预览均通过，CodeQL跳过；本次仅更新真实运维交接和验证记录，统一Worker仍未部署，PR197保留Draft。

新看门狗版本计划21:10:23的自然Cron实际于21:10:32.765执行，outcome=ok、日志watchdog: ok、exceptions为空。21:11只读回读服务和原群管理员身份一致、备份0700/0600及SQLite integrity_check=ok，仍无切换后新自然事件。根完整Python回归和治理、实时61项及实时契约通过；发布文档的最终检查以PR197新head为准，不提前合并或启用统一Cron。

21:24运营者确认已/start，API核验新Bot收到切换后私聊/start且该私聊可读取，不再把/start列为待用户操作；未比对加密ALERT_CHAT_ID，真实告警和手机送达仍未验证。新看门狗第二轮计划21:15:23、实际21:15:37.068也ok，服务/原群/话题仍保持，切换后仍无新自然事件。358807bc的CI37011428036与Pages预览全部可用检查通过，CodeQL跳过；详情见新Bot记录，本次不改生产配置。

## 基础收尾与三类自然消息回读

运营者进一步要求完成 Cloudflare 合并及剩余改造。核验 32a838fb2cd99c5ea72bf55f7aec4ccb1a06dbcd 的 [CI37012988502](https://github.com/ohxiyu/xiyunews/actions/runs/37012988502)：真实 edge-build、治理、主站、实时 3.11/3.12、路径检查全部成功，Pages 预览也通过；CodeQL 跳过，不写成成功。main 仍为 PR195 的 d6a9d3f，分支同步无冲突。

实时新 Bot 切换后取得 11 条自然发送成功回执，最新行情 1251、公告 1250、资金流向 1249；6 条 archived 是原规则结果，不是发送失败。服务 active、MainPID235825/NRestarts0、原话题和配置保留，详细时间见 [自然回执](../../realtime/docs/releases/deploy-20261002-xiyunews-bot.md)。纠正现行交接中的无自然消息、旧 Bot 普通成员等过时阻塞；历史时点的记录保持原样。手机收件、看门狗实际私聊告警和群精确名称仍未独立验收。

本 PR 的范围是默认关闭的迁移基础，代码与可用 CI 已完成；生产接管另建串行任务，不将缺少运行凭据的生产切换假装已完成。当前 GitHub 只有 github-pages 环境，没有 xiyunews-production 环境或 Cloudflare 自动发布 Secrets；本机 OAuth 不能替代 Actions 凭据，旧加密值不能导出。暂停预览部署单独请求确认，主域、旧 Cron、DO/KV 与现役服务尚未修改或删除。
