# 2026-09-17 突发/趋势策略部署

部署状态：deployed
源码提交：f131fc0d8d0cc84f3ad7546aa904636208982c35
运行版本：2.1.0，alert policy_version=2；前后端均已部署。
验收结果：systemd active/running、公网版本及策略字段一致、events API成功；前端域名、版本、跨域与浏览器实时数据通过；Telegram未启用。
回退信息：保留185fabf5旧release与/opt/fomobtc/backups/20260917T030340Z-before-f131fc0备份；单实例恢复。
授权记录：用户2026-09-17明确要求“已经登陆，上线。”，沿用部署授权；没有新增密钥或发送消息。

## 后端已部署
目标运行源码 f131fc0d8d0cc84f3ad7546aa904636208982c35（PR #34 已合并，原策略 CI 通过）。
东京实例通过已有阿里云命令助手执行，没有新增 SSH 密钥或更改网络权限。
旧服务 release 185fabf590abe65cf7f943433d85a9ce69889d13、PID 66842。

Workbench 文件传输检查未进入选择框，改为命令助手分段传送压缩内容。已核对 GitHub compare：旧生产到目标版本的运行差异文件为 app.py、delivery.py、market.py、signals.py、store.py 与 config/thresholds.yaml，共 6 个文件（5 个 Python，1 个配置）。从旧 release 复制到独立新目录，逐文件 SHA-256 校验为本地经过测试的内容，运行依赖未变，保留原虚拟环境链接。docs/web 不参与该后端增量运行部署。

- 准备命令 t-jpn6xatb7vesidc：退出码0，6文件哈希验证、compileall通过，旧服务未改。
- 切换命令 t-jpn6xatd8h4jmdc：2026-09-17 11:03:40–11:03:42（北京时间），退出码0。
- 停服务后 SQLite backup API 备份并 integrity_check=ok；备份目录 /opt/fomobtc/backups/20260917T030340Z-before-f131fc0，包含旧环境和 release 指针，权限700。
- 原子切换 /opt/fomobtc/current，更新 SOURCE_COMMIT；新 PID 91155，active/running。
- 公网 /api/health 回报目标 SHA，policy_version=2、突发900秒、趋势21600秒、按币种/类型/方向、需重新越线、允许突破追加。/api/events 返回成功。

Telegram 仍关闭，未发送任何消息；既有配置保留。Binance/Hyperliquid 公告仍轮询降级；部署成功不等于所有来源实时验收或手机收件。

## 前端已发布（2026-09-18）
用户再次明确“已授权”。现有OAuth缺少workers_scripts:write，补充该权限及zone:read后成功发布，未申请无关服务写权限。
以 API_ORIGIN=https://api.fomobtc.com、SOURCE_COMMIT=f131fc0d8d0cc84f3ad7546aa904636208982c35 构建并通过dry-run；wrangler deploy --keep-vars退出0，上传5个变更静态文件。
- 域名：https://fomobtc.com；Worker版本e86d3aef-1fe7-4f03-852b-a91d0991a6da。
- 12:37（北京时间）公网config.js HTTP200、revision与目标SHA一致，安全响应头存在。
- events API HTTP200，Access-Control-Allow-Origin=https://fomobtc.com。
- 浏览器显示实时连接、962条记录、HH:mm左侧时间、异动单行标题；自然事件包括ONE 1分钟下跌3.24%、SYRUP 24小时上涨8.10%、ZEC 24小时上涨9.99%突破24小时新高。
- 本次health运行时长22136秒，3587847条市场消息，2942549次有效计算，318个币种；快照中149个突发就绪、257个趋势就绪，仍不宣称全量覆盖。Telegram=false，通知未发送。
- 旧前端历史版本6c0c0a6d-59e7-4338-a1f3-796633a6134f保留为回退参考，回退前需核对Cloudflare版本记录。

## 回滚
旧 release 与虚拟环境未删除。激活脚本在切换失败时恢复旧环境/指针并重启；本次未触发回滚。数据库备份已保留，回滚不得盲目重放 unknown 或恢复旧发送队列。新策略完整准确率、真实ZEC回放与长期资源稳定性仍待验证。

启动202秒实测：29375条消息，2405次有效计算；82个币种近期成交且突发窗口就绪、254个趋势历史就绪，316个监控币种并未全部ready。部分缺失/低频币种预热及轮询公告降级使完整readiness验收未通过。未人为注入生产行情、未宣称自然预警准确率或Telegram送达。
