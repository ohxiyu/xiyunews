# 当前交接

## Current execution pointer
当前目标：2.2.0 多交易所公告/新交易对与网页两级分类：合并、部署后端与 Cloudflare 前端并验收。
任务 Issue / 负责人：本 PR / Claude；币安官方流（PR #40）已部署待自然公告验证。
工作分支 / 最后提交 / PR：feat/exchanges-and-feed-tabs；最终提交见 PR head；线上运行 290d373edc73babebb995abe54c122cc954f3aac。
已经完成：PR #36–#40 已合并部署（覆盖修复、大盘合并、K 线补平、Telegram 与币安只读 Key、币安官方流去重）；2.2.0 本地实跑全部新来源 polling。
尚未完成：2.2.0 合并与前后端部署；各交易所自然公告延迟与误报观察；24 小时稳定性；OKX/Hyperliquid 翻译。
已运行的验证及结果：2.2.0：Python 78 项、Ruff、Mypy、前端检查通过；本地 log-only 真实接口全部新来源 polling，基线 5686 条，UI 桌面与手机截图核验。
尚未验证的内容：生产东京 IP 下各新来源长期可用性与限流；新交易对推送量；币安官方流与官网副本的毫秒对齐。
线上版本 / 对应源码提交：后端 2.1.0 运行 290d373edc73babebb995abe54c122cc954f3aac；前端 f131fc0d8d0cc84f3ad7546aa904636208982c35。
阻塞与所需权限：合并与部署需用户授权；Upbit 韩国站、Gate、MEXC 公告 API 在东京 403，只能监测新交易对。
下一步具体动作：合并后部署后端并核验新来源状态，构建并发布前端（API_ORIGIN=https://api.fomobtc.com），观察首批自然公告推送。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[2026-09-24 无成交 K 线补丁部署](releases/deploy-20260924-trend-empty-bars.md)。
