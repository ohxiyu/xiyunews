# 当前交接

## Current execution pointer
当前目标：币安官方公告流推送修复（中英副本去重）部署并用自然公告验证延迟。
任务 Issue / 负责人：PR #36、#37 已合并部署 / Claude；Telegram #4 待用户确认手机收件后关闭。
工作分支 / 最后提交 / PR：fix/binance-stream-delivery；最终提交见 PR head；线上运行 ff21d4cb20bccbe343310e6d11d30b5b8e846f1d。
已经完成：剔除下架币、滞回与增量分片、就绪口径、无成交 K 线补平、Telegram 大盘合并及一键配置脚本全部上线；用户已启用 Telegram 私聊。
尚未完成：本修复部署；自然币安公告的官方流延迟与中英去重实测；24 小时稳定性；OKX/Hyperliquid 英文翻译。
已运行的验证及结果：ff21d4c 部署 261 秒时三个分片 live、361 对；启用后 100 条行情事件全部 sent，合并为 26 条消息，发送延迟 3.7–10.6 秒。详见 [部署记录](releases/deploy-20260924-trend-empty-bars.md)。
尚未验证的内容：手机端合并消息显示由用户确认；宇宙变动时仅单分片重启的长期表现；24 小时连续稳定性。
线上版本 / 对应源码提交：后端 2.1.0 运行 ff21d4cb20bccbe343310e6d11d30b5b8e846f1d；前端 f131fc0d8d0cc84f3ad7546aa904636208982c35（无前端变更）。
阻塞与所需权限：公告实时化需 Binance 公告 API Key 或 Hyperliquid 授权会话；/api/ready 因公告降级仍 503。
下一步具体动作：部署后等待下一条币安公告，记录官方流 detected 与 published 差值、Telegram 送达及官网副本升级。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[2026-09-24 无成交 K 线补丁部署](releases/deploy-20260924-trend-empty-bars.md)。
