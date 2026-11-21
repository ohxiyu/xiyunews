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
- 合并：待 PR 与 CI。
- 部署：待正常 Deploy Docs → 统一 Cloudflare 工作流。
- 生产验收：待正式域数量、顺序、日期/圆点边界、手机/桌面明暗及版本回读。

Source commit: 改前 6eb1b9f1bb8af30417f5573cdf57e9c74ddc84e6。

Worker version: 改前 ae340dcf-0094-4edf-8baa-ba36a1689d08；Artifact 1494083fe3ba4c822a46b622549e839cbc669d94。

Deployment: pending。

Verification: 2026-10-31 改前浏览器截图与 health 核对，本次生产结果尚未验证。

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
