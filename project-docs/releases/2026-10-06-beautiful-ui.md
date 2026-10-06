# 公开页面与分享图视觉统一

Issue: https://github.com/ohxiyu/xiyunews/issues/220
Branch: agent/beautiful-ui
PR: https://github.com/ohxiyu/xiyunews/pull/221
Implementation commit: 884ef081921e9739495f66cf1c032578df247c95
Baseline: 91c9c14b9cb5ca06735a5af2c21fa2a0d184e55b

## 范围与授权

维护者确认独立真实内容预览后，要求分享图与其他页面一并修改。本次只交付 PR，不合并、部署或触发生产工作流。

公开首页、日报归档、追踪、事件与实体详情、周报和说明页共享浅灰/炭灰、白色/深灰轻面板与品牌蓝。保留实际导航、默认两期、证据、完整正文/分段、折叠、排行、阅读/PWA 和分享流程。分享 PNG 同步配色与面板、较小分析字号，从 CSS 令牌读取当前主题；不显示重复品牌、交互按钮、页面 URL。长来源换行，原有画布高度保护保留。

独立后台 /s、AI、评分、去重、分发、数据与生产 Worker 均不变。初始视觉提交未改依赖；维护者随后授权解除依赖告警，定向修复见下节。没有模型/套餐/鉴权变化。既有版本仍为 0.2.0。本次是共享视觉层变化，不复制第三方组件代码。

## 验证

- git fetch origin / git merge origin/main：与 91c9c14b9cb5ca06735a5af2c21fa2a0d184e55b 同步，Already up to date。
- 初始视觉提交 uv sync --frozen --extra dev：成功，72 个包；当时依赖和锁文件没有改动。
- uv run pytest：1045 passed，1 条既有 google/genai 弃用警告。
- node --test tests/test_pwa_*.mjs tests/test_agent_worker.mjs tests/test_story_card.mjs：40 passed。新增共享主题/完整绘制/长来源边界、响应式默认字号与明确字号覆盖测试，均使用 mock，无真实 AI 或渠道调用。
- uv run python scripts/check_governance.py：通过；git diff --check：通过。
- 根与 docs 配置资产指纹一致：sha256-94e4e835f53d。

本地浏览器验收采用当日已公开 HTML + 当前任务真实 CSS/JS，不是假新闻示意图，也不改动生产内容。1280×720：中文首页、追踪、周报、实体详情、开发者说明；390×844：中英首页、日报归档、追踪、事件详情、实体列表/详情、周报、关于、开发者说明；英文首页另查 320×844。上述页面 document scrollWidth 均等于视口宽度，无整页横向溢出。中文首页浅/深色均检查；正文实际桌面 16px / 手机 15px，手机分析 12.8px。Crypto 筛选保留 9 条且默认仍为两期；背景折叠可展开，键盘焦点有 2px 可见轮廓。手机仍有分享入口。

真实分享渲染器完成浅/深色两张 1320×4074 PNG 的生成、保存及图片检查，包含所有段落、来源、影响、背景、参考及标签；品牌一次，没有按钮或本地页面链接。颜色随当前页面主题变化。既有的高度上限、惰性加载、复制图片后打开 X 的流程保持不变；未尝试真实剪贴板写入或 X 发帖。

### 图片证据

- 首页 1280×720：[改前](images/2026-10-06-beautiful-ui/before-home-desktop.jpg) / [改后](images/2026-10-06-beautiful-ui/home-desktop.jpg) / [深色](images/2026-10-06-beautiful-ui/home-dark-desktop.jpg)。
- 首页 390×844：[改前](images/2026-10-06-beautiful-ui/before-home-mobile.jpg) / [改后](images/2026-10-06-beautiful-ui/home-mobile.jpg) / [正文](images/2026-10-06-beautiful-ui/story-mobile.jpg)。
- 其他页面 390×844：[追踪](images/2026-10-06-beautiful-ui/threads-mobile.jpg)、[周报](images/2026-10-06-beautiful-ui/weekly-mobile.jpg)、[事件](images/2026-10-06-beautiful-ui/event-mobile.jpg)、[实体](images/2026-10-06-beautiful-ui/entity-mobile.jpg)、[实体详情](images/2026-10-06-beautiful-ui/entity-detail-mobile.jpg)、[关于](images/2026-10-06-beautiful-ui/about-mobile.jpg)、[开发者](images/2026-10-06-beautiful-ui/developers-mobile.jpg)、[归档](images/2026-10-06-beautiful-ui/archive-mobile.jpg)、[英文](images/2026-10-06-beautiful-ui/home-en-mobile.jpg)。
- 实际导出：[浅色 PNG](images/2026-10-06-beautiful-ui/share-light.png) / [深色 PNG](images/2026-10-06-beautiful-ui/share-dark.png)。

