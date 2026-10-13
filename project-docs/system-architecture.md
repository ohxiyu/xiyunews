# 稀有News 系统架构

本文件描述当前实际架构，不把代码、合并、部署和验收混为一谈。项目统一名为 xiyunews，主仓为私有 ohxiyu/xiyunews，网站为 https://xiyu.news；PR195 保留完整实时历史并入 realtime/，PR199 的最终业务配置已合并。2026-10-03，单个 xiyunews Worker 已接管网站、后台/API、日报调度和实时看门狗，原 RecoveryGate 与 KV 身份保留，旧 Pages 已解除主域、两个旧 Worker 已停用。东京实时服务仍运行新仓 d6a9d3f、原话题和三个现货分片，数据库和部署方式未变；自动部署、自然运行及登录后的后台验收分项记录，实际私聊告警另验。当前证据见 [接管记录](releases/2026-10-03-cloudflare-production-verification.md) 与 [交接](handoff.md)。

## 1. 总体结构

系统仍有代码/任务管理、计算执行和边缘服务三个职责。2026-10-13起，GitHub保存私有仓、工作流定义、Secrets、任务记录与产物分支，所有应用Actions任务由现有东京服务器专用自托管执行器计算；Cloudflare提供网页、只读接口、后台认证与定时派发。东京服务器同时保留独立实时提醒进程，两个用户/依赖/数据目录和发送目标分离；网站不是浏览器调用AI，也不是实时行情前端。运行位置变化不改变每日刊期、四小时采集或AI缓存规则。

```mermaid
flowchart TD
    GitHub[私有GitHub：代码 / 工作流 / Secrets / 任务记录] --> Runner[东京专用受限执行器：单任务排队]
    Runner --> Collection[Actions工作流：四小时采集，东京执行]
    Sources[公开新闻、交易所公告与其他已配置来源] --> Collection
    Collection --> Analysis[Python：规范化、去重、新内容分析]
    Analysis --> MainDB[独立出版SQLite：候选 / 缓存 / 报告]
    MainDB --> Stage[staging-cache：正常Actions导出的审计快照]
    Analysis --> Events[持续事件更新]
    Stage --> Edition[每日 07:26：定稿中英文日报]
    Edition --> Published[gh-pages：网页、归档、JSON、RSS]
    Events --> Published
    Published --> Build[固定输入校验：同版本跳过 / 已验证构建复用]
    Build --> Edge[统一 xiyunews Worker / Assets]
    Edge --> Readers[xiyu.news 网页 / PWA / 只读 API]
    Edition --> DailyTG[日报 Telegram 频道]
    Edition --> Plans[X / Square 持久化发送计划]
    Plans --> Delivery[东京执行独立Actions：检查点后发送]
    Edge --> Clock[同一 Worker：Cron + 原 RecoveryGate]
    Clock --> Collection
    Clock --> Edition
    Clock --> Delivery
    Owner[单账号编辑者] --> Access[Cloudflare Access 验证码登录]
    Access --> QuickPost[同一 Worker：Quick Post]
    QuickPost --> Editorial[私有仓固定编辑文件与图片]
    Editorial --> Edge
    Editorial --> Published
    Realtime[东京 systemd：独立实时监测] --> SQLite[SQLite：状态、去重与发送队列]
    SQLite --> TopicTG[实时 Telegram 话题群]
    Realtime --> ReadAPI[api.xiyu.news：只读健康接口]
    Edge --> Watchdog[同一 Worker：实时看门狗 + 原 STATE KV]
    Watchdog --> ReadAPI
    MainDB --> Backup[在线副本 / 一致镜像去重 / xz + age加密]
    SQLite --> Backup
    Backup --> Offhost[原私有Artifact / 本机隔离恢复]
```

图中是当前部署结构。Cloudflare 的同一个项目合并静态资产、边缘后台、Clock 和 Watchdog；realtime/ 仅整合代码管理与独立 CI，不合并运行进程、Python 依赖、数据库或 Telegram 目标。东京服务仍是独立单实例，网站没有增加实时行情前端。

实时 API 的新主域为 `api.xiyu.news`，DNS-only 直连东京；`api.fomobtc.com` 仅保留过渡，不再是看门狗目标。主站 `/health` 描述边缘服务，不能替代实时 `/api/health`。迁移实际阶段与验证见[接口迁移记录](releases/2026-10-05-realtime-api-domain.md)。

## 2. 模块与部署边界

