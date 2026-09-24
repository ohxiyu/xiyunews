# 当前交接

## Current execution pointer
当前目标：隐藏交易对基线（本 PR）并观察 2.2.0 各交易所自然公告与新交易对推送。
任务 Issue / 负责人：本 PR / Claude；币安官方流（PR #40）已部署待自然公告验证。
工作分支 / 最后提交 / PR：fix/hide-pair-baseline；最终提交见 PR head；线上运行 bf62c640191cd08e0b447a6d4ba88f4c1bb182b1。
已经完成：2.2.0 已部署后端与 Cloudflare 前端；全部新来源在东京 polling，首轮基线无推送积压。
尚未完成：本修复部署；各交易所自然公告延迟与推送量观察；币安官方流毫秒对齐验证；24 小时稳定性；OKX/Hyperliquid 翻译。
已运行的验证及结果：2.2.0 部署：health 2.2.0/bf62c64，新来源全部 polling，前端 config.js 同 SHA；本修复 Python 79 项、Ruff 通过。详见 [部署记录](releases/deploy-20260924-exchanges.md)。
尚未验证的内容：生产东京 IP 下各新来源长期可用性与限流；新交易对推送量；币安官方流与官网副本的毫秒对齐。
线上版本 / 对应源码提交：后端 2.2.0 与前端均为 bf62c640191cd08e0b447a6d4ba88f4c1bb182b1。
阻塞与所需权限：合并与部署需用户授权；Upbit 韩国站、Gate、MEXC 公告 API 在东京 403，只能监测新交易对。
下一步具体动作：部署本修复后核验“全部交易所”只剩公告与真实新增交易对；观察一天推送量。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[2026-09-24 2.2.0 部署](releases/deploy-20260924-exchanges.md)。
