# Quick Post 整组预览与插入

Issue: https://github.com/ohxiyu/xiyunews/issues/212

PR: https://github.com/ohxiyu/xiyunews/pull/213
Local validation source: 6398ceef4ec808ed6be7ec61edae58e4b4da6c0e

Deployment evidence PR: https://github.com/ohxiyu/xiyunews/pull/215

目标：仅处理新输入，人工核对AI预览后整组发布，共享刊期与稳定新闻ID锚点，保留组内输入顺序。不修改日报、评分、配额、翻译或渠道分发。旧单条、编辑、广告和屏蔽记录保留。无新收费服务、数据库或登录方式；模型调用仍消耗既有DeepSeek额度。

用户已授权部署统一Worker；QUICK_POST_AI_API_KEY由用户设置后通知，不能从Actions复制密钥。QUICK_POST_AI_ENABLED=true且密钥存在才调用模型。未配置或失败不保存、不发布、不自动重试。已有STATE KV仅用于24小时精确输入缓存。

代码完成；本地uv frozen dev、pytest1043项、治理、Node88项（后新增并发/超时后89项）、Worker102项及npm audit/typecheck/构建通过。统一Worker仅空资产目录dry-run通过，完整产物由CI构建验证。旧单条浏览器、整组后台和公开流在390×844 / 1280×900、浅色/深色模拟通过。mock涵盖AI失败/截断/遗漏/重排/限流/缓存/重复请求、SHA冲突、整组原子写入、锚点缺失/同日重排、无评分及公开白名单，不进行真实模型调用。

PR、合并、部署、线上验收pending。真实AI、Access登录和真实内容发布尚未验证；等待用户确认Secret及准备真实输入，不用假新闻进行生产验收。模型整理不具备独立来源核验，生成内容仍须人工核对。

以上为合并前快照。业务PR213已于2026-10-04T05:37:43Z合并；代码/测试/合并/部署完成，公共只读验收通过，真实AI和用户Access操作仍未验收。验收文档Issue214，独立文档分支，不再触发生产部署。

Source commit: 53af4f4f04926d210a0679515ab7800fe8bb27f1

Worker version: 9407da2b-307e-47e1-b600-003457c0a24f

Deployment: [Deploy Docs37180445715](https://github.com/ohxiyu/xiyunews/actions/runs/37180445715)成功生成产物3b1aa2a5af7f1388d9f2d0ee4816a126698462e5；
[Cloudflare37180465863](https://github.com/ohxiyu/xiyunews/actions/runs/37180465863)成功，05:39:39Z部署同名统一Worker，版本ID与health一致。既有变量由keep-vars保留，未修改Secret或启用开关。

Verification: 2026-10-04T05:41:12Z，https://xiyu.news/health健康、源码/产物/Worker版本均匹配；
/api/latest.json日期2026-10-04、generated_at03:43:17.666677Z、12条保持不变。
/assets/js/quick-posts.js的SHA256为43e55615260b215010497ef61574b7998a9a9248fa47390f25e9ce327c668bf9，与合并源码字节一致。
/openapi.json为3.1.1并含batch_id/anchor_id/title/tags/sources；/api/quick-posts.json返回version1、当日日期、Git revision912af7a8275608917f807725b69e4b62ed56e65b、0条（没有新增测试内容）。
非法日期返回结构化invalid_date错误；/s/和/api/admin/generate匿名均302转邮箱验证，生成接口并未对外开放。没有真实AI或渠道调用。

Remaining acceptance: 等待用户确认在Cloudflare统一Worker xiyunews设置QUICK_POST_AI_API_KEY Secret和QUICK_POST_AI_ENABLED=true变量，随后使用用户真实材料生成预览。未登录Access操作、不验证/发布假新闻；不把公开验收当成AI质量证明。

CI: [37180286568](https://github.com/ohxiyu/xiyunews/actions/runs/37180286568)最终head115fe216成功，test/edge-build/governance及Cloudflare Pages预览通过；CodeQL因现有私有套餐跳过，realtime路径未修改跳过，不宣称完整安全分析已执行。

额外runtime模拟：现有认证测试通过workerd（有效JWT接受、重定向JWKS拒绝），测试脚本使用已安装Miniflare的V4选项转换器兼容新版本，不新增依赖。统一Worker的完整静态资产构建仍由远端edge-build确认。

## 视觉证据（模拟内容，无生产写入）

390×844变更前：[旧后台](assets/quick-batches/before-quick-post-390.png)；
变更后：[新后台](assets/quick-batches/batch-admin-390-light.png)、[公开流](assets/quick-batches/batch-stream-390-light.png)、[深色后台](assets/quick-batches/batch-admin-390-dark.png)。
1280×900变更前：[旧后台](assets/quick-batches/before-quick-post-1280.png)；
变更后：[新后台](assets/quick-batches/batch-admin-1280-light.png)、[公开流](assets/quick-batches/batch-stream-1280-light.png)、[深色后台](assets/quick-batches/batch-admin-1280-dark.png)。

Rollback: 上一健康Worker 1b668bd4-ebfd-4bdb-b944-03a408a6a905；经单独授权后revert本PR并走现有部署流程，保留Git中的旧记录与整组原始输入，不手改状态分支或队列。
