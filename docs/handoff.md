# 当前交接

## Current execution pointer
当前目标：2.5.0 资金流向并入与 Telegram 群组话题：部署，用户运行 setup_telegram_topics.sh 切换推送；确认后停用 cex.top Cloudflare Cron。
任务 Issue / 负责人：本 PR / Claude；cex.top 停用待用户确认。
工作分支 / 最后提交 / PR：feat/flows-and-topics；最终提交见 PR head；线上运行 47e47ece2bcf7d261e7f99fc4f3ab5d0623376e8。
已经完成：2.4.0 行情图片推送已上线并首条送达；2.5.0 本地完成，真实链上试跑通过。
尚未完成：2.5.0 部署；群组话题配置与收件；cex.top 停用；Solana 资金流向（需非公共 RPC）；地址簿扩充。
已运行的验证及结果：2.5.0：Python 91 项、Ruff、Mypy、前端检查通过；真实链上试跑 Arbitrum 扫出 800 万美元 USDC 流出，TRON/以太坊节点验证。
尚未验证的内容：生产各链检查点持续前进与落后块数；首条自然资金流向推送；话题路由实际显示。
线上版本 / 对应源码提交：后端 2.4.0 与前端均为 47e47ece2bcf7d261e7f99fc4f3ab5d0623376e8。
阻塞与所需权限：群组需用户创建并授予机器人管理话题权限；停用 cex.top 需用户确认；Solana 需带 Key 的 RPC。
下一步具体动作：合并部署后核验 flow_* 来源 polling 且落后块数下降，再由用户运行话题配置脚本。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[2026-09-24 2.2.0 部署](releases/deploy-20260924-exchanges.md)。
