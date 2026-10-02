# 资产信息与内容页脚

Issue #27。每条内容显示正文、关联资产及当前USD市值、时间和原来源。公告按标题中的符号/名称自动匹配，可能误匹配；同名币种不猜测市值，缺失/缓存超过30分钟显示未获取。
CoinPaprika免费tickers由东京后台每600秒更新，UI显示上游更新时间；不是事件发生时的历史市值。一次请求共享缓存，不阻塞行情入库。匹配结果最多512项缓存。
TradingView官方Mini Chart按点击加载，BINANCE现货符号，当前1日走势，并非预警窗口截图；保留TradingView链接及不可用后备链接，旧合约不嵌入现货图。仅允许官方脚本和widget iframe来源。
测试：46项Python测试，覆盖名称/币种匹配、同名歧义及过期；Ruff/Mypy及前端构建回归。部署成功：前后端c1daf5cd496a7809f440cd57ccb1155a151040c4，Worker ed4d832f-b31b-418d-8b19-01e8c4445d59。线上仅spot；RED实际市值约41.1M，ASTR约65.3M，来源CoinPaprika及更新时间可见。浏览器TradingView REDUSDT折线绘制成功，原链接与时间页脚可见。过滤X-合约的单字母误匹配。
备份 /var/backups/fomobtc/pre-spot-timeline-1789446547.sqlite3，integrity_check=ok。PR #28合并状态以GitHub为准。
回退：后台0668d01，前端00b490b；新缓存无数据库迁移。保留9810344虚拟环境目录。
