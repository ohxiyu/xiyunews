# 当前交接

## Current execution pointer
当前目标：fomobtc.com 已跳转到 Telegram 群组、成员只读；观察三个话题自然推送；待用户执行 cex.top 永久删除与服务器旧版本清理。
任务 Issue / 负责人：本 PR / Claude；cex.top 删除由用户执行（fomobtc Worker 现为跳转，不删除）。
工作分支 / 最后提交 / PR：feat/domain-redirect；最终提交见 PR head；线上后端运行 8f1751ef7f7ce403007965ab136d039657420461。
已经完成：2.5.1 精简已上线；群组成员只读；fomobtc.com 302 到邀请链接；已合并分支清理、过时 Issue 关闭。
尚未完成：用户删除 cex.top 的 3 个 Worker、D1 与仓库；服务器旧 release 清理；Solana 资金流向；地址簿扩充；24 小时稳定性。
已运行的验证及结果：见 [域名跳转记录](releases/domain-redirect.md)；后端 2.5.1 health 正常，/api/stream 404，/api/events 200。
尚未验证的内容：首条自然资金流向推送；话题内手机显示；cex.top Cron 删除全网生效（15 分钟后复查）。
线上版本 / 对应源码提交：后端 2.5.1 运行 8f1751ef7f7ce403007965ab136d039657420461；fomobtc.com 为跳转 Worker c165e6c5-f2c9-4fab-a29a-c42089452c13。
阻塞与所需权限：永久删除（cex.top Worker/D1/仓库、服务器旧 release）需用户本人执行；Solana 需非公共 RPC Key。
下一步具体动作：观察推送；需要时扩充币安地址簿或接入 Solana。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[2026-09-25 部署与群组话题](releases/deploy-20260925-flows-topics.md)。
