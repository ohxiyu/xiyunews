# 当前交接

## Current execution pointer
当前目标：2.4.0 行情图片推送（K 线 + 双语 + 市值）：合并并部署（新依赖，独立 venv）。
任务 Issue / 负责人：本 PR / Claude。
工作分支 / 最后提交 / PR：feat/market-chart-push；最终提交见 PR head；线上运行 c36d67194ce841f71762d4323fef82806e84a636。
已经完成：2.3.0 双语摘要已上线；2.4.0 本地完成并用真实 K 线渲染核验。
尚未完成：2.4.0 部署与首条自然行情图片推送手机验收；2.3.0 自然公告中文推送/编辑验收；24 小时稳定性。
已运行的验证及结果：2.4.0：Python 87 项、Ruff、Mypy、前端检查通过；真实 ZEC 1m 图约 0.3 秒、24KB。
尚未验证的内容：生产 sendPhoto 送达与手机显示、东京服务器绘图耗时与内存。
线上版本 / 对应源码提交：后端 2.3.0 与前端均为 c36d67194ce841f71762d4323fef82806e84a636。
阻塞与所需权限：合并与部署需用户授权；Upbit 韩国站、Gate、MEXC 公告 API 在东京 403，只能监测新交易对。
下一步具体动作：合并后在服务器为新 release 建独立 venv 安装锁定依赖，切换并观察首条自然行情图片推送。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[2026-09-24 2.2.0 部署](releases/deploy-20260924-exchanges.md)。
