# 2026-10-22 网站发布恢复

任务：[Issue293](https://github.com/ohxiyu/xiyunews/issues/293)。运营者要求修复网站仅更新到 20 日的问题；本会话唯一负责编辑、合并及正常生产发布。

## 根因与范围

10 月 21 日 Daily Edition [39515049970](https://github.com/ohxiyu/xiyunews/actions/runs/39515049970) 与 22 日 [39693448142](https://github.com/ohxiyu/xiyunews/actions/runs/39693448142) 均成功。调查时 gh-pages 为 14cee6f84b30567b95f6d07dee5d787320f8e79f，api/latest.json 为 2026-10-22、14 条；21、22 日中英文 Markdown 已存在，窗口正确。

生产网站 latest 仍是 2026-10-20、14 条。统一部署 [39711109423](https://github.com/ohxiyu/xiyunews/actions/runs/39711109423) 在 npm audit 失败：Vitest 4.1.11 的 @vitest/mocker 与 Vite 8.3.2 被新安全通告覆盖。审计阻止有问题的构建进入生产，并非采集或定时任务停用。东京磁盘可用 16 GB、无失败 systemd 单元。

最小更新 Vitest 至 4.1.12，并更新锁文件中的 Vite 安全补丁。保持 audit-level=low，不跳过测试，不修改调度、运行凭据、实时服务、来源、费用或发送状态。不重跑日报 AI；通过正常 cloudflare-unified.yml 发布现存产物即可同时恢复缺失页面。

上游修复依据：[Vitest 通告](https://github.com/advisories/GHSA-qxg6-89mg-rqv8)、[Vite 通告](https://github.com/advisories/GHSA-rq7h-c2jc-7f22)。

## 交付状态

- 代码：Vitest 4.1.12、Vite 8.3.5 已完成最小更新，相关传递依赖与完整性哈希同步更新。
- 验证：npm ci/audit 为 0 漏洞；类型、TypeScript、135 项 Worker 测试、Wrangler dry-run、118 项网页 Node 测试和治理检查通过；Python 完整回归 1118 passed / 4 个既有 skipped，缓存相关 86 passed；两次应用 PR 的适用远端 CI 全通过。
- PR 合并：PR294 与 PR296 的适用 CI 全通过后均已合并，精确版本见下。
- 部署：依赖恢复发布、缓存修复的 Deploy Docs 与统一发布均成功。
- 公网验收：2026-10-22 12:52 上海，14 个普通正式域地址全部通过，明细见最终证据。

修复前 Source commit: 2f69a7a8e2dc01691e78660c9a364e2cacd625de。

修复前 Worker version: e1d9fc95-60a5-4793-8ac7-43f77c174e96；Artifact commit: 7bc2f6039bde075f5a4818fe2203ab4621814783。

Deployment: PR294 合并为 d4d89453e4f7504397e46d5043ecd6b909af8d94；CI39722103810 的治理、web、edge-build 与外部 Pages 检查通过，其他正确按范围跳过。统一部署 [39722786056](https://github.com/ohxiyu/xiyunews/actions/runs/39722786056) 于 04:35:24Z 成功（4 分 34 秒）。

Verification: 2026-10-22 12:36 上海，中英文首页为 22/21 日各 14 条，canonical 正确。新 Worker ece1c144-636e-4910-bec9-c77b2f943b7c；Artifact 14cee6f84b30567b95f6d07dee5d787320f8e79f。普通 latest API 仍命中旧缓存，故尚不认定全链路验收完成。

## 生产验收发现的缓存一致性问题

[Issue295](https://github.com/ohxiyu/xiyunews/issues/295)：12:36 普通 /api/latest.json 返回 20 日，响应为 HIT / age 69 / CDN max-age=600；加全新查询参数立即为 22 日。/api/editions.json 与 22 日独立 edition.json 已为新内容。根因是 Cache API 键只包含固定 mutable-v2 命名空间，未绑定发布版本，缓存可以跨 Worker 更新保留。

将缓存 key 加入已有可信 SITE_BUILD_KEY（代码与出版产物的组合哈希），并覆盖调用方传入的同名内部查询参数，避免客户端选择旧命名空间。无该变量的独立托管保持既有兼容逻辑；统一生产工作流每次都设置该值。保留 TTL、Markdown/HTML 变体、鉴权/后台/PWA 元数据绕过与隐私策略，不进行账户级缓存清理或配置变更。

新增同一公开 URL 的发布前后缓存回归：旧版为 20 日，新版立即为 22 日，同版第二次请求命中，新版本客户端无法指定旧版缓存。覆盖 latest/index API、首页、RSS。135 项 Worker 测试、118 项网页 Node 测试、86 项相关 Python 回归、安全审计（0 漏洞）、类型、dry-run 与治理检查通过。

## 最终部署与公网证据

[Issue297](https://github.com/ohxiyu/xiyunews/issues/297) 仅归档最终证据。缓存修复 [PR296](https://github.com/ohxiyu/xiyunews/pull/296) 合并为 def7aeb2e2c07d2d26b489378b85197831b93e9d，CI [39723492938](https://github.com/ohxiyu/xiyunews/actions/runs/39723492938) 的治理、web、edge-build、路径检查与外部 Pages 全通过；无关 Python/realtime jobs 按路径正确跳过，相关 Python 已本地验证。

Source commit: def7aeb2e2c07d2d26b489378b85197831b93e9d。

Artifact commit: 3af570f64c203444be25611ae3f626204b3cda5b。

Worker version: efa60ee6-46bb-4fff-90cc-1a39d6c80ee3。

Deployment: [Deploy Docs39724132940](https://github.com/ohxiyu/xiyunews/actions/runs/39724132940) 成功（04:45:20–04:46:21Z）；后续自动[统一部署39724238673](https://github.com/ohxiyu/xiyunews/actions/runs/39724238673) 成功（04:46:27–04:51:01Z）。没有重复派发日报或人工写入状态分支。

Verification: 2026-10-22 12:52 上海，在不添加绕缓存查询参数的普通 URL 上核对内容，而非仅检查 HTTP 200。

| 正式域地址 | 观察结果 |
| --- | --- |
| /、/en/ | 均 200，首两天为 22 日 / 21 日，各 14 条，canonical 为 xiyu.news。 |
| /api/latest.json、/api/editions.json | 均 200，latest 为 22 日 14 条；索引前两期为 22/21 日。 |
| /editions/2026-10-21/edition.json、/editions/2026-10-22/edition.json | 均 200，日期与路径一致，各 14 条。 |
| /2026/10/21/summary-{zh,en}.html、/2026/10/22/summary-{zh,en}.html | 四个地址均跳转到对应干净 URL 并返回 200，各 14 条；canonical 为主域相应日期。 |
| /feed.xml、/sitemap.xml | 均 200，RSS 含 22 日内容；sitemap 含 22 日中英文 edition 页面及正确 lastmod。 |
| /health、/ready | 均 200，source/artifact/Worker 与上述一致，ready 为 ready。 |
| www.xiyu.news/ | 301 到 https://xiyu.news/。 |

边缘缓存响应仍为 browser max-age=0 / must-revalidate、latest CDN max-age=600；同版继续命中，但缓存键由 SITE_BUILD_KEY 隔离。正式域按新版本读取到 22 日，源码/产物标记可核对。

东京执行器与原实时服务均 active / NRestarts=0；执行器 MemoryPeak 747606016 字节，根盘仍可用约 15 GB。没有改密钥、DNS、费用、来源、提醒规则、部署主域或发送回执；构建不调用日报 AI，不发送测试消息或补发历史消息。

本次代码、测试、应用 PR 合并、生产部署与当前公网验收均完成。下一次 2026-10-23 07:26 自然出刊尚未发生，不提前触发或冒充验证。现有调度与预算保留；未来新的依赖漏洞仍须按同样的安全更新流程处理，不能保证永远不会出现上游故障。

Rollback: 不自动回退或手写 gh-pages。如修复发布失败，保留现生产版本，先检查工作流日志；回退需运营者明确授权，旧依赖不能作为绕过安全检查的恢复方案。
