# 旧品牌资源清理与保留边界

本记录对应 [Issue193](https://github.com/ohxiyu/xiyunews/issues/193)，核验时间为 2026-10-02。运营者授权删除确实不再使用的 fomobtc/BMTNews 资源，不代表按旧名称批量删除；资源名称、仓库别名和实际运行依赖必须分别判断。后续状态以 [当前交接](handoff.md) 为准。

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
| Pages `bmtnews` | 实际承载 `xiyu.news`，必须保留；旧项目名不是闲置证明。 |
| Worker `bmtnews-daily-dispatcher` | `/health` 指向 `ohxiyu/xiyunews` 和 `https://xiyu.news`，继续负责采集、日报恢复和分发派发，必须保留。 |
| `ohxiyu/fomobtc` | 主仓 main 尚无 `realtime/`，服务器仍是旧仓 2.6.0；保留迁移和恢复入口，不删除、不提前归档。 |
| Worker `fomobtc-watchdog` 及其 STATE KV | 当前五分钟定时看门狗仍运行；没有 HTTP 路由不等于无用，不删除 Worker、Cron 或状态。 |
| `fomobtc.com` DNS 区域与 `api.fomobtc.com` | 原域仍转入既有话题群，只读 API 被看门狗使用；必须保留，不修改 nginx。 |
| 东京 `fomobtc` 服务、SQLite、环境文件、备份 | 现役实时运行系统，不在清理目标中。 |

旧 Worker `fomobtc` 的退役已记载在原项目 2026-09-25 发布记录，本次账户列表没有该 Worker；本次没有再次删除。其他产品的 Cloudflare 项目、DNS 区域与资源不在授权范围内。

## 旧域清理：准备完成，尚未删除

`bmt.news` DNS 面板当前仅有三条代理 CNAME：`bmt.news`、`www.bmt.news`、`next.bmt.news`，均指向 `bmtnews.pages.dev`，Pages 中还有对应三个绑定。`xiyu.news` 自己的 CNAME 独立指向同一生产项目，不依赖旧 DNS 区域；本次没有修改新域的其他记录。

运营者要求旧域不再跳转：当前 apex/www 由 Worker 返回 410，但 `next.bmt.news` 仍是旧绑定，不能写成所有旧入口已清理。本机 `bmt-news-dns-observed.json` 仅保存上述三个已观察到的 DNS 记录，不是完整区域导出或所有 Cloudflare 设置备份。浏览器下载权限提示未授权，因此没有宣称已成功导出 BIND 文件。

下一步是操作时确认后删除上述三个 Pages 自定义域及 `bmt.news` DNS 区域。旧地址可能变为解析或 TLS 错误，不再保证返回 410；域名注册及续费不受区域删除直接影响，原设置不会自动恢复。依据 [Pages 自定义域说明](https://developers.cloudflare.com/pages/configuration/custom-domains/) 和 [删除 DNS 区域说明](https://developers.cloudflare.com/fundamentals/manage-domains/remove-domain/)，删除后必须回读项目列表、区域列表和普通新主域，不把旧域失效当成新站成功。

## Telegram 与旧仓退役条件

运营者于 2026-10-02 报告 Bot 已更换，仍使用原频道且频道已改名。这是运营者报告，不是读取 Secrets、机器人身份或自然发送回执所得；本次未改 Token、目标 ID、话题、权限、信源或提醒规则，也不假设实时话题群和看门狗凭据同步更换。

更换 Bot 不证明原 Token 已在 BotFather 撤销。旧仓完整历史含疑似旧凭据，在收到撤销确认前不得上传本地 unsquashed 历史。须先完成安全历史导入、远端 CI 与合并，再通过原可信 SSH 入口从新主仓发布，核对完整 SHA、三个现货分片、下一条自然 `message_id` 和看门狗，最后按迁移计划归档旧仓。原请求要求保留 Git 历史；目前没有可安全删除旧仓的验收证据。

逐条部署步骤见 [服务器迁移清单](realtime-server-migration.md)，运行边界见 [系统架构](system-architecture.md)，Telegram 状态见 [品牌执行清单](telegram-brand-migration.md)。未经验证不归档或删除当前恢复源，不制造生产消息作为验收。
