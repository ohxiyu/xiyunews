# 当前交接

## Current execution pointer
当前目标：部署无成交 K 线补丁（PR #37），使全部行情分片 live；随后用 scripts/setup_telegram.sh 配置 Telegram 私聊并验收。
任务 Issue / 负责人：PR #36 已合并部署、PR #37 / Claude；Telegram #4。
工作分支 / 最后提交 / PR：fix/trend-empty-bars；最终提交见 PR #37 head；线上运行 38194b2acad231ccc2ad72ae4131314a28071053。
已经完成：PR #36（剔除下架币、滞回与增量分片、就绪口径、Telegram 大盘合并、一键配置脚本）已合并并于 2026-09-24 部署；线上 382 对，分片 0/1 live。
尚未完成：PR #37 合并与部署；Telegram 私聊配置及真实推送；24 小时稳定性与真实行情准确率验收。
已运行的验证及结果：38194b2 部署：SQLite 备份 integrity ok，systemd active，公网 health 为目标 SHA；263 秒时分片 0/1 live，分片 2 因 USDPUSDT 无成交 K 线停在 warming。PR #37 本地 73 项测试、Ruff、Mypy 通过。
尚未验证的内容：PR #37 部署后分片 2 live；合并消息手机显示；宇宙变动时仅单分片重启的线上表现；24 小时连续稳定性。
线上版本 / 对应源码提交：后端 2.1.0 运行 38194b2acad231ccc2ad72ae4131314a28071053；前端仍为 f131fc0d8d0cc84f3ad7546aa904636208982c35（本轮无前端变更）。
阻塞与所需权限：Telegram Token 需用户在服务器上运行配置脚本输入；Binance/Hyperliquid 公告仍降级，/api/ready 因此仍为 503。
下一步具体动作：合并部署 PR #37 并核验三分片 live；用户运行 setup_telegram.sh 后观察自然事件合并推送。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[2026-09-24 覆盖修复部署](releases/deploy-20260924-universe-digest.md)。
