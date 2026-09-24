# 当前交接

## Current execution pointer
当前目标：行情覆盖修复（剔除下架币、滞回与增量分片、就绪口径）与 Telegram 大盘合并；随后 Telegram 私聊配置与真实收件验收。
任务 Issue / 负责人：本轮 PR（fix/burst-readiness-market-digest）/ Claude；Telegram #4。
工作分支 / 最后提交 / PR：fix/burst-readiness-market-digest；最终提交见 PR head；前次上线源码 f131fc0d8d0cc84f3ad7546aa904636208982c35。
已经完成：定位就绪率低的原因（统计口径、61 个下架币、宇宙变动全量重建），实现修复与 Telegram 行情合并；本地测试与真实行情 log-only 冒烟通过。详见 [验证记录](releases/universe-digest.md)。
尚未完成：本 PR 合并与后端部署；Telegram 私聊配置及真实推送；24 小时稳定性与真实行情准确率验收。
已运行的验证及结果：Python 72 项、Ruff、Mypy、仓库契约通过；本地 log-only 连接真实 Binance，宇宙 381 对、185 秒全部分片 live，/api/ready 200。
尚未验证的内容：生产部署后分片 live 与 /api/ready；合并消息手机显示；宇宙变动时仅单分片重启的线上表现；24 小时连续稳定性。
线上版本 / 对应源码提交：后端 2.1.0 与前端均为 f131fc0d8d0cc84f3ad7546aa904636208982c35（本轮未部署）。
阻塞与所需权限：部署需用户授权及东京服务器 SSH；Telegram Token 和 Chat ID 尚未配置；Binance/Hyperliquid 公告仍降级。
下一步具体动作：审阅合并本 PR，停服务备份 SQLite 后部署，核验 /api/health 分片 live 与宇宙数；再按运行手册配置 Telegram 私聊并验收合并消息。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[2026-09-17策略部署](releases/deploy-burst-trend-20260917.md)。
