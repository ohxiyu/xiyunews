# 2026-09-24 无成交 K 线补丁部署（PR #37）

部署状态：deployed
源码提交：ff21d4cb20bccbe343310e6d11d30b5b8e846f1d
运行版本：2.1.0 后端 systemd fomobtc，PID 159679，/opt/fomobtc/current 指向该 SHA 的 release；前端未变更。
验收结果：2026-09-24 19:54（北京时间）切换；公网 health source_commit 为目标 SHA，telegram_enabled=true；261 秒时 spot_stream_0/1/2 全部 live（361 对，趋势历史齐全，4 个上市不足 24h），/api/ready 503 仅因 Binance/Hyperliquid 公告降级。Telegram 由用户 16:38 以 setup_telegram.sh 启用：此前 100 条行情事件全部 sent，合并为 26 条 Telegram 消息，检测到发送 3.7–10.6 秒（含 3 秒合并等待）；API 回执不等于手机已读。
回退信息：上一 release 38194b2acad231ccc2ad72ae4131314a28071053 保留；备份 /opt/fomobtc/backups/20260924T115433Z-before-ff21d4c（SQLite integrity ok、env、previous_release）；依赖不变，沿用 98103447 虚拟环境链接。
授权记录：用户 2026-09-24 “telegram 已经配置，部署pr37”；未读取或输出 Token。

首次通过 stdin 传脚本时 SSH 被远端断开，核验脚本未执行（无备份、release 未变、服务正常）后改为上传脚本执行。上传包与本地 git 对象 SHA-256 一致，仅 signals.py、market.py 变化。
