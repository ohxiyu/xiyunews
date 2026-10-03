# 统一 Cloudflare 生产接管与验收

Task: https://github.com/ohxiyu/xiyunews/issues/201 （父任务 Issue198）。
PR: 部署后文档 PR 待创建；业务 PR199 已合并，不继续编辑原分支。
Source commit: b2aeb97f8481bfad123277463c24bddac0895f8c。
Worker version: 00b0f0f6-f6cf-4ba7-9b79-96644eb6c7dc，首次GitHub自动部署后正式域和绑定回读；手动启用版本f8c394e3保留历史。
Deployment: 实际生产接管已执行，https://xiyu.news 由 xiyunews Worker 提供；两个运行开关与原 Cron 已开启，首次 GitHub 部署工作流37122753609=success。
Verification: 2026-10-03T12:36Z 回读正式域、namespace/KV、8个Secret名称与旧服务停用，两轮自然Cron均通过；下一次真正到期的dispatch与登录后的后台读取仍分项待验收。
Rollback: 保留旧项目历史、原状态与服务器备份。transfer 后不得把旧创建配置直接重跑、回滚 Worker 至迁移前版本或创建空 namespace；任何回退须负责人重新核对原 namespace/主域/唯一调度者并取得授权，不启动双发送者。

## 实际切换顺序

