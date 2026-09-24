# 当前交接

## Current execution pointer
当前目标：2.3.0 双语标题+摘要+要点（官方版本，无机器翻译）与 Telegram 新格式：合并并部署前后端。
任务 Issue / 负责人：本 PR / Claude。
工作分支 / 最后提交 / PR：feat/bilingual-summary；最终提交见 PR head；线上运行 6e3e76deac9f27bea96730e8e1cfc3b1490af686。
已经完成：2.2.0 多交易所与分类已上线；2.3.0 本地完成，演示库核验中英文界面与 Telegram 样例。
尚未完成：2.3.0 部署；自然公告的中文补发编辑、Binance 官方流毫秒对齐验证；24 小时稳定性。
已运行的验证及结果：2.3.0：Python 83 项、Ruff、Mypy、前端 7 组检查通过；本地真实接口构建演示库，OKX 中英文正文、Bybit/Bitget 中英文标题、Bithumb 原文标注均正确。
尚未验证的内容：生产中翻译晚到时 editMessageText 实际效果；Bybit/Bitget 中文列表与英文列表发布时间差。
线上版本 / 对应源码提交：后端 2.2.0 运行 6e3e76deac9f27bea96730e8e1cfc3b1490af686；前端 bf62c640191cd08e0b447a6d4ba88f4c1bb182b1。
阻塞与所需权限：合并与部署需用户授权；Upbit 韩国站、Gate、MEXC 公告 API 在东京 403，只能监测新交易对。
下一步具体动作：合并后部署后端（新表自动创建，events 增加 sent_lang/edit_state 列）与前端，观察首批自然公告的中文推送与编辑。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[2026-09-24 2.2.0 部署](releases/deploy-20260924-exchanges.md)。