| 模块 | 代码入口 | 执行位置 | 主要职责 |
| --- | --- | --- | --- |
| 内容管线 | src/main.py、src/orchestrator.py、src/scrapers/、src/ai/ | GitHub管理的Actions，东京自托管Python任务 | 采集、去重、评分、选稿、翻译和扩写；缓存有效结果。 |
| 网页与公开数据 | docs/、Jekyll 模板、src/orchestrator.py、src/site_pages.py、src/weekly.py | 出版 Actions 生成，统一部署 Actions 渲染，Worker Assets 提供 | 日报、连续信息流、事件线、实体、周报、订阅与 JSON 输出。 |
| 统一边缘层 | ops/daily-dispatcher/src/unified.ts，复用 docs/_worker.js | 单个 xiyunews Worker | 内容协商、接口路由、缓存、Quick Post、认证与两个定时组件。 |
| 调度与恢复 | ops/daily-dispatcher/src/ | 同一 Worker Cron + 原 RecoveryGate Durable Object | 检查日报缺失、受限补发、四小时采集和分发到期门控。 |
| 人工编辑 | src/quick_posts.py、data/editorial.json、站点后台 | Access 保护的 /s/ 与统一 Worker | 不调用 AI 的快速发布，保留人工编辑身份和原始内容。 |
| 社交分发 | src/x_queue.py、src/services/x_delivery.py、src/square_plan.py、src/square_delivery.py | 独立Actions工作流，东京执行 | 持久化计划、到期发送、保留回执，未知结果不自动重发。 |
| 实时提醒 | realtime/ | 东京 systemd 服务 fomobtc，已部署新仓合并 SHA | 三个币安现货分片、公告与链上监测，输出到独立话题群；@xiyunewsbot 为原群管理员，三类自然 API 回执已核验，手机收件另验。 |

前端仍是静态模板和原生 JavaScript/CSS，不是 React 应用，没有因为视觉调整引入一套前端组件服务。PWA 增加安装、离线阅读、阅读状态和更新提示，不新增服务器常驻进程；本站没有引入 D1、Redis、Kafka 或独立用户数据库。

## 3. 数据如何流动

### 3.1 四小时采集与每日定稿

Feed Collection 每四小时补采候选，复用有效分析结果，并对真实新进展更新事件线。每日刊期仍固定一次：上海时间 07:26 启动，内容窗口为前一日 07:00 至当日 07:00；07:26 是开始生成而非保证已可见时间。因此，“今天采集成功”不代表首页当天固定日报已经重写；事件线、候选暂存和日报是不同结果。

分析缓存的键包含来源输入、模型及相关分析规则。输入和配置没有变化、缓存有效时复用；新内容、修订内容、模型或规则变化、过期缓存仍可能调用 AI。系统不能承诺永远只付第一次的费用，也没有独立的生成后事实核验器；读者应核对原始来源，运行报告应如实记录扩写或翻译降级。

### 3.2 存储职责

| 位置 | 保存内容 | 写入方和边界 |
| --- | --- | --- |
| main | 应用、配置样例、治理文档与固定人工编辑数据 | 代码经 PR 合并；已授权后台只能写预定编辑文件和图片，不是任意代码代理。 |
| staging-cache | staging-items.json、analysis-cache.json | 正常管线的数据提交，保留父历史，不手动写、不 force。 |
| gh-pages | 已发布网页、日报状态、归档、事件与公开 JSON/RSS | 正常出版工作流生成；不与 main 混合、不手改。 |
| x-queue | X v2 计划、任务时间、状态与回执 | 分发工作流在发送前后持久化检查点。 |
| square-queue | 广场每日计划、发送结果与回执 | 独立分发工作流，已尝试任务不重新当作未发送。 |
| Actions cache / artifact | 缓存副本、机器可读运行报告 | 缓存可失效；报告用于核对采集、tokens 和执行结果。 |
| 主出版 SQLite | publication.sqlite3：缓存、staging、文档、投递检查点、200报告和400任务 | 可信main生产者；CI/PR/预览不启用业务库，未出版与不同Git快照冲突时保留双方并停止。 |
| 实时 SQLite | 原独立监测状态、去重和消息队列 | 实时服务管理，不由网站或日报读写。 |
| 加密备份 | 双库在线副本、完整SHA/表计数与部署版本 | 原128MiB/20%CPU单元，仅整理副本/等价镜像去重；xz preset3/age，8MiB/7版本/3天异机。 |

### 3.3 Quick Post

