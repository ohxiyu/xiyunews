# 日报延迟与统一 Worker 自探测修复

Task: https://github.com/ohxiyu/xiyunews/issues/204。
Source commit: 71b3b16881999fa3578dc988f0066c785c772252，[PR205](https://github.com/ohxiyu/xiyunews/pull/205) 的合并提交；最终head d30fdf125d5faff1b51de5e64221d899e6ae36fb。
Worker version: 当期自动部署 1b668bd4-ebfd-4bdb-b944-03a408a6a905；修复首次部署f61af910-85c3-4ecc-bac5-7f2222665735，修复前3f034d1a保留故障证据。
Deployment: 用户明确授权，既有纯部署[37174629571](https://github.com/ohxiyu/xiyunews/actions/runs/37174629571)=success；源码71b3b168、初始资产1fefda76c1aea903871e0446055416c7d4b60b61，03:40Z正式域回读一致。
Verification: 2026-10-04T03:41Z自然派发，03:43:17Z生成12条，03:45Z自动部署成功，03:46Z正式域/API/中英正文全部匹配，03:47Z共享恢复healthy/200。本记录由Issue206独立文档任务维护。
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

uv sync --frozen --extra dev 成功；完整 pytest 1021 项通过（仅依赖的 Python 3.14 弃用 warning），npm check 含 102 项、类型、audit0 和 dry-run 通过；网站/后台/时间提示 Node 37 项通过，治理和 diff 检查通过。远端 CI、生产部署、自然派发和当期网站内容已核验。仅正常补跑缺失当期；不 force_publish，不手改 gh-pages、staging-cache、x-queue 或 square-queue，不清队列，不重启东京实时服务。

## 实际部署与自然恢复

最终head d30fdf12 的CI37174512609全部可用检查通过（test56秒、edge-build96秒、治理12秒）；Pages预览成功。CodeQL按私有套餐跳过，实时路径未变所以实时专属测试按设计跳过。合并前再次fetch/merge确认main同步，正常merge为71b3b168，无force push。

纯部署37174629571以--keep-vars完成，正式health source=71b3b168、version=f61af910、双开关true、07:00截止与原三Cron保持；ready返回原Actions写/Contents读权限。

自然Cron计划03:40:51Z在03:41:15.449Z执行，publication_check为daily_dispatched/edition_date2026-10-04/items0，真实日报[37174775715](https://github.com/ohxiyu/xiyunews/actions/runs/37174775715)创建于03:41:18Z，名称Daily 2026-10-04 via cloudflare-morning-check。没有手工直派日报、force_publish或改状态分支；自然跨分钟回调实证恢复了检查。因为当时已逾08:11，旧有overdue警示仍使该scheduled outcome=exception，不能将它误写为ok，也不能误判为未派发；请求已经成功且后续受原共享预算保护。看门狗watchdog:ok、采集fresh、X idle继续独立执行。

日报37174775715=success，generated_at=2026-10-04T03:43:17.666677Z。窗口仍为2026-10-02T23:00Z至2026-10-03T23:00Z（北京时间前日07:00至当日07:00）；256个候选、225分析缓存命中、31个未命中，最终12条，不把补跑时间当新闻窗口。

自动出版部署[37174881998](https://github.com/ohxiyu/xiyunews/actions/runs/37174881998)=success（03:45:19Z完成），源码71b3b168、出版f9b9fb3fe6f8fbbd3f9a237bb39f3b2b672148aa、版本1b668bd4正式health回读一致。外部正式域/api/latest.json与私有gh-pages JSON精确匹配；首页第一期和中英/2026/10/04/summary-{zh,en}.html重定向后均200、当期日期、12个article和逐条正文revision全部匹配。

既有共享恢复工作流[37175060909](https://github.com/ohxiyu/xiyunews/actions/runs/37175060909)=success，03:47:43Z普通日志healthy/HTTP200；Worker日志raw_ready/public_ready均true、items12，不创建额外日报。只读X队列首条sent/HTTP201，第二条planned，实际到期北京时间15:12:49；币安广场12条已有正常计划，当时无发送回执，不冒称全部发出。

## 剩余问题与权限边界

- 本次run-report.status=warning，而非全链路无警告。既有日报Telegram返回403：Forbidden: bot is not a member of the channel chat；目标日报频道成员/管理员关系需要运营者确认，非代码重试能修复。未修改Secret或频道权限，不重刊、不清队列、不反复发送。日报频道与东京实时话题群不能混用，手机收件未验收。
- Crypto合格主轨6/9、AI4条、政策2条；现有生产配置AI上限5而数据契约仍写3，属于原有策略/文档偏差，本次不擅自改配额或降低评分凑数。
- EN今日脉络未生成，但中英文新闻正文仍全部可读；报告另有edition_started_late=281分钟，诚实保留今天延迟记录。
- 自然日内派发与共享healthy已验证；明日07:26主触发尚未发生，不能以本次补跑代替明日验收。原Quick Post登录、旧资源退役、实时手机收件仍在其他任务，不扩大本次修复范围。
