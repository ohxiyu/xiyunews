# 公告正文与简讯

Issue #17：独立后台任务补全正文和提取原文句子简讯，持久化到附加表，不改原事件、去重摘要和通知状态。OKX 官方详情限2MB、10秒超时、禁止重定向，正文失败每小时重试。每轮最多100条，每条间隔1秒，每15秒取待处理记录。Hyperliquid/Binance复用原有正文，缺少Binance凭据时不会虚构文章。简讯为原文摘录而非翻译，最多700字符，前端两行预览、可展开完整正文。已有公告自动补全，网页15秒轮询可见。

验证与实际部署结果见PR。

生产验收 2026-09-14：前后端源码3ebdddd08f13f8093824b15d4ec480028e1bf398；Worker ed98cd61-a2d5-4e25-80bf-e666be70fa08。数据库备份/var/backups/fomobtc/pre-content-1789392618.sqlite3，integrity_check=ok。东京服务NRestarts=0，MemoryCurrent=51838976。40条已有公告全部ready且有brief（OKX20、Hyperliquid20），FLOCK正文1773字符且状态仍baseline。页面验证简讯预览、展开正文与来源链接通过。43项Python测试、Ruff/Mypy、前端构建/交互回归及初次CI全通过。

回退：后台恢复135894380f2a745e63655c1648762f9196c0cab6，前端恢复d655fc8；保留新增附加表和历史数据库。Binance尚无凭据，未验证实际Telegram送达；不把正文补全称为自动推送。
