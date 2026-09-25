# 当前交接

## Current execution pointer
当前目标：全部服务在东京服务器（含 fomobtc.com 跳转），Cloudflare 只做 DNS 与看门狗；观察推送与看门狗；待用户执行 cex.top 永久删除与服务器旧版本清理。
任务 Issue / 负责人：本 PR / Claude；cex.top 删除与服务器旧 release 清理由用户执行。
工作分支 / 最后提交 / PR：feat/single-host-watchdog；最终提交见 PR head；线上后端运行 8f1751ef7f7ce403007965ab136d039657420461。
已经完成：fomobtc.com/www 由 nginx 302 到群组并启用 HTTPS；Cloudflare 跳转 Worker 已删除；看门狗上线并配置凭据；群组成员只读。
尚未完成：用户删除 cex.top 的 3 个 Worker、D1 与仓库；服务器旧 release 清理；Solana 资金流向；地址簿扩充；24 小时稳定性。
已运行的验证及结果：见 [单机与看门狗记录](releases/single-host-watchdog.md)；看门狗 node 测试 3 项通过。
尚未验证的内容：看门狗真实故障提醒（需一次计划内停机或等待自然故障）；24 小时稳定性。
线上版本 / 对应源码提交：后端 2.5.1 运行 8f1751ef7f7ce403007965ab136d039657420461；nginx 与 scripts/deploy/nginx.conf 一致；看门狗 Worker 55671d87-29c2-4225-8bdf-176cb4712ed3。
阻塞与所需权限：Cloudflare DNS 修改需用户在后台操作（wrangler 登录无 DNS 权限）；永久删除操作由用户执行；Solana 需非公共 RPC Key。
下一步具体动作：可安排一次计划内短暂停机验证看门狗提醒；观察三个话题的自然推送。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。

本轮部署证据：[单机运行与看门狗](releases/single-host-watchdog.md)。
