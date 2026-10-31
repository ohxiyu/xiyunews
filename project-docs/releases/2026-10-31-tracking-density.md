# 2026-10-31 事件追踪阅读优化

任务：[Issue305](https://github.com/ohxiyu/xiyunews/issues/305)，分支 agent/tracking-density。当前会话唯一编辑与整合负责人；运营者明确要求直接优化并部署，沿用 PR 检查通过、同步 main、正常自动发布流程。

## 行为与范围

追踪首个重点事件显示最近 10 条不同进展，其他事件显示 3 条，不足时全部展示；完整历史与稳定 update_id 锚点保留。重点资格、上限六个、Crypto 优先和置信度标准不变，选中事件改按最近实质进展倒序展示。首页保留重大且近期事件的重点资格，展示该事件最近 3 条完整进展，每条可直接打开对应详情节点。

详情页正文和右侧节点导航统一按发生时间倒序，序号为当前阅读顺序，不改写事件目录与 API 的历史顺序。时间线改为同一面板内连续行，保留浅分隔与连接线；圆点移到日期旁的独立轨道，不遮挡日期；手机预览的类型和正文共用内容列，避免三列挤压阅读。保留事件概览、来源、纠正样式、原生折叠和无 JS 阅读。

src/tracking_republish.py 原来只刷新索引，现同时从受信的出版目录重建中英文详情页，确保本次无需日报 AI 即可部署详情修改。不会重写 API、目录、合并跳转、数据库、发送回执或消息。资源版本随 CSS 改动同步更新，两份配置一致。

不改来源、AI 模型与调用、事件归属、费用、运行 Secrets、主域、Cron、实时服务或无关菜单；不手写 gh-pages、不重跑日报、不补发历史消息。既有审计策略待办不在本次授权范围。

## 验证与交付

- 代码：已实现，包括标题对齐、侧栏重复分隔线收敛；资源版本 sha256-a83a2ecb89e0。
- 测试：Python 1120 passed / 4 个既有 skipped；135 项 Worker、118 项网页 Node、类型、dry-run、npm 与 Python 安全审计 0 漏洞、治理均通过。数量、倒序、稳定锚点、重建保持 API/目录/跳转不变与模板转义有回归覆盖。
- 合并：[PR306](https://github.com/ohxiyu/xiyunews/pull/306) 于 2026-10-31 18:32:58Z 合并，完整远端 CI 通过。
- 部署：正常 Deploy Docs → 统一 Cloudflare 工作流均成功，未手写产物分支或重新生成日报。
- 生产验收：2026-11-01 02:40–02:42 Asia/Shanghai，正式域数量、顺序、日期/圆点边界、手机/桌面明暗、无 JS 操作及版本回读全部通过。

Source commit: 0291c7ff86b56847ffbde20e756561bce381a242（PR306 合并 SHA）；改前 6eb1b9f1bb8af30417f5573cdf57e9c74ddc84e6。

Worker version: e20bf912-c89c-4ba1-85f5-df7fcdc85a67；Artifact 73fcbcc0aae9971a7841af04207da0e4e4d06e97；Build key 8fc37d581db0e32dd4b16b40be8c995e25b526b61df15d2ad97f5a13a1219203。

Deployment: [Deploy Docs41229957178](https://github.com/ohxiyu/xiyunews/actions/runs/41229957178)，2026-10-31 18:33:04–18:34:15Z success；[统一 Cloudflare41230062324](https://github.com/ohxiyu/xiyunews/actions/runs/41230062324)，18:34:20–18:40:01Z success（job 时间）。

Verification: 正式域 https://xiyu.news 的首页、/threads/、中英事件详情、/health、/ready、/api/latest.json 均可正常访问。普通 URL 回读 source/artifact/Worker 与部署一致，首页 CSS 指纹为 sha256-a83a2ecb89e0，未靠绕缓存参数验收。

## 正式域验收与完成状态

使用正式域执行中英 × 明暗 × 1440、390、320px 共 12 组浏览器检查：每组首卡 10 条、其余五卡各 3 条，首页重点同一事件最近 3 条；示例 evt_349ae44c04b4d209 的 43 个节点全部保留，发生时间倒序、导航与正文节点同序、稳定锚点可达。所有节点日期与圆点矩形均无重叠，节点无逐条圆角卡片或上边距，没有横向溢出或 pageerror。查看正式域桌面、手机截图确认连续面板、首页三条与索引排版正常。

390px 禁用 JavaScript 后再次验证首卡 10 条、首页 3 条、原生资料折叠通过 Enter 开关、首页链接通过键盘打开具体节点，全部通过。/ready 为 ready，/health 为 ok。latest 仍是 2026-10-31，generated_at 为 2026-10-30T23:31:35.388801Z；验收时为上海 11 月 1 日凌晨，尚未到 07:26 新刊生成时间，本次没有触发 AI、重跑日报或补发历史消息。

代码完成、测试通过、PR 合并、生产部署、生产验收五阶段均 complete。[Issue307](https://github.com/ohxiyu/xiyunews/issues/307) / agent/tracking-density-evidence 仅归档这些证据。手机检查是尺寸模拟，不是实机 PWA 安装测试；未来自然采集与下一刊生成没有纳入本次 UI 验收。

远端 [CI41220056184](https://github.com/ohxiyu/xiyunews/actions/runs/41220056184) 最终 attempt 2 全部成功，包含治理、主项目测试、web、realtime Python 3.11/3.12 及 edge-build。edge-build 首次在 30 分钟上限取消；日志已输出 Jekyll、资产检查与 dry-run 成功，等待任务结束后只重试该 job，最新 job124608102579 用时 26 分钟并成功，其余已成功检查未重复运行。此前 15 分钟取消及本次 30 分钟取消均保留在运行记录中，未绕过安全或页面检查。

## 本地真实归档与视觉证据

从 gh-pages 1494083f 导出完整出版快照，覆盖本次模板/CSS，执行 tracking_republish 重建后用 Ruby 3.3 / Jekyll 3.10 渲染整站成功。浏览器对中英 × 明暗 × 1440、390、320px 共 12 组检查：首页最新 3 条各有稳定节点链接，首卡 10 条、其他 3 条；详情 43 个节点全部保留、发生时间倒序、节点导航同序；每个节点日期矩形与圆点矩形无交叠，逐条卡片边框/圆角已移除，没有横向溢出或网页脚本错误。分类筛选、桌面节点导航和首页到具体节点点击成功，手机继续使用正文与首页锚点入口。

本地静态预览的 Quick Post API 由只读生产空列表快照提供，用于还原正常页面显示；不代表后台编辑验收，也没有写入 Quick Post。自动化浏览器检查不是实际手机 PWA 安装测试，本次未改变 PWA 协议或离线行为。

## 合并前安全依赖前置修复

当前 main 的 Python 锁文件在全 extras 审计中报告 4 个包的已知漏洞，会阻止本次 PR 合并。仅通过 uv 的锁定更新补齐 aiohttp 3.14.4、Brotli 1.2.1、certifi 2026.10.18、pyasn1 0.6.5；aiohttp 的约束同时要求传递包 yarl 1.25.1。两份锁文件包名/版本集合对比确认只更换上述五个版本，不合并独立 Dependabot PR 的其他升级，不改 pyproject、Python 支持范围或实时项目依赖。

依据：[aiohttp 公告](https://github.com/advisories/GHSA-2g87-pp6c-29x5)、[Brotli](https://pypi.org/project/brotli/1.2.1/)、[certifi](https://pypi.org/project/certifi/2026.10.18/)、[pyasn1](https://pypi.org/project/pyasn1/0.6.5/)。更新后 all-extras pip-audit 为 No known vulnerabilities found，完整 pytest 再次 1120 passed / 4 skipped，未降低或跳过安全检查。

## 服务器构建时限前置修复

CI41216824913 的治理与 web 通过，但 edge-build124584577445 在 2026-10-31 16:13:47–16:28:56Z 达到 15 分钟上限而取消。约 10 分钟用于两次精确 checkout，随后 Ruby 依赖下载仍未完成，尚未进入 Jekyll，不是页面测试失败。原有生产 X 任务也曾因下载缓慢耗尽自己的时限；未手动取消、重启或改写发送状态。

仅把整站 CI 的 15 分钟和统一纯部署的 20 分钟总上限放宽到 30 分钟，保留 CPU/内存限制、全部检查与安全审计、串行执行和生产权限，不增加机器、并行或套餐。工作流变更按现有保守范围规则运行完整 CI，包括独立 realtime 的只测试任务（TELEGRAM_ENABLED=false），而不是绕过相关检查。

| 对比 | 截图 |
| --- | --- |
| 详情桌面改前（1440×1100） | [改前](images/2026-10-31-tracking/before-detail-desktop.png) |
| 详情桌面改后（1440×1100） | [改后](images/2026-10-31-tracking/after-detail-1440-light.png) |
| 详情手机改前（390×844） | [改前](images/2026-10-31-tracking/before-detail-mobile.png) |
| 详情手机改后（390×844） | [改后](images/2026-10-31-tracking/after-detail-390-light.png) |
| 首页重点三条（390×844） | [首页](images/2026-10-31-tracking/after-home-390-light.png) |

Rollback: 不自动回退。若发布失败保留当前生产版本并查看日志；任何回退或状态操作须按授权规则处理，不以重置数据库或发送回执恢复 UI。
