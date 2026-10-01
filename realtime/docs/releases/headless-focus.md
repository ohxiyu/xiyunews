# 无头服务重点与数据库查看页

Issue #29。网页恢复紧凑只读数据库表格，保留筛选、分页、状态和正文展开。去除图表、市值与展示专用外部脚本权限；后台停止辅助市值轮询及API匹配，不动业务数据和回执。
AGENTS.md明确无头Telegram优先；agent.md为接手入口；handoff.md保存当前事实；telegram-runbook.md记录配置、启用、去重、发送异常和真实收件验收。
测试：46项Python、Ruff/Mypy、前端刷新/筛选/文案回归和构建通过。Telegram凭据存在性检查为false，开关false；没有真实发送。
代码完成：是。测试通过：是。部署成功：前后端185fabf590abe65cf7f943433d85a9ce69889d13，Worker 6c0c0a6d-59e7-4338-a1f3-796633a6134f。线上仅spot，API无市值增强，浏览器8列表格与真实记录已验收。PR #30合并状态以GitHub为准。
备份/var/backups/fomobtc/pre-spot-timeline-1789447150.sqlite3，integrity_check=ok。
回退：前后端c1daf5c；无需数据库迁移或清空。