编辑者先通过 Access 的原单账号验证码登录，再由统一 Worker 复用原 handler 验证 JWT、允许身份、目标域、同源请求和输入格式。内容写入私有仓的固定位置，图片使用内容哈希标识；公共 Quick Post 接口即时读取编辑结果，正常 Actions 再生成静态页面。读取失败必须明确报错，不能以旧内容伪装发布成功；后台、写接口和鉴权响应不进入公共缓存，workers.dev 预览不能充当正式域后台。

### 3.4 Telegram、X 和币安广场

日报频道与实时话题群是两个独立目标。X 按当天选定故事生成持久化计划，后续任务依据前次实际发送时间计算间隔；币安广场使用自己的每日计划。发送前先写 pending 并成功持久化，收到确定回执再记 sent；超时、结果不明确或进程中断进入 unknown，禁止自动重发。

Worker 每五分钟只读私有队列判断是否需要启动任务，不直接访问发帖接口、不持有社交发帖凭据。未到期则 idle，X 与广场独立派发；正常发布事件和小时级 GitHub schedule 保留备用。平台同时故障时仍可能延迟，不能用无限重试或清空队列“恢复”。

## 4. 网页、缓存与域名

出版成功后，cloudflare-unified.yml 固定读取 main 与最新 gh-pages 的完整 SHA，Jekyll 渲染、资产安全校验、完整 npm audit 后部署同一个 xiyunews 项目；该步骤不采集、不调用 AI、不写状态分支。XIYUNEWS_EDGE_ENABLED 已设为精确 true，可信 main/成功出版/串行生产部署门槛保留；旧 Pages 仍暂时保留，但不再承载主域，不能将其预览构建作为新站上线证据。HTML、公开 API、订阅和静态资源有不同缓存期限，验收回读普通主域、版本与固定 SHA，而不是只检查带查询参数的请求。

PWA 的离线内容可能不是最新一期，必须显示保存状态并保留匹配的资源版本。后台、凭据、私有接口不允许离线缓存；域名改变后浏览器 origin 改变，原收藏、草稿和安装状态不能假定自动迁移。只在新域安装和使用后台。

