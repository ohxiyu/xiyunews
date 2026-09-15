# 当前交接

## Current execution pointer
当前目标：Issue #29收敛前端与交接；后续主线是Telegram无头推送，停止前端视觉迭代。
任务 Issue / 负责人：[Issue #29](https://github.com/ohxiyu/fomobtc/issues/29) / ohxiyu；Codex实施。Telegram跟踪#4，中文翻译跟踪#19。
工作分支 / 最后提交 / PR：refactor/headless-focus，基于main 4d5fe75；[PR #30](https://github.com/ohxiyu/fomobtc/pull/30)。
已经完成：紧凑只读数据库表格；移除图表/市值展示与第三方脚本授权；停止市值轮询；更新agent.md、长期规则、Telegram运行手册。现货及公告采集、持久化队列与24小时去重继续保留。
尚未完成：最终合并状态以GitHub为准；Telegram Token和Chat ID未配置，未真实推送；自动翻译服务未配置；Telegram行情消息尚有英文技术说明，需后续统一文案。
已运行的验证及结果：46项Python测试、Ruff/Mypy、前端回归及构建通过；安全检查只输出凭据是否存在，确认两项均缺失且TELEGRAM_ENABLED=false。
尚未验证的内容：手机收件、自然事件自动发送、24小时稳定性及端到端P95/P99。
线上版本 / 对应源码提交：前后端185fabf590abe65cf7f943433d85a9ce69889d13；Worker 6c0c0a6d-59e7-4338-a1f3-796633a6134f。
阻塞与所需权限：沿用SSH及合并部署授权；需要用户提供Telegram配置安全位置。服务器位置/etc/fomobtc.env，root0600，密钥不能写聊天或git。
下一步具体动作：部署已验证，完成PR #30合并；获得配置后按Telegram运行手册核验Bot/目标、启用单实例、测试收件并观察自然事件，不能重置队列或补发历史。

运行资料：[Telegram运行与验收](telegram-runbook.md)。本轮证据：[无头服务收敛](releases/headless-focus.md)。

生产路径：/opt/fomobtc/current，SQLite /var/lib/fomobtc/fomobtc.sqlite3，systemd fomobtc，API https://api.fomobtc.com。SSH配置见运行手册。虚拟环境依赖9810344 release，不能删除该目录。
