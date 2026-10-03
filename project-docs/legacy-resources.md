# 旧品牌资源清理与保留边界

早期清理对应 [Issue193](https://github.com/ohxiyu/xiyunews/issues/193)，本清单已按2026-10-03生产切换更新；当前证据任务为[Issue201](https://github.com/ohxiyu/xiyunews/issues/201)。运营者授权删除确实不再使用的旧资源，不代表按旧名称批量删除；资源名称、仓库别名和实际依赖分别判断。统一项目已接管，但下列旧资源未宣称已删除，后续状态以[当前交接](handoff.md)为准。

## 已删除

Cloudflare Pages 项目 `horizon-ohxiyu` 已删除，并由项目列表确认不存在。它只有 `horizon-ohxiyu.pages.dev`，没有自定义域；面板连接旧仓 `ohxiyu/Horizon`，最近生产更新为 2026-08-21，当前代码和运行文档没有依赖。新站 `bmtnews` 和其他项目均未作为删除目标。

旧项目有 323 个部署，第一次删除因 Cloudflare `8000076` 被拒绝。随后按 [Cloudflare 大量部署的已知问题流程](https://developers.cloudflare.com/pages/platform/known-issues/#delete-a-project-with-a-high-number-of-deployments)，仅清理这个项目的旧 Preview 部署，再执行项目删除；中途网络错误停止后重新列出实际剩余目标，未清理新站部署。

本机留存 `/tmp/xiyunews-legacy-pages-backup.n1NmPl/wrangler.toml` 和公开首页 `homepage.html`。这只是项目配置与首页快照，不是完整站点、Git 历史或所有历史部署备份；被删的部署历史不能由这两份文件直接恢复。临时目录不进 Git，不作为新的部署源，不删除用户本地文件。

## 不能按名字删除的现役资源

| 资源 | 当前依赖与处理 |
| --- | --- |
| `ohxiyu/xiyunews` | 当前私有主仓，必须保留。 |
| `ohxiyu/bmtnews-standalone` | GitHub 已重定向到主仓，不是独立副本；通过旧名字删除可能删除新主仓，禁止操作。 |
| `ohxiyu/bmtnews` | 当前访问 404，未找到独立可清理仓库，不把 404 当作已执行删除。 |
| Pages `bmtnews` | xiyu.news绑定及对应CNAME已解除，主域由统一Worker提供；旧项目/历史仍保留，验收后具体确认退役。 |
| Worker `bmtnews-daily-dispatcher` | 已停用、无Cron、旧协调入口retired；原RecoveryGate已迁入xiyunews，同ID状态必须保留，不能随旧项目清理删除DO。 |
| `ohxiyu/fomobtc` | PR195保留完整main历史，服务器已运行新仓d6a9d3f；删除/归档前仍须核对其他分支、PR和独有工作，不能用main祖先证明所有内容已合并。 |
| Worker `fomobtc-watchdog` 及其 STATE KV | 旧Worker已停用、无Cron，统一Worker接管自然检查；STATE仍现用，旧Worker退役不代表KV可以删除。 |
| `fomobtc.com` DNS 区域与 `api.fomobtc.com` | 原域仍转入既有话题群，只读 API 被看门狗使用；必须保留，不修改 nginx。 |
| 东京 `fomobtc` 服务、SQLite、环境文件、备份 | 现役实时运行系统，不在清理目标中。 |

旧 Worker `fomobtc` 的退役已记载在原项目 2026-09-25 发布记录，本次账户列表没有该 Worker；本次没有再次删除。其他产品的 Cloudflare 项目、DNS 区域与资源不在授权范围内。

## 旧域清理：已删除并回读

`bmt.news` DNS 面板当前仅有三条代理 CNAME：`bmt.news`、`www.bmt.news`、`next.bmt.news`，均指向 `bmtnews.pages.dev`，Pages 中还有对应三个绑定。`xiyu.news` 自己的 CNAME 独立指向同一生产项目，不依赖旧 DNS 区域；本次没有修改新域的其他记录。

运营者要求旧域不再跳转：当前 apex/www 由 Worker 返回 410，但 `next.bmt.news` 仍是旧绑定，不能写成所有旧入口已清理。本机 `bmt-news-dns-observed.json` 仅保存上述三个已观察到的 DNS 记录，不是完整区域导出或所有 Cloudflare 设置备份。浏览器下载权限提示未授权，因此没有宣称已成功导出 BIND 文件。

运营者本轮操作时明确确认后，已删除上述三个Pages绑定和bmt.news DNS区域；面板回读生产绑定仅剩xiyu.news，区域列表没有旧区且保留新域和实时域。普通新域latest回读为2026-10-02、14条。旧地址可能解析或TLS失败、不保证410；没有删除注册，设置不会自动恢复。资源与域名注册区别见 [删除区域说明](https://developers.cloudflare.com/fundamentals/manage-domains/remove-domain/)。

## Telegram 与旧仓退役条件

运营者于 2026-10-02 报告 Bot 已更换，仍使用原频道且频道已改名。这是运营者报告，不是读取 Secrets、机器人身份或自然发送回执所得；本次未改 Token、目标 ID、话题、权限、信源或提醒规则，也不假设实时话题群和看门狗凭据同步更换。

运营者明确原Token已撤销；PR195全绿后以merge commit完成完整main历史导入，旧main祖先已核验。服务器已按原路径发布新仓d6a9d3f、原Bot改为管理员@xiyunewsbot，三现货分片与三类自然message_id已核验，不再列为未部署；Cloudflare统一项目已接管，但后台登录/自然定时/旧仓独有工作仍分项核对后再退役。证据见[本次接管](releases/2026-10-03-cloudflare-production-verification.md)和[服务器记录](../realtime/docs/releases/deploy-20261002-xiyunews-repository.md)。

2026-10-03进一步只读核验旧实时仓：private、未archive，仅main一个分支、无tags/开放PR，37个关闭PR均merged，旧main7807126d是origin/main祖先。Git历史保留不等于GitHub Issues/PR页面、设置、部署记录或资产完整备份；旧仓退役优先归档保留只读审计，永久删除须说明非Git内容丢失风险并确认，本次仍未执行。

逐条部署步骤见 [服务器迁移清单](realtime-server-migration.md)，运行边界见 [系统架构](system-architecture.md)，Telegram 状态见 [品牌执行清单](telegram-brand-migration.md)。未经验证不归档或删除当前恢复源，不制造生产消息作为验收。
