# 日报延迟与统一 Worker 自探测修复

Task: https://github.com/ohxiyu/xiyunews/issues/204。
Source commit: 修复前 main d1b53f10d58a73fed70a5e746606363cf3f9c5b3；修复 PR head 待创建。
Worker version: 修复前 3f034d1a-1bb8-4d37-ac4f-9c70f42e8a65，修复尚未部署。
Deployment: pending；用户本轮明确授权既有自动部署链路与正常补刊。
Verification: 2026-10-04T03:23Z production latest=2026-10-03；今日无 daily-summary 运行；ready=ready。完整修复验收待补。
Rollback: 已知修复前版本存在漏刊缺陷，不盲目回退；任何回退须授权且保留现用 RecoveryGate/STATE，不恢复旧调度者。

## 原因与证据

统一 Worker 接管后，原 recovery.getText 继续从调度器 fetch 正式域。该域此时由同一个 Worker 提供，生产子请求返回 HTTP 522，inspectPublication 在派发日报前中断。备用 Watchdog 和 Feed Collection 恢复也调用相同协调器，不能绕过此故障。

GitHub 备用失败运行37172343260、采集恢复失败37172247534。受保护共享检查诊断运行[37174085943](https://github.com/ohxiyu/xiyunews/actions/runs/37174085943)及 Workers tail 捕获 publication_check_failed / Publication probe failed: HTTP 522。该诊断没有产生日报运行。权限探测可达，故不重配 Secret。

## 最小修复

- 统一入口为 HTTP 与 Cron 注入当前 website.fetch，同一处理器读取已部署 ASSETS；带 publication_check 查询绕过网站边缘缓存，不通过公网自请求。
- 独立旧调度器测试和外部网站仍使用原 fetch；不启用退役 Worker、不改 Cron、DO/KV、07:00/07:26 窗口、重试次数与租约。
- 额外捕获自然 03:30:51Z 计划回调在 03:31:23Z 执行，却未检查日报：原组合调度按实际分钟选择 cadence。改为按 scheduledTime 选检查时隙，再用实际时间判断刊期，防止迟到一分钟漏掉整次恢复检查；不增加检查频率。
- 仍逐项验证私有 gh-pages、当期首页、中英详情页、正文数量与内容 revision；不能把读取静态资产成功当全站发布成功。部署后的外部正式域验收另做。
- GitHub 协调器白名单状态进入普通日志，避免只有笼统失败和需打开 summary；不打印异常、凭据或任意 URL。
- 回归覆盖公网自请求522时缺失日报可派发、已发布可确认、旧正文不可确认，以及 HTTP/Cron 两入口使用同一本地探测。保留权限失败、共享锁并发、冷却和预算用例。

## 验证与尚未完成

uv sync --frozen --extra dev 成功；完整 pytest 1021 项通过（仅依赖的 Python 3.14 弃用 warning），npm check 含 102 项、类型、audit0 和 dry-run 通过；网站/后台/时间提示 Node 37 项通过，治理和 diff 检查通过。远端 CI、生产部署、自然 Cron 和当期内容回读待执行，未提前宣称完成。仅正常补跑缺失当期；不 force_publish，不手改 gh-pages、staging-cache、x-queue 或 square-queue，不清队列，不重启东京实时服务。
