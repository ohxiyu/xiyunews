# 稀有News 系统架构

本文件描述当前实际架构，不把代码、合并、部署和验收混为一谈。项目统一名为 xiyunews，主仓为私有 ohxiyu/xiyunews，网站为 https://xiyu.news；PR195 已保留完整历史并入 realtime/，PR197 的默认关闭统一边缘基础已合并，生产接管进入 Issue198。实时服务器运行新仓 d6a9d3f 完整 SHA；@xiyunewsbot 为原群管理员，原话题保留、三个现货分片 live，已取得行情、公告和资金流向共 11 条自然成功回执。现役看门狗更新了机器人密钥，但原私聊目标、Cron、KV 未变，实际私聊告警另行验收。Cloudflare 仍是三个现役项目，统一入口未部署；见 [当前交接](handoff.md) 与 [单项目清单](cloudflare-single-project.md)。

## 1. 总体结构

系统有三个分离的部分：GitHub Actions 执行采集、分析和定稿；Cloudflare 提供网页、只读接口、后台认证与调度；东京服务器运行实时提醒。网站不是在浏览器里调用 AI，也不是实时行情前端。实时服务只通过自己的 Telegram 话题群输出，不混入日报频道或首页。

```mermaid
flowchart TD
    Sources[公开新闻、交易所公告与其他已配置来源] --> Collection[GitHub Actions：四小时采集]
    Collection --> Analysis[Python：规范化、去重、新内容分析]
    Analysis --> Stage[staging-cache：候选与分析缓存]
    Analysis --> Events[持续事件更新]
    Stage --> Edition[每日 07:26：定稿中英文日报]
    Edition --> Published[gh-pages：网页、归档、JSON、RSS]
    Events --> Published
    Published --> Pages[Cloudflare Pages + Pages Worker]
    Pages --> Readers[xiyu.news 网页 / PWA / 只读 API]
    Edition --> DailyTG[日报 Telegram 频道]
    Edition --> Plans[X / Square 持久化发送计划]
    Plans --> Delivery[独立 GitHub Actions：检查点后发送]
    Clock[Cloudflare 调度器：Cron + 恢复协调] --> Collection
    Clock --> Edition
    Clock --> Delivery
    Owner[单账号编辑者] --> Access[Cloudflare Access 验证码登录]
    Access --> QuickPost[Pages Worker：Quick Post]
    QuickPost --> Editorial[私有仓固定编辑文件与图片]
    Editorial --> Pages
    Editorial --> Published
    Realtime[东京 systemd：独立实时监测] --> SQLite[SQLite：状态、去重与发送队列]
    SQLite --> TopicTG[实时 Telegram 话题群]
    Realtime --> ReadAPI[api.fomobtc.com：只读健康接口]
    Watchdog[既有实时看门狗 Worker] --> ReadAPI
```

图中是当前部署结构。realtime/ 已整合代码管理与独立 CI，但不合并运行进程、依赖、数据库或 Telegram 目标；未来单个 xiyunews Worker 将合并图中的 Pages、边缘后台、Clock 和 Watchdog，东京实时系统保持原部署方式。

## 2. 模块与部署边界

| 模块 | 代码入口 | 执行位置 | 主要职责 |
| --- | --- | --- | --- |
| 内容管线 | src/main.py、src/orchestrator.py、src/scrapers/、src/ai/ | GitHub Actions 的 Python 任务 | 采集、去重、评分、选稿、翻译和扩写；缓存有效结果。 |
| 网页与公开数据 | docs/、Jekyll 模板、src/orchestrator.py、src/site_pages.py、src/weekly.py | Actions 生成，Cloudflare Pages 构建 | 日报、连续信息流、事件线、实体、周报、订阅与 JSON 输出。 |
| 站点边缘层 | docs/_worker.js | Cloudflare Pages 的 Workers 运行时 | 内容协商、接口路由、缓存、旧域停用、Quick Post 读写及认证校验。 |
| 独立调度器 | ops/daily-dispatcher/src/ | Cloudflare Cron + 既有 RecoveryGate Durable Object | 检查日报缺失、受限补发、四小时采集和分发到期门控。 |
| 人工编辑 | src/quick_posts.py、data/editorial.json、站点后台 | Access 保护的 /s/ 与 Pages Worker | 不调用 AI 的快速发布，保留人工编辑身份和原始内容。 |
| 社交分发 | src/x_queue.py、src/services/x_delivery.py、src/square_plan.py、src/square_delivery.py | 独立 GitHub Actions | 持久化计划、到期发送、保留回执，未知结果不自动重发。 |
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
| 东京 SQLite | 实时监测状态、去重和消息队列 | 实时服务独立管理，不由网站或日报读写。 |

### 3.3 Quick Post

编辑者先通过 Access 的单账号验证码登录，再由 Pages Worker 验证 JWT、允许身份、目标域、同源请求和输入格式。内容写入私有仓的固定位置，图片使用内容哈希标识；公共 Quick Post 接口即时读取编辑结果，正常 Actions 再生成静态页面。读取失败必须明确报错，不能以旧内容伪装发布成功；后台、写接口和鉴权响应不进入公共缓存。

