# 公开页面与分享图视觉统一

Issue: https://github.com/ohxiyu/xiyunews/issues/220
Branch: agent/beautiful-ui
PR: https://github.com/ohxiyu/xiyunews/pull/221
Implementation commit: 884ef081921e9739495f66cf1c032578df247c95
Baseline: 91c9c14b9cb5ca06735a5af2c21fa2a0d184e55b

## 范围与授权

维护者确认独立真实内容预览后，要求分享图与其他页面一并修改。初始阶段只交付 PR；后续“上线”授权与实际发布证据见本文末节。

公开首页、日报归档、追踪、事件与实体详情、周报和说明页共享浅灰/炭灰、白色/深灰轻面板与品牌蓝。保留实际导航、默认两期、证据、完整正文/分段、折叠、排行、阅读/PWA 和分享流程。分享 PNG 同步配色与面板、较小分析字号，从 CSS 令牌读取当前主题；不显示重复品牌、交互按钮、页面 URL。长来源换行，原有画布高度保护保留。

独立后台 /s、AI、评分、去重、分发、数据与生产 Worker 均不变。初始视觉提交未改依赖；维护者随后授权解除依赖告警，Python 与 Worker 开发工具链定向修复见下节。Worker 业务源码、工作流和运行配置不改。没有模型/套餐/鉴权变化。既有版本仍为 0.2.0。本次是共享视觉层变化，不复制第三方组件代码。

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

- uv sync --frozen --extra dev：成功；sharp 下限测试加入后默认 uv run pytest：1047 passed / 4 skipped / 1 条既有弃用警告。四个 skip 是基础环境未安装可选 multidict；版本下限检查仍执行。
- uv run --frozen --with multidict==6.9.1 pytest：完整 1051 passed / 1 条既有弃用警告，无 skip；安全模块单独 13 passed。
- Node 分享/PWA/站点 Worker 测试：40 passed；治理、diff 检查通过。资产/前端代码和指纹未再修改。
- 对全部 extras 导出的依赖执行与 CI 同版本/同参数 pip-audit 2.10.1 / PyPI 扫描：No known vulnerabilities found。没有忽略 CVE、关闭检查或批量升级其他包。不触发生产工作流。

### 同一检查暴露的 Worker 工具链告警

