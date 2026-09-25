# 当前交接

## Current execution pointer
当前目标：2.5.1 精简（删除旧 CoinSignal、未用模块、SSE/CORS、Telegram 账号监听模式）：合并部署；清理已合并分支与过时 Issue。
任务 Issue / 负责人：本 PR / Claude；cex.top 与 fomobtc Worker 删除由用户执行。
工作分支 / 最后提交 / PR：chore/remove-legacy；最终提交见 PR head；线上运行 1739fe3e97f077ed5d4e2dbe4ecb3cebbd55e7c6。
已经完成：2.5.0 与群组话题已上线；网页前端源码已删除；cex.top Cron 已停且仓库归档；2.5.1 本地完成。
尚未完成：用户删除 Cloudflare Worker fomobtc/cex-top*、D1 cex-top 与 cex.top 仓库；Solana 资金流向（需带 Key 的 RPC）；地址簿扩充；24 小时稳定性。
已运行的验证及结果：2.5.1：Python 74 项、Ruff、Mypy、仓库契约通过；此前见 [部署记录](releases/deploy-20260925-flows-topics.md)。
尚未验证的内容：首条自然资金流向推送；话题内手机显示；cex.top Cron 删除全网生效（15 分钟后复查）。
线上版本 / 对应源码提交：后端 2.5.0 运行 1739fe3e97f077ed5d4e2dbe4ecb3cebbd55e7c6；网页前端已下线（Worker 待用户删除）。
阻塞与所需权限：永久删除操作需用户本人执行；Solana 需非公共 RPC Key。
下一步具体动作：部署 2.5.1（新 venv）并核验来源与推送；用户执行 Cloudflare/cex.top 永久删除与服务器旧版本清理。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[2026-09-25 部署与群组话题](releases/deploy-20260925-flows-topics.md)。
