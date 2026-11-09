# 日报调度与部署

统一 `xiyunews` Worker 是日报调度入口，配置在 `ops/daily-dispatcher/wrangler.unified.jsonc`。沿用既有RecoveryGate命名空间和迁移，不创建第二个调度器。独立realtime看门狗保持原样。

## 时间和恢复

业务时区Asia/Shanghai，窗口为[前日07:00，当日07:00)，07:26启动，目标约07:30可见。显式edition_date绑定窗口，不能用补跑时间改变刊期；07:30是目标而非保证。

UTC Cron保持 `26 23 * * *`、`36,46,56 23 * * *`、`*/5 * * * *`。07:26主派发；07:36/46/56、08:00–11:50每十分钟、12:00–23:00每小时整点检查。Worker验证原始API、中文出版稿、生产API、首页及日期页的期号、条目数和revision；内部读取部署资产避免自fetch，外部DNS/TLS另行验收。

按刊期持久租约最多两分钟；日报最多3次、部署最多2次，分别冷却30分钟。先记预算再请求，即使超时也不立即重发；运行中任务不叠加。任务45分钟以上卡住需调查，不能自动取消或删锁。已有选稿但页面未确认时留15分钟部署窗口，再触发只构建静态快照的Cloudflare任务，不重跑AI。既有日报不能force覆盖。

`POST /publication/check` 仍为既有受保护恢复入口，使用Bearer恢复凭据；GET/查询参数不能触发。精确变量 `XIYUNEWS_EDGE_ENABLED=true` 才启用统一链路，密钥缺失不回退或直接派发。删除GitHub旧watchdog/telegram-recovery/publication-state任务；不伪称有独立第三方备用时钟。

## 后台采集

Feed Collection由Worker每五分钟检查，GitHub五分钟schedule备用。新近采集或任何活动任务不叠加；失败30分钟冷却，同一失败运行共享两次派发预算。实际频率受队列与采集耗时影响。

`src.rolling_feed` 现仅是兼容的后台入口名：采集→缓存评分→语义去重→保存已合格候选。它不扩写、不公开HTTP写入、不重建站点、不写gh-pages、不发读者消息。使用独立并发组，合并staging-cache最新数据与分析键，Git非快进拒绝覆盖。保留原缓存时限、条数和AI预算。

## 单一部署和投递

共五个业务工作流：feed-collection、daily-summary、daily-telegram、x-distribution、cloudflare-unified；另有CI、CodeQL和server-backup。

Daily Edition只在新刊期生成选稿、中文静态稿与JSON，持久化并发布gh-pages快照。成功后Cloudflare任务读取固定出版快照，复用已核验缓存，叠加当前模板、Jekyll渲染、精简并校验公开资产，然后部署同一Worker。源代码改动也走这个任务，不另用deploy-docs。

部署后从真实正式域读取health、latest、首页和日期页，核对构建键、artifact、完整API与文章revision。验证失败不产生可投递凭证。每日出刊凭证绑定原始producer报告字节与选稿字节SHA256、原始run_id、source/artifact、期号及验证时间；纯代码部署没有每日run_id。

Telegram只监听Cloudflare成功，读取该部署的精确凭证和上游原始报告；要求当日期号、匹配hash、非重建新刊、首个运行attempt以及持久一次性回执。HTTP前落盘unknown，未知结果不自动重发。普通代码部署与历史修复不发消息。运维摘要也须等真实生产验证通过。

## 运维与验证

运维告警发到指定“日报运维”话题，使用DAILY_TELEGRAM_BOT_TOKEN及专用chat/thread绑定，与realtime的bot/告警目的地隔离。07:45未检测到当期和采集超过30分钟告警；同故障去重，恢复后开新故障周期。余额检查已按用户要求取消，保留实际token费用估算。

`/health`报告版本但不证明自然Cron已运行；`/ready`检查现有Actions写/Contents读权限，不生成真实任务。生产声明需核对真实运行、正式域和版本；两天自然出刊及七期质量验收只能在时间经过后记录。

所有生成分支只由Actions写入。部署使用 `--keep-vars`，保留既有Secret与独立看门狗配置。不以关闭安全控制、删回执、恢复旧服务或无限重试解决故障。回滚或暂停另需明确授权。
