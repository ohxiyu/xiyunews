# 当前交接

## Current execution pointer
当前目标：PR #34 前后端上线已完成，继续 Telegram 私聊配置与真实行情验收。
任务 Issue / 负责人：Issue #33 已随 PR #34 合并关闭 / Codex；Telegram #4。
工作分支 / 最后提交 / PR：docs/deploy-burst-trend-20260917；运行源码 f131fc0d8d0cc84f3ad7546aa904636208982c35；PR #35 记录部署证据，最终提交见该 PR head。
已经完成：策略 PR #34 合并；67项Python测试与前端、GitHub CI通过；后端备份及切换；2026-09-18 Cloudflare前端发布并核验真实域名、API跨域与实时信息流。
尚未完成：Telegram私聊配置及真实推送；全部币种覆盖率、真实行情长期准确率与稳定性验收。
已运行的验证及结果：后端部署时systemd active/running；本次公网health为目标SHA、policy_version=2；前端config.js为同一SHA，events API HTTP200且CORS正确。浏览器显示实时连接，ONE突发下跌、SYRUP持续上涨、ZEC突破24小时新高等自然事件。Wrangler部署成功，版本e86d3aef-1fe7-4f03-852b-a91d0991a6da。
尚未验证的内容：全部币种就绪、手机收件、完整自然事件推送链路、24小时连续稳定性、真实ZEC历史回放准确率。
线上版本 / 对应源码提交：后端2.1.0与前端均为f131fc0d8d0cc84f3ad7546aa904636208982c35。
阻塞与所需权限：发布权限已解决；Telegram Token和Chat ID尚未配置；部分币种窗口未就绪，Binance/Hyperliquid公告仍降级。
下一步具体动作：安全配置Telegram私聊，先核验目标Chat ID再按用户授权验证收件；调查币种未就绪原因与公告覆盖，持续记录自然行情结果。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[2026-09-17策略部署](releases/deploy-burst-trend-20260917.md)。
