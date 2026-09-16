# 当前交接

## Current execution pointer
当前目标：Issue #31，前端与 Telegram 并行；先完成 bmt.news 风格 UI。
任务 Issue / 负责人：[Issue #31](https://github.com/ohxiyu/fomobtc/issues/31) / Codex；Telegram #4，中文翻译 #19。
工作分支 / 最后提交 / PR：feat/editorial-feed，基于 main 918d0f212fa775b36d9e96d73aa3626bf71613e9；[Draft PR #32](https://github.com/ohxiyu/fomobtc/pull/32)，实现提交ce70fc10cf292660a8c8bdba77823277c24099a5。
已经完成：核实 PR #30 已合并、#29 已关闭；用户新方向覆盖此前前端暂停规则；已实现暖白/深色信息流；按用户反馈移除大标题与介绍区、压缩留白，序号改采集与推送确认时刻；行情API补充notification_sent；按最新反馈公告仅标题/精简正文/关联币种，异动仅一句涨跌标题；左侧时分、不显示秒。筛选搜索与移动端样式保留。
尚未完成：CI；UI 生产部署；Telegram 私聊配置及真实推送；自动翻译服务。
已运行的验证及结果：Python 46项、Ruff、Mypy、compileall及仓库契约通过；前端回归（含转义/外链/交付状态）与构建通过；桌面和390px手机视觉、主题、搜索及50→100条分页验证通过。
尚未验证的内容：本轮生产版本、手机收件、自然事件发送、24小时稳定性及端到端P95/P99。
线上版本 / 对应源码提交：公开/api/health本轮报告2.1.0、185fabf590abe65cf7f943433d85a9ce69889d13、Telegram关闭；SSH/systemd尚未重新核验。Worker上轮记录6c0c0a6d-59e7-4338-a1f3-796633a6134f。
阻塞与所需权限：GitHub连接可用，CLI无认证；阿里云Workbench可连接东京实例，本机缺少SSH配置。机器人已创建、暂不加群；Token需用户写入服务器安全配置，不进聊天/git。
下一步具体动作：检查PR #32 CI，继续UI审阅与部署；用户私聊机器人/start，在服务器安全配置Token后核验目标与队列，再启用单实例和授权测试收件。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[阅读型信息流](releases/editorial-feed.md)。
生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，配置/etc/fomobtc.env（root0600），API https://api.fomobtc.com。虚拟环境依赖9810344 release，不能删除该目录。
