# 2026-10-22 网站发布恢复

任务：[Issue293](https://github.com/ohxiyu/xiyunews/issues/293)。运营者要求修复网站仅更新到 20 日的问题；本会话唯一负责编辑、合并及正常生产发布。

## 根因与范围

10 月 21 日 Daily Edition [39515049970](https://github.com/ohxiyu/xiyunews/actions/runs/39515049970) 与 22 日 [39693448142](https://github.com/ohxiyu/xiyunews/actions/runs/39693448142) 均成功。调查时 gh-pages 为 14cee6f84b30567b95f6d07dee5d787320f8e79f，api/latest.json 为 2026-10-22、14 条；21、22 日中英文 Markdown 已存在，窗口正确。

生产网站 latest 仍是 2026-10-20、14 条。统一部署 [39711109423](https://github.com/ohxiyu/xiyunews/actions/runs/39711109423) 在 npm audit 失败：Vitest 4.1.11 的 @vitest/mocker 与 Vite 8.3.2 被新安全通告覆盖。审计阻止有问题的构建进入生产，并非采集或定时任务停用。东京磁盘可用 16 GB、无失败 systemd 单元。

最小更新 Vitest 至 4.1.12，并更新锁文件中的 Vite 安全补丁。保持 audit-level=low，不跳过测试，不修改调度、运行凭据、实时服务、来源、费用或发送状态。不重跑日报 AI；通过正常 cloudflare-unified.yml 发布现存产物即可同时恢复缺失页面。

上游修复依据：[Vitest 通告](https://github.com/advisories/GHSA-qxg6-89mg-rqv8)、[Vite 通告](https://github.com/advisories/GHSA-rq7h-c2jc-7f22)。

## 交付状态

- 代码：Vitest 4.1.12、Vite 8.3.5 已完成最小更新，相关传递依赖与完整性哈希同步更新。
- 验证：npm ci/audit 为 0 漏洞；类型、TypeScript、135 项 Worker 测试、Wrangler dry-run、117 项网页 Node 测试和治理检查通过；Python 回归进行中，远端 CI 待运行。
- PR 合并：待 CI。
- 部署：待合并后按现有授权执行统一工作流。
- 公网验收：待核对首页、21/22 日详情、中英 API、RSS 和 health 版本。

修复前 Source commit: 2f69a7a8e2dc01691e78660c9a364e2cacd625de。

修复前 Worker version: e1d9fc95-60a5-4793-8ac7-43f77c174e96；Artifact commit: 7bc2f6039bde075f5a4818fe2203ab4621814783。

Deployment: pending。Verification: 2026-10-22 12:20 上海，仅完成故障调查，不宣称恢复上线。

Rollback: 不自动回退或手写 gh-pages。如修复发布失败，保留现生产版本，先检查工作流日志；回退需运营者明确授权，旧依赖不能作为绕过安全检查的恢复方案。
