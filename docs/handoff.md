# 当前交接

## Current execution pointer
当前目标：Issue #33，重做现货预警：滚动突发异动与持续趋势。
任务 Issue / 负责人：[Issue #33](https://github.com/ohxiyu/fomobtc/issues/33) / Codex。
工作分支 / 最后提交 / PR：feat/burst-trend-alerts，基于 main 782e45341fdb0b41a00c0e3d3b567595a4d23d43；[PR #34](https://github.com/ohxiyu/fomobtc/pull/34)，实现提交 ee0e0071542640dbddad4892e89842471ecc997e；最终状态以 PR head 为准。
已经完成：UI PR #32 已合并；已实现突发/趋势双检测器、方向独立持久化去重、合并事件和一致中文标题。
尚未完成：生产部署；Telegram 私聊配置及真实推送。
已运行的验证及结果：新策略 Python 67 项通过；Ruff、Mypy、compileall、仓库契约、前端回归与构建通过；合成流→事件→通知格式链路通过。实现提交 ee0e007 的 GitHub CI（Python 3.11/3.12、前端）和 Repository contracts 已成功；最终合并状态见 PR #34。
尚未验证的内容：生产部署、真实 ZEC 回放、手机收件、24小时稳定性及端到端 P95/P99。
线上版本 / 对应源码提交：2026-09-17 公开 API 报告 2.1.0、185fabf590abe65cf7f943433d85a9ce69889d13、Telegram 关闭；仍是旧 86400 秒预警策略，不能视为新策略上线。
阻塞与所需权限：GitHub connector 可用；CLI 无认证；本机缺少服务器 SSH 配置；Cloudflare whoami 未认证、Safari 显示登录页；机器人 Token 未配置。
下一步具体动作：PR #34 最终检查与合并状态以 GitHub 为准；恢复 Cloudflare/服务器登录后部署并核验 policy_version=2；不能将本地验证称为线上生效。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。