multidict 修复提交 835985ee94214631e3b961bd0b1a88ee3a710aee 的 [CI 37488488287](https://github.com/ohxiyu/xiyunews/actions/runs/37488488287) 中 Python 测试/审计与 edge-build 已通过，但 [npm check 日志](https://github.com/ohxiyu/xiyunews/actions/runs/37488488287/job/112354676278) 报告既有 sharp 0.35.4 / GHSA-wq5f-xc86-pv6w。在 [同一 Issue 追加文件范围](https://github.com/ohxiyu/xiyunews/issues/220#issuecomment-6019805066) 后继续处理，不忽略漏洞，也不执行 npm audit fix --force 所推荐的不兼容工具链降级。

[sharp 官方公告](https://github.com/lovell/sharp/security/advisories/GHSA-wq5f-xc86-pv6w) 指出 0.35.5 的预构建二进制修复了 librsvg 漏洞，携带 librsvg 2.63.2。提交 bfd644940a567566aaf3d872ca6ca224250f0565 将已有 sharp override 0.35.4→0.35.5，并重新生成仅涉及 sharp 与 @img/sharp-* 平台包的锁项（关联 libvips 1.3.3→1.3.4），Wrangler、Vitest、Miniflare 与其他依赖条目均不变。新增离线跨平台锁版本下限/对应关系检查，防止仅更新当前平台而遗漏 Linux 构建二进制。

npm ci / npm run check 本地通过：npm audit 0 vulnerabilities；配置类型与 TypeScript 校验通过；6 个文件 / 102 项 mock 测试通过；wrangler deploy --dry-run 只打包，没有上传部署。无需密钥或真实渠道/AI 调用。默认 pytest 1047 passed / 4 skipped；载入可选 multidict 后 1051 passed。

### 修复后远端证据

代码提交 bfd644940a567566aaf3d872ca6ca224250f0565 的 [CI37489270867](https://github.com/ohxiyu/xiyunews/actions/runs/37489270867) 全部适用检查成功：test（包含 1047 passed / 4 skipped、pip-audit PyPI 无已知漏洞、npm audit 零告警、Worker 102 项测试及所有 Node 检查）、governance、edge-build、realtime-paths。realtime 因未修改相关路径按既有规则跳过；[CodeQL analyze](https://github.com/ohxiyu/xiyunews/actions/runs/37489270820) 按既有私有许可条件跳过，不标为通过，也没有开启付费扫描。Cloudflare 既有 Git 集成的分支预览检查成功，但不是生产部署。证据文档后续提交仍需核对最新 head 检查，不能直接沿用代码提交的 checks；没有授权合并/上线。

## 初始 PR 交付时的五阶段（历史）

- 代码：完成。
- 测试：定向修复后本地测试、两套依赖审计通过；上述精确代码提交的适用 CI 检查通过，证据文档后的最新 head 另行核对。CodeQL 许可跳过保留为未验证事项。
- PR 合并：未执行。
- 部署：未执行。
- 生产验收：未执行。

## 初始发布与回退计划（历史）

经另行确认后沿用 PR → main → Deploy Docs / 统一 Worker 现有发布流程。CSS/JS 指纹同时更新根与 docs 配置，PWA 保留用户主动更新，不清空阅读记录或队列。
回退通过 revert 本 PR 并执行获授权的现有发布流程，不手改 gh-pages。此前生产 source 4e3862117671db962798fc305622a476f07e5ec7、Worker fb50c31c-7ca6-4339-b1f6-9929bd12ae74 的记录保持原样，实时迁移证据见 [既有记录](2026-10-05-realtime-api-domain.md)。

## 2026-10-06 / 07：获授权上线与生产验收

维护者最新要求“上线”，[Issue220 授权记录](https://github.com/ohxiyu/xiyunews/issues/220#issuecomment-6020019818) 明确本次合并及现有站点/统一 Worker 静态资源发布。上海10月6日23:52发布完成，验收跨午夜，以 UTC 记录版本时间。证据整理认领 [Issue222](https://github.com/ohxiyu/xiyunews/issues/222)，只改交接、发布记录与图片，不再次部署。

Source commit: 665a956235d73541e7289f242eec7913f13c3e6c
Worker version: e9285050-ac06-4dcc-97c9-1b8470c6d147
Deployment: [Deploy Docs37490743603](https://github.com/ohxiyu/xiyunews/actions/runs/37490743603) 与 [xiyunews Cloudflare37490823390](https://github.com/ohxiyu/xiyunews/actions/runs/37490823390) 自动执行成功；Worker 发布约2026-10-06T15:52:02Z，流程完成15:52:10Z。
Verification: 正式 https://xiyu.news/ 健康、资源字节、公开接口、响应式页面及实际分享 PNG 验收完成，最后只读核对2026-10-06T16:00:55Z。
Rollback: 需维护者授权，通过独立分支/PR 回退视觉改动并保留安全版本下限，再走现有自动发布；不手改产物/队列。如果 revert 整个 PR221，必须重新应用 multidict>=6.9.1 与 sharp0.35.5 的修复后再发布，不能重新引入漏洞。

### 精确合并与部署

- 账号 ohxiyu、仓库 ohxiyu/xiyunews、管理权限均已核验；不直接修改/提交/推送 main。
- PR221 精确 head12f95ba3f5b2271ca4b76659bb560b97f3514d1c 的 [CI37489761507 attempt2](https://github.com/ohxiyu/xiyunews/actions/runs/37489761507/attempts/2) 通过 test/governance/edge-build/realtime-paths 与分支预览。attempt1 npm audit 网络 ECONNRESET，仅重跑失败 CI 后通过，没有忽略扫描；CodeQL 私有许可跳过，不算通过。
- fetch/merge 最新 origin/main 后，上线前再次 frozen dev 安装成功；pytest1047 passed /4 skipped /1 条既有弃用警告，18.74s；治理通过。上文1051项可选环境与 Worker102项本地结果来自修复阶段，不冒充本次重跑。
- 2026-10-06T15:49:29Z 按精确 head 条件 squash 合并 PR221，源码为665a956。Deploy Docs 重建既有归档，不调用真实AI；下游现有 Cloudflare 流程自动部署同一 Worker，保留变量。
- 产物 f85da0836e4927104cd3119a30ebda2ecf916020；build2026-10-06T15:50:36+00:00；指纹sha256-94e4e835f53d。
- 发布前实查源码91c9c14b9cb5ca06735a5af2c21fa2a0d184e55b、产物9a08436cd964e8e5a2e61a8842b05b99dcd1d498、Worker392253d9-25a4-483d-930e-c3e9a130c50b。上文4e386/fb50是更早历史记录，不是本次最新基线。
- 未手动触发生产工作流、日报/强制重刊/编辑重建/渠道发送，未改密钥、DNS、套餐、调度或状态分支；产物仅由获授权的既有自动发布更新。

### 生产验收

`/health` 返回ok，repo/public_site_url/source/artifact/Worker version与上述版本一致。07:00截止、07:26首轮及后续调度配置保持不变。

正式资源200（归档沿用无扩展名跳转）：`/`、`/en/`、10月6日中英归档、10月5日中文归档、`/threads/`、`/events/evt_cc2ee6ed697c7f69/`、`/weekly/`、`/about/`、`/developers/`、`/feed-zh.xml`、`/manifest.webmanifest`、`/service-worker.js`、`/pwa-version.json`、`/api/latest.json`；JSON/XML/manifest/JS类型正确。匿名`/s/`返回302到opensat.cloudflareaccess.com登录入口，未进行真实后台登录/发布。

正式资源与源码665a956逐字节一致，SHA256：

- editorial-ui.css：4c302b8d46e825f8560f7e129ca0763dc8484e52c22b995cca6bb98d844a67de。
- story-card.js：28718b9096d6081ede4fb39e42c10b36ca2c9befc657f472343d07ea3ed4d286。
- pwa-reader.js：a16763a0cd3bde315bc5596518d713479ae720f7626d5dca7c449116fdaa9fbd。

日报`/api/latest.json`发布前后完整字节SHA256均为ac44a36a88ce4861cec58169d912b46f301c5d4a80731ee6583fc0808b068411；刊期2026-10-06，14条，generated_at2026-10-05T23:30:40.478217Z。默认仍为10月6日14条和10月5日9条两期，新闻没有改写/重排。午夜后“10月7日今日版准备中，07:26开始”是既有日期提示，不是本次发布造成延期。

生产浏览器核对首页/追踪/事件/实体列表与Anthropic详情/周报/关于/开发者/归档；桌面1280、手机390、英文320无整页横向溢出。正文桌面16px、最大740px（示例实测680.27px），手机15px、分析12.8px。首条完整3段正文、影响/背景、3个参考链接、6个标签及手机分享入口保留，浅深主题正常。

旧PWA缓存先展示“有新内容·点击更新”，点击后新指纹和样式生效，不强制打断阅读。实际生成、保存并查看浅深两张1320×4074 PNG，正文/来源/分析/参考/标签完整，无交互按钮、本地URL或重复品牌。分享面板“保存图片”“复制图片并打开X”存在且启用；只测试保存，未写剪贴板或打开X发帖。

### 正式站点图片证据

- [桌面首页](images/2026-10-06-beautiful-ui/production-home-desktop.jpg) / [桌面正文](images/2026-10-06-beautiful-ui/production-article-desktop.jpg) / [旧缓存更新入口](images/2026-10-06-beautiful-ui/production-before-opt-in.jpg)。
- [手机首页](images/2026-10-06-beautiful-ui/production-home-mobile.jpg) / [手机深色](images/2026-10-06-beautiful-ui/production-dark-mobile.jpg) / [分享面板](images/2026-10-06-beautiful-ui/production-share-mobile.jpg)。
- [实际浅色PNG](images/2026-10-06-beautiful-ui/production-share-light.png) / [实际深色PNG](images/2026-10-06-beautiful-ui/production-share-dark.png)。
- [追踪](images/2026-10-06-beautiful-ui/production-threads-mobile.jpg)、[事件](images/2026-10-06-beautiful-ui/production-event-mobile.jpg)、[实体列表](images/2026-10-06-beautiful-ui/production-entity-index-mobile.jpg)、[实体详情](images/2026-10-06-beautiful-ui/production-entity-detail-mobile.jpg)、[周报](images/2026-10-06-beautiful-ui/production-weekly-mobile.jpg)、[关于](images/2026-10-06-beautiful-ui/production-about-mobile.jpg)、[开发者](images/2026-10-06-beautiful-ui/production-developers-mobile.jpg)、[归档](images/2026-10-06-beautiful-ui/production-archive-mobile.jpg)、[英文320px](images/2026-10-06-beautiful-ui/production-en-mobile.jpg)。

### 当前五阶段与边界

应用PR221：代码完成、测试通过、PR已合并、部署成功、限定范围生产验收完成。Issue222证据另走文档PR，不把文档合并当成新的Worker发布。

文档证据分支从最新源码665a956独立建立；再次fetch/merge为Already up to date，uv sync --frozen --extra dev成功，uv run pytest为1047 passed /4 skipped /1条既有弃用警告（22.88s），治理及diff检查通过。证据PR为 [PR223](https://github.com/ohxiyu/xiyunews/pull/223)，其检查与合并状态以GitHub精确head记录为准，不据文档预先宣称通过。

未验证：CodeQL私有许可跳过；实体手机PWA安装/离线、剪贴板权限、X实际发帖、后台真实Access登录/发布、真实AI/渠道调用。本次不引入收费服务，不把浏览器模拟等同实体设备。