1. 最终业务代码 PR199 的 head add3b20605fdb7cffbe12a00c1f686001b450f11 经 CI37119954469 和 Pages 预览通过，合并 SHA 为 b2aeb97f8481bfad123277463c24bddac0895f8c；CodeQL 因私有套餐跳过。
2. 固定生产出版快照4f87497ecf068324e0a6211e9f4a38a7047f797e，Ruby3.3真实Jekyll构建46.814秒，校验8593个公开资产，使用明确快照目录而非混有旧快照的父目录。main/gh-pages仅只读，本机lock保留到仓库外，不提交生成产物。
3. 先更新暂停预览14e88d14-600b-4161-abd6-2e1213859a79，双开关false、无Cron/主域；生产网站和旧调度在此阶段未改。
4. 原dispatcher部署1f2c4d8a-4491-495c-9ed8-66f0c8eecb80，原watchdog部署90b876b9-c47d-494b-afdc-9c3839be80a9：XIYUNEWS_LEGACY_DISABLED精确true，Cron为空，秘密值和历史保留。旧dispatcher健康回读停用true，watchdog绑定回读停用true和原KV；旧Cron传播期间入口no-op，不依赖仅撤销Cron避免双执行。
5. 以无Cron、双开关false的配置部署transfer版本de359776-95f1-440b-8038-3aac8e2c3778，回读RecoveryGate本地namespace_id=d4f55a5a95624e7e9776bbf050cf1ee7，与原值一致；STATE=469346950dfc4f36b8d9bf9997d960fa也不变。未创建新类、执行delete migration、写测试租约/预算或重置状态。
6. 运营者选择第1项确认域名切换后，用Safari现有Cloudflare会话解除旧Pages的xiyu.news绑定；确认框说明删除对应CNAME，面板回读绑定为空。仅删除绑定和该CNAME，不删除域名注册、项目、内容、其他DNS记录或Access应用。
7. 部署主域接管但调度仍暂停的559c5ce3-93a4-437c-bd36-6508adc93657，正式域健康回读统一服务和固定SHA；公开及匿名后台检查通过后部署最终f8c394e3，两个开关true，原三Cron启用。
8. 正式域健康确认最终版本/双开关/SHA后，设置XIYUNEWS_EDGE_ENABLED=true；派发仅构建/部署的cloudflare-unified.yml，运行[37122753609](https://github.com/ohxiyu/xiyunews/actions/runs/37122753609)。它不采集、不调用AI、不写状态分支、不发测试新闻；部署结果待追加。

## 公网与权限验收

首页、/api/latest.json、/feed-zh.xml、/sitemap.xml、manifest、service-worker、openapi.json和llms.txt均200；canonical为xiyu.news，latest为2026-10-03、14条、generated_at=2026-10-02T23:29:27.197755Z。旧日报路径/2026/10/03/summary-zh.html及当日/editions/2026-10-03/zh.html经静态资产自动HTML重定向后200，不把307误判为丢失文章；不存在路径404。最初随手构造的summary.html实际不存在，真实站内链接为summary-zh.html。

正式域/s、/s/、/admin、/api/admin和/api/admin/quick-posts匿名访问均302到原Access；预览后台因wrong-origin403，保留单账号issuer/AUD/email原值及8个Secret，不扩大白名单或关闭认证。/ready返回ready，Actions写和Contents读可访问；它不等于登录后写接口验收，也未以真实新闻探测权限。Safari已打开原Access登录入口，显示名仍为BMTNews Admin，需后续仅改名称；运营者自行登录后再只读Quick Post，助手不代填/记录验证码。

## 定时与自动发布

正式配置恢复原UTC三组：26 23 * * *、36,46,56 23 * * *、*/5 * * * *。新恢复协调选择同一精确true仓库开关、正式域与单独XIYUNEWS_RECOVERY_CHECK_TOKEN，旧值不覆盖、不回退；旧协调入口retired，原两个Worker无Cron并设置停用保护。仍需真实版本/自然scheduled日志与workflow_dispatch回读，不把health代码声明的Cron表当触发器已激活证据。

STATE只读回读为failing=0、alerted=false、lastAlert=0，不能代替自然检查或告警收件。本轮不发送测试消息、不人为制造故障、不重放失败新闻；东京服务未重启、未改配置/数据库/群组/话题/规则。只读SSH回读MainPID235825/NRestarts0、active、current=d6a9d3f新仓release；公网health三spot分片live、队列0、Hyperliquid既有degraded保留。

首次自动部署37122753609实际success：Jekyll60.726秒，上传/触发器成功，部署版本00b0f0f6；正式域/health的版本、完整source/artifact SHA与双true开关一致，版本API再次确认本地原namespace、原KV及8个Secret均保持。不是仅凭Secret存在或本机OAuth上传来宣称GitHub凭据可部署。

统一Worker两轮自然Cron计划2026-10-03T12:30:51Z、12:35:51Z，均版本00b0f0f6、outcome=ok、exceptions=[]、watchdog:ok，采集分别fresh/not_due，square和x均idle。因内容新鲜、队列未到期，两轮均没有实际派发，不能将idle或本次纯部署手动派发当自然Feed Collection验收；下一次真正到期的自然dispatch仍待，不为验收产生额外AI消耗或消息。

## 尚未完成与保留边界

东京只读SQLite进一步核验Bot切换后125条sent、78条archived，无失败状态；最新自然行情message_id1364（12:29:37Z）、公告1352（Bitget，11:00:09Z）、资金流入1361（11:54:39Z）。只读连接mode=ro，未执行发送或修改队列；第一次误用不存在的release虚拟环境路径在sudo启动前失败，后用已有系统Python标准库读取，没有安装依赖或更改服务器。手机收件仍未确认。

旧私有ohxiyu/fomobtc当前未归档，仅main一个分支、无tags/开放PR，列出的37个关闭PR均已合并；旧main7807126d仍是origin/main祖先。没有据此声称GitHub Issues/PR页面、设置或Release资产能由subtree完整恢复；退役优先保留只读历史，删除需明确接受丢失这些非Git内容的风险。本轮未删除旧仓。

首次GitHub纯部署和两轮自然watchdog已通过，第一次真正到期的自然dispatch仍待，且需区分采集与社交分发，不用手工派发冒充。登录后的Quick Post读取、手机收件及实际私聊告警仍未验收。旧Pages、两个停用Worker和旧实时仓库暂保留；具体确认退役时保留非Git历史审计，不删除现用DO/KV、fomobtc.com/API/DNS/nginx、SQLite、环境文件、SSH或备份。

本轮根完整1019项、治理、实时repository契约、diff检查通过。初次精简实时交接时未保留契约要求的10个固定字段，检查发现后已恢复全部字段并再次通过；未放宽治理。边缘95项/audit0与watchdog4项是业务PR199已验证代码，当前仅文档变更，不虚构重复部署或改业务版本。

前序秘密值只留在既有安全存储，当前版本回读仅列名称/非秘密开关/状态ID，不导出密文、添加秘密调试端点或提交凭据。实际部署通过既有Wrangler认证，GitHub上传凭据已由隐藏输入配置；不复制CLI OAuth为业务Token。文档在Issue201的独立agent分支回写，禁止直接提交main。历史记录见[前阶段](2026-10-02-cloudflare-production-cutover.md)，当前架构见[系统架构](../system-architecture.md)。