### 3.4 Telegram、X 和币安广场

日报频道与实时话题群是两个独立目标。X 按当天选定故事生成持久化计划，后续任务依据前次实际发送时间计算间隔；币安广场使用自己的每日计划。发送前先写 pending 并成功持久化，收到确定回执再记 sent；超时、结果不明确或进程中断进入 unknown，禁止自动重发。

Worker 每五分钟只读私有队列判断是否需要启动任务，不直接访问发帖接口、不持有社交发帖凭据。未到期则 idle，X 与广场独立派发；正常发布事件和小时级 GitHub schedule 保留备用。平台同时故障时仍可能延迟，不能用无限重试或清空队列“恢复”。

## 4. 网页、缓存与域名

Cloudflare Pages 从 gh-pages 构建生产站，main 和代码分支用于预览。状态分支 staging-cache、x-queue、square-queue 不应触发网站预览，以免消耗构建次数且生成无意义失败。HTML、公开 API、订阅和静态资源有不同的缓存期限；新部署成功后，旧边缘缓存可能短暂保留，验收必须回读普通主域链接，不能仅验证带查询参数的请求。

PWA 的离线内容可能不是最新一期，必须显示保存状态并保留匹配的资源版本。后台、凭据、私有接口不允许离线缓存；域名改变后浏览器 origin 改变，原收藏、草稿和安装状态不能假定自动迁移。只在新域安装和使用后台。

运营者取消旧域跳转，并于2026-10-02操作时确认后删除bmt.news DNS区域及三个旧Pages绑定，面板回读确认不存在；新域绑定与DNS保留。旧地址可能解析或TLS失败，不保证410；没有删除域名注册，也不会远程清空旧安装缓存。旧Horizon已删除，但生产Pages、调度器和看门狗须等统一项目真实验收后退役，详见 [旧资源清单](legacy-resources.md)。网页站名xiyu.news、中文品牌稀有News，公开联系仅 [X @ohxiyu](https://x.com/ohxiyu)。

## 5. 安全、成本与运维

密钥只在 GitHub Secrets、Cloudflare Secrets 和服务器环境文件中使用，不进入 Git、浏览器脚本、公开 API、架构图或日志。私有仓内容通过鉴权 Contents API 读取，禁止带凭据跟随第三方重定向；内容与模型返回都是不可信输入，保留 URL 校验、输出转义和输入限制。Access 与 Worker 双重校验，私有仓不能代替撤销已泄露凭据。

主要可变成本是 AI 输入/输出、私有 Actions 执行时间、网站 Worker 请求和既有服务器。有效缓存降低重复分析；到期门控降低空 runner；Quick Post、普通阅读、调度检查和实时规则不因每次动作调用 AI。它们不等于系统总成本为零；当前没有新增付费套餐，实际账单和剩余额度需在各平台核实。

日报恢复使用按刊期命名的 Durable Object 租约、重试预算与冷却期；先确认产物，再确认生产页面，产物有而页面未更新时优先处理部署，不重跑 AI。采集、缓存持久化、Pages 构建、社交回执和实时健康必须分别验收。/health 可用不等于完整就绪；实时 Hyperliquid 的既有降级会使 ready 失败，不能隐藏或写成迁移后全部正常。

当前套餐不能提供私有仓分支保护和 CodeQL 授权，未购买升级；已有 CI、依赖审计、治理和整合负责人的 main/检查核对继续执行，但不能宣称等价于平台强制保护。每个变更仍保持一个 Issue、一个 agent 分支和一个 PR，部署后的真实证据以文档 PR 回写。

## 6. 尚未完成的迁移依赖

1. 旧Token撤销已获运营者明确确认，完整历史已合并为PR195；不能继续把此项写成阻塞。Cloudflare单项目还缺安全配置、状态/域名切换与实际自然运行证据。
2. 专用SSH已恢复，实时服务已按原路径备份并切换到新仓完整合并SHA；源码、单进程和三个现货分片已验证，但自然回执未通过。原release和备份保留，待业务验收后再退役旧仓；不改数据库、systemd、规则或目标群。
3. 运营者报告日报Bot已换、原频道改名；只读实查实时群名为xiyuNews，@fomobtcbot凭据有效但在禁止普通成员发消息的群中只是member。需要群管理员恢复其管理员发消息权限，再观察新的自然message_id；不补发失败消息。看门狗未检查Bot群权限，其无告警不能当作送达证据，新品牌Worker代码未部署。
4. 新域后台的匿名登录入口已恢复；验证码登录后的 Quick Post 读写仍须验收，不发布生产测试新闻或绕过认证。

以上限制不是新的技术架构，只是尚未满足的安全与运营条件。逐条命令见 [实时服务器迁移清单](realtime-server-migration.md)，实际结果见 [服务器部署记录](../realtime/docs/releases/deploy-20261002-xiyunews-repository.md)，待确认文案见 [Telegram 品牌草案](telegram-brand-migration.md)；操作清单和品牌草案不是执行证据。后续仍沿用这三个独立运行边界，不为了迁移引入额外系统。