未验证：本机无可用 Jekyll 环境，未声称本地完整站点构建成功；浏览器检查复用已公开 HTML，模板未改动。CI edge-build 现有流程构建 gh-pages，不能当成本任务新样式上线证据。真实手机 PWA 安装/离线、剪贴板权限、X 发帖和生产效果需合并部署后按原流程另验。

### 修复前 GitHub 检查与自动预览

PR head b66b053329170ca6e2f4ebdcc2f46df4fb3e8c80 的 [CI 37481253270](https://github.com/ohxiyu/xiyunews/actions/runs/37481253270)：governance 成功，pytest 成功，但 test job 在既有依赖扫描被拦截。前一个同 head 的 [扫描日志](https://github.com/ohxiyu/xiyunews/actions/runs/37481214065/job/112329503389) 明确报告 multidict 6.7.1 / CVE-2026-104874，建议修复版本 6.9.1。当时尚未授权更改依赖，故留下阻塞。CodeQL analyze 按仓库既有私有扫描许可条件跳过，不称其通过。

既有 Cloudflare Git 集成自动构建出 implementation commit 884ef081 的 [分支预览](https://3dc2df38.bmtnews.pages.dev/about/)，不是生产发布。已在浏览器核对新 asset_version sha256-94e4e835f53d、关于页样式与 1280×720 [截图](images/2026-10-06-beautiful-ui/pages-preview-about.jpg)。预览没有 gh-pages 日报归档，因此首页是诚实空态，不能用它冒充真实日报/分享图片验收；有内容的浏览器/PNG 检查仍以上述本地真实公开 HTML 方法为准。没有手动部署 Worker 或触发生产流程。

## 后续授权：修复依赖扫描阻塞

维护者随后要求“改”，按前文告警上下文解释为授权修复依赖，不是授权合并部署。在 [Issue220 追加认领说明](https://github.com/ohxiyu/xiyunews/issues/220#issuecomment-6019605384)，继续单一负责人、当前分支/worktree/PR，不覆盖其他 Codex 或 Dependabot 分支。

[上游安全公告](https://github.com/aio-libs/multidict/security/advisories/GHSA-54p9-h82j-f925) 确认 6.7.0–6.9.0 的 C 扩展 items-view 反向并集/减集引用泄漏，修复版本 6.9.1。沿用既有 tool.uv.constraint-dependencies 机制新增 multidict>=6.9.1,<7，不覆盖父依赖约束、不把可选包强制加入基础运行依赖。uv lock 定向更新 6.7.1→6.9.1；结构化对比确认其余 162 个 package 元数据未改变，根 manifest 只增加该安全下限。

新增安全版本下限/manifest 回归及 MultiDict/CIMultiDict 两种操作释放引用的离线检查。小规模隔离验证旧 6.7.1 四个路径各残留 32 个 value 引用，新 6.9.1 四个路径测试均通过；测试不调用业务外部服务，不进行高内存负载。

- uv sync --frozen --extra dev：成功；默认 uv run pytest：1046 passed / 4 skipped / 1 条既有弃用警告。四个 skip 是基础环境未安装可选 multidict；版本下限检查仍执行。
- uv run --frozen --with multidict==6.9.1 pytest：完整 1050 passed / 1 条既有弃用警告，无 skip；安全模块单独 13 passed。
- Node 分享/PWA/站点 Worker 测试：40 passed；治理、diff 检查通过。资产/前端代码和指纹未再修改。
- 对全部 extras 导出的依赖执行与 CI 同版本/同参数 pip-audit 2.10.1 / PyPI 扫描：No known vulnerabilities found。没有忽略 CVE、关闭检查或批量升级其他包。推送后最新 head CI 待核对，不触发生产工作流。

## 五阶段

- 代码：完成。
- 测试：定向修复后本地测试与完整依赖审计通过；最新修复 head 的 CI 尚待核对，不能沿用旧 head 结果或宣称全部 required checks 已通过。
- PR 合并：未执行。
- 部署：未执行。
- 生产验收：未执行。

## 发布与回退

经另行确认后沿用 PR → main → Deploy Docs / 统一 Worker 现有发布流程。CSS/JS 指纹同时更新根与 docs 配置，PWA 保留用户主动更新，不清空阅读记录或队列。
回退通过 revert 本 PR 并执行获授权的现有发布流程，不手改 gh-pages。此前生产 source 4e3862117671db962798fc305622a476f07e5ec7、Worker fb50c31c-7ca6-4339-b1f6-9929bd12ae74 的记录保持原样，实时迁移证据见 [既有记录](2026-10-05-realtime-api-domain.md)。