运营者取消旧域跳转，并于2026-10-02操作时确认后删除bmt.news DNS区域及三个旧Pages绑定，面板回读确认不存在；新域绑定与DNS保留。旧地址可能解析或TLS失败，不保证410；没有删除域名注册，也不会远程清空旧安装缓存。旧Horizon已删除，但生产Pages、调度器和看门狗须等统一项目真实验收后退役，详见 [旧资源清单](legacy-resources.md)。网页站名xiyu.news、中文品牌稀有News，公开联系仅 [X @ohxiyu](https://x.com/ohxiyu)。

## 5. 安全、成本与运维

2026-10-13九项优化均已生产验收，见[完整记录](releases/2026-10-13-server-optimization-complete.md)。主缓存与staging采用独立SQLite，关系结果逐条落库、任务结束导出正常Git快照；publication-state.yml只读导入缺失状态并证明原样一致，重复迁移不覆盖现役库。来源替代只在主RSS失败时使用同发布者公开索引，headline-only不足仍延后，不以标题补造进展。

构建key绑定不可变产物SHA与相关代码/锁文件；缓存每文件SHA和完整集合先验证，无效重建，相同已上线输入跳过。完整252秒/复用96秒/同输入24秒分别实际验证。生成副本压缩9资源约33%、首屏后延迟布局，全文仍在DOM，保留现行密度/UI；不把文件字节当WebVitals。干净任务工作区与工具/凭据/业务状态分离，hook_completed仅表示清理结束，任务成功以GitHub实际结论为准。

guardian每分钟仅在服务已启用、失活、无任务、无维护暂停时启动执行器，最大3次/日且间隔30分钟；边缘恢复同样保留预算/冷却/活跃任务门控，不无限重跑AI或重启发送者。备份03:20上海、异机上传03:45上海，latest.tar.xz.age为现役导出，旧gzip加密文件保留兼容；实际6820048B双库异机恢复通过。只整理隔离副本，现役库不VACUUM，只有镜像与本次副本内容哈希相同才去重，较新镜像保留，全部活跃业务记录仍在库中。

运营者本机隔离解密并自动识别压缩，核对完整性/SHA/所有表计数后清明文，不启动第二发送者。限额超出停止，不静默减少业务数据或增加费用；未来自然故障未人为制造，手机模拟不是真机安装/收件。系统仍依赖GitHub控制面与单服务器，Quick Post登录后验收另列。

密钥只在 GitHub Secrets、Cloudflare Secrets 和服务器环境文件中使用，不进入 Git、浏览器脚本、公开 API、架构图或日志。私有仓内容通过鉴权 Contents API 读取，禁止带凭据跟随第三方重定向；内容与模型返回都是不可信输入，保留 URL 校验、输出转义和输入限制。Access 与 Worker 双重校验，私有仓不能代替撤销已泄露凭据。

主要可变成本是AI输入/输出、网站Worker请求和既有服务器，以及GitHub artifact/cache存储限额。现有私有Actions托管2000分钟已耗尽、预算保持0；应用执行已转自托管，按GitHub当前说明自托管执行不占托管分钟。有效缓存降低重复分析，到期门控降低空任务；Quick Post、普通阅读、调度检查和实时规则不因每次动作调用AI。不是系统免费，没有购买新服务器或付费升级，实际账单和剩余额度仍需分别核实。

东京新增无sudo权限的xiyunews-runner用户与单个systemd执行器，所有任务排队串行，CPU最多1核、内存768MiB硬上限/704MiB软线，512MiB交换缓冲；工具环境复用，Node/测试并发受限。每周维护只清专用旧执行日志与无用uv包缓存，不清AI分析或生产状态；原fomobtc进程不重启、凭据/数据库目录对执行器隐藏。只接受可信同仓PR，系统仍依赖GitHub控制面与单台服务器网络，不提供高可用保证；手册见[自托管执行器](self-hosted-runner.md)。

日报恢复使用按刊期命名的 Durable Object 租约、重试预算与冷却期；先确认产物，再确认生产页面，产物有而页面未更新时优先处理部署，不重跑 AI。采集、缓存持久化、Pages 构建、社交回执和实时健康必须分别验收。/health 可用不等于完整就绪；实时 Hyperliquid 的既有降级会使 ready 失败，不能隐藏或写成迁移后全部正常。

当前套餐不能提供私有仓分支保护和 CodeQL 授权，未购买升级；已有 CI、依赖审计、治理和整合负责人的 main/检查核对继续执行，但不能宣称等价于平台强制保护。每个变更仍保持一个 Issue、一个 agent 分支和一个 PR，部署后的真实证据以文档 PR 回写。

## 6. 品牌迁移的历史依赖清单

下列为2026-10-03迁移记录的历史条件，不能作为当前执行清单。2026-10-13本任务只核实服务器计算迁移、正常采集/恢复/分发与网站发布；旧资源、实际手机收件和登录后Quick Post验收以[当前交接](handoff.md)及对应记录为准，不由本次计算位置迁移推断完成。

1. 旧Token撤销、完整历史、安全凭据、原状态迁移和正式域切换均已完成，不再列为阻塞。原两个边缘Worker已停用，新统一Worker已启用原Cron；自动部署成功与自然运行证据须分别回读。
2. 专用SSH已恢复，实时服务已按原路径备份并切换到新仓完整合并SHA；源码、单进程、三个现货分片和三类自然回执均已验证，2026-10-03只读累计30条sent。原release和备份仍保留，手机收件与看门狗私聊实际告警另行验收；不改数据库、systemd、规则或目标群。
3. 日报Bot/原频道改名由运营者报告；实时已切换为管理员@xiyunewsbot，群名xiyu.news，原话题3/5/7不变，/start已核验，不再要求给旧Bot授权或重复/start。新品牌看门狗代码已在统一Worker部署，保留原KV，私聊目的地沿用原备份来源，未导出旧CF密文直接比对；无告警本身不是私聊送达证据，不制造故障或补发失败消息。
4. 新域后台的匿名登录入口已恢复；验证码登录后的 Quick Post 读写仍须验收，不发布生产测试新闻或绕过认证。
5. GitHub部署Secret和统一Worker8个业务Secret已补齐，自动部署开关已启用；旧项目与旧实时仓退役尚未执行，需确认新生产验收及旧仓独有工作。Access登录页仍有旧应用显示名，后续仅改名称，不把品牌更新变成权限变更。

以上限制不是新的技术架构，只是尚未满足的安全与运营条件。逐条命令见 [实时服务器迁移清单](realtime-server-migration.md)，实际结果见 [服务器部署记录](../realtime/docs/releases/deploy-20261002-xiyunews-repository.md)，待确认文案见 [Telegram 品牌草案](telegram-brand-migration.md)；操作清单和品牌草案不是执行证据。后续仍沿用这三个独立运行边界，不为了迁移引入额外系统。
