# 日报调度与部署

统一 `xiyunews` Worker 是日报调度入口，配置在 `ops/daily-dispatcher/wrangler.unified.jsonc`。沿用既有RecoveryGate命名空间和迁移，不创建第二个调度器。

## 时间和恢复

业务时区Asia/Shanghai，窗口为[前日07:00，当日07:00)，07:26启动，目标约07:30可见。显式edition_date绑定窗口，不能用补跑时间改变刊期；07:30是目标而非保证。

UTC Cron保持 `26 23 * * *`、`36,46,56 23 * * *`、`*/5 * * * *`。07:26主派发；07:36/46/56、08:00–11:50每十分钟、12:00–23:00每小时整点检查。Worker验证原始API、中文出版稿、生产API、首页及日期页的期号、条目数和revision；内部读取部署资产避免自fetch，外部DNS/TLS另行验收。

按刊期持久租约最多两分钟；日报最多3次、部署最多2次，分别冷却30分钟。先记预算再请求，即使超时也不立即重发；运行中任务不叠加。任务45分钟以上卡住需调查，不能自动取消或删锁。已有选稿但页面未确认时留15分钟部署窗口，再触发只构建静态快照的Cloudflare任务，不重跑AI。既有日报不能force覆盖。

`POST /publication/check` 仍为既有受保护恢复入口，使用Bearer恢复凭据；GET/查询参数不能触发。精确变量 `XIYUNEWS_EDGE_ENABLED=true` 才启用统一链路，密钥缺失不回退或直接派发。删除GitHub旧watchdog/telegram-recovery/publication-state任务；不伪称有独立第三方备用时钟。

## 后台采集

Feed Collection由Worker每五分钟检查，GitHub五分钟schedule备用。新近采集或任何活动任务不叠加；失败30分钟冷却，同一失败运行共享两次派发预算。实际频率受队列与采集耗时影响。

`src.rolling_feed` 每半小时采集和去重，06:30 按相同流程运行。07:26 的日报任务统一评分，候选、评分与简版均写入现有私有出版状态。采集流程独立于网站发布和 X 分发。

## 单一部署和投递

共四个业务工作流：feed-collection、daily-summary、x-distribution、cloudflare-unified；另有CI、CodeQL和手动publication-runtime迁移/验证。11/17用户取消专属备份，server-backup已移除；正常批处理经验证后切标准托管计算，私有运行状态和互斥锁复用Cloudflare，东京执行器已退役，见[运行手册](self-hosted-runner.md)。

Daily Edition只在新刊期生成选稿、中文静态稿与JSON，持久化并发布gh-pages快照。成功后Cloudflare任务读取固定出版快照，复用已核验缓存，叠加当前模板、Jekyll渲染、精简并校验公开资产，然后部署同一Worker。源代码改动也走这个任务，不另用deploy-docs。

部署后从真实正式域读取health、latest、首页和日期页，核对构建键、artifact、完整API与文章revision。验证失败不产生可投递凭证。每日出刊凭证绑定原始producer报告字节与选稿字节SHA256、原始run_id、source/artifact、期号及验证时间；纯代码部署没有每日run_id。


## 运维与验证


`/health`报告版本但不证明自然Cron已运行；`/ready`检查现有Actions写/Contents读权限，不生成真实任务。生产声明需核对真实运行、正式域和版本；两天自然出刊及七期质量验收只能在时间经过后记录。

所有生成分支只由Actions写入。部署使用 `--keep-vars`，保留既有Secret与独立看门狗配置。不以关闭安全控制、删回执、恢复旧服务或无限重试解决故障。回滚或暂停另需明确授权。
