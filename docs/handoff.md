# 当前交接

## Current execution pointer
当前目标：推送已切换到 Telegram 群组话题；网页前端下线（本 PR）；观察首条自然资金流向与各话题推送；cex.top 待用户永久删除。
任务 Issue / 负责人：本 PR / Claude；cex.top 与 fomobtc Worker 删除由用户执行。
工作分支 / 最后提交 / PR：chore/remove-web-frontend；最终提交见 PR head；线上运行 1739fe3e97f077ed5d4e2dbe4ecb3cebbd55e7c6。
已经完成：2.5.0 资金流向与话题路由已上线；群组 fomobtc 三个话题已创建并切换推送；cex.top Cron 已移除、仓库已归档；前端源码删除。
尚未完成：用户删除 Cloudflare Worker fomobtc/cex-top*、D1 cex-top 与 cex.top 仓库；Solana 资金流向（需带 Key 的 RPC）；地址簿扩充；24 小时稳定性。
已运行的验证及结果：见 [部署记录](releases/deploy-20260925-flows-topics.md)；本 PR Python 91 项、Ruff、Mypy、仓库契约通过。
尚未验证的内容：首条自然资金流向推送；话题内手机显示；cex.top Cron 删除全网生效（15 分钟后复查）。
线上版本 / 对应源码提交：后端 2.5.0 运行 1739fe3e97f077ed5d4e2dbe4ecb3cebbd55e7c6；网页前端已下线（Worker 待用户删除）。
阻塞与所需权限：永久删除操作需用户本人执行；Solana 需非公共 RPC Key。
下一步具体动作：复查 cex.top 不再扫描；观察三个话题的自然推送；需要时扩充币安地址簿。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[2026-09-25 部署与群组话题](releases/deploy-20260925-flows-topics.md)。
