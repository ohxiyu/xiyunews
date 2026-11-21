# llms.txt 新闻站导航与可信度边界

Issue: https://github.com/ohxiyu/xiyunews/issues/224
Branch: agent/llms-discovery
PR: https://github.com/ohxiyu/xiyunews/pull/225
Baseline: f5499e869a3a910ecaae8d7cb6246c74796759ee

## 方案与授权

维护者要求给出合理方案并补齐 llms.txt，随后明确授权“检查通过后合并并发布”。现有正式文件已返回200，不是新建缺失文件。参考 [llms.txt 提案](https://llmstxt.org/) 的H1、摘要blockquote、正文说明与H2链接清单结构，保持小型静态索引、机器可读入口优先、次要链接放Optional，不生成整个历史的llms-full.txt。提案是导航约定，不保证各AI读取、SEO排名或训练许可。

只改llms.txt、对应developer文字、静态Content-Type声明、发布资产缺失检查与回归测试、交接证据。无需新服务、框架、依赖、AI、外部鉴权；不改公开UI、评分/去重、Worker业务/调度、密钥、数据及队列，不触发真实AI或渠道发送。

## 修改

- 最新日报/历史索引/事件/Quick Post四个公开JSON入口优先；仍列OpenAPI、Markdown概览与公共法律文件，所有完整链接为正式域HTTPS。
- 精确说明Asia/Shanghai、07:00窗口和07:26启动不是保证可见时间；latest可早于今日、generated_at不是新闻发生时间、采集并非实时。
- 类别配额是目标，不足不凑数；排名分数不是事实概率/交易建议，缺失不转0，来源聚合数不等于独立确认，AI扩写无独立生成后事实核验。
- Quick Post为人工批准、可能AI辅助、无重要性分数与自动翻译、整组连续/锚点语义和503错误；不把它混入日报配额。
- 日期先从现有索引取得，再跟随json URL；完整网页按既有日期路径查找，不编造索引不存在的zh/en字段。摘要JSON不冒充全文背景/参考资料。
- `/llms.txt`显式text/plain UTF-8；公开构建资产缺失此文件时报错，正常复制保留字节；无需更改请求处理器。

## 初始 PR 验证与交付状态（历史）

- git fetch origin / git merge origin/main：与f5499e86同步，Already up to date；uv sync --frozen --extra dev成功，锁文件无变化。
- 定向agent readiness/edge/private-public测试26 passed；完整uv run pytest为1050 passed /4 skipped /1条既有Google SDK弃用警告，19.23s。四项skip为基础环境未装可选multidict，与任务无关。
- 治理与git diff --check通过；格式/6KB上限、HTTPS公开目标、优先顺序、时效/证据/整组边界均离线测试。构建fixture验证缺失拒绝与原字节保留。
- 新文件5785 UTF-8字节；18条完整链接全部只读GET200，JSON/Markdown/XML/HTML/plain类型符合。正式文件本身仍为旧版，不能用链接200代替新文件上线；新版本与字节哈希待发布后验证。
- 发布前最新日报API完整字节SHA256为d5cd3df385773b104cdbcf3043f485b0103a6accdda472358d6133452a8a1353，发布后再比对；不因文档任务重跑新闻。

待记录：精确head CI、合并及生产新文件验收。测试不联网，使用现有schema/源码/临时构建fixture；公开URL另用只读GET验证。

开工生产：源码f5499e869a3a910ecaae8d7cb6246c74796759ee，产物6c53108e0af414c5fd6e08ab4c131fca78a0fe4d，Worker5961e838-9999-4736-a5d3-df39e1dc8a00，2026-10-07期14条，generated_at2026-10-06T23:30:18.069638Z。这是只读基线，不能当任务部署结果；正常采集可能自然更新产物。

代码完成；本地测试通过；精确head CI/PR合并/部署/生产验收待完成。部署走既有Deploy Docs→统一Worker，结果通过后续文档PR记录，不直接改main/gh-pages。回退需授权，在独立PR中回退本任务文件，再走同一路径，不清空缓存、历史或队列。

未验证/非目标：实际AI提供商采纳程度、搜索排名变化、CodeQL许可跳过、真实AI/发送/后台/手机功能。

## 2026-10-07：正式发布与验收

证据归档认领 [Issue226](https://github.com/ohxiyu/xiyunews/issues/226)，独立分支agent/llms-release，只改本记录与交接，文档合并不等于新Worker部署。

Source commit: 5367b824412681e41d327af7e2cc19fe145fd1a1
Worker version: 214e2228-7caf-4be4-884e-9087175d25ca
Deployment: [Deploy Docs37566027437](https://github.com/ohxiyu/xiyunews/actions/runs/37566027437) 成功，随后 [统一Worker37566072103](https://github.com/ohxiyu/xiyunews/actions/runs/37566072103) 自动发布成功（1m52s）；沿用现有项目/变量，不手动派发工作流。
Verification: 2026-10-07T03:20:04.490229Z（上海11:20:04），正式llms200/UTF-8与源码逐字节一致，18个完整链接全部200且结构/类型有效；日报API发布前后哈希一致，健康版本吻合。
Rollback: 必须另行授权，以独立PR回退本任务文件，再由原出版/统一Worker路径更新静态资源；此前源码f5499e869a3a910ecaae8d7cb6246c74796759ee、Worker5961e838-9999-4736-a5d3-df39e1dc8a00为开工实查基线。不手改状态分支或清空历史/队列。

### 精确 PR 与生产产物

- PR225精确head23b7c77017a93885747de5bcef6b6658d182312c的 [CI37565762161](https://github.com/ohxiyu/xiyunews/actions/runs/37565762161) 成功：test/governance/edge-build/realtime-paths，Pages自动预览成功；realtime未改路径跳过，CodeQL许可跳过不算通过。初始head运行按既有并发规则被后续head取代，不冒用旧检查。
- 同步最新main后2026-10-07T03:16:59Z按精确head条件合并PR225，源码5367b824。出版产物6a096b7261d5ca9b278b5a5a76493fdaf19fdf91；`/health`回读source/artifact/Worker ID与记录一致、status=ok，原07:00/07:26/四小时调度保持。
- 只经现有自动流程写gh-pages与部署；不运行日报/force_publish/editorial-rebuild/AI/渠道，不改密钥/费用/权限/Worker业务。正常服务自己的定时运行不由本次任务暂停或重放。

### 公开文件与端点

`https://xiyu.news/llms.txt`：200，`Content-Type: text/plain; charset=utf-8`，5785字节，无HTML壳或前置模板，SHA256为ca1bb2ff1c33f44c3237b13050acce56de84d245dc491f26221d94d6915f3ff4，与源码完全一致。全部18个链接再GET验证200：最新/历史/事件/Quick Post JSON、developer说明、OpenAPI JSON、中英Markdown、三类英文Atom、sitemap、about/contact/legal、三份法律plain文本。JSON成功解析、XML成功解析、Markdown以H1开头，其他类型正确；不请求任何写入接口。

developer新增时效/证据说明通过带校验query的原站GET确认。无query路径可能按原600秒缓存短暂展示旧说明；不为文字更新修改全站缓存策略。中英直接Markdown与首页Accept:text/markdown协商保持，响应Vary包含Accept。

最新日报2026-10-07、14条、generated_at2026-10-06T23:30:18.069638Z。完整API SHA256仍为d5cd3df385773b104cdbcf3043f485b0103a6accdda472358d6133452a8a1353，发布前后相同，新闻没有重写/重排/重新生成。

### 文档验证与当前状态

独立证据worktree基于最新已合并源码5367b824。frozen dev成功；pytest1050 passed/4 skipped/1既有弃用警告，20.37s；治理通过。文档最终head检查/合并状态看 [PR227](https://github.com/ohxiyu/xiyunews/pull/227)，不预先宣称通过。

应用PR225：代码完成、测试通过、已合并、已部署、限定范围生产验收完成。剩余未验证是第三方AI是否采纳/排名变化，及原有CodeQL许可跳过、真实AI/渠道/后台/实体设备边界；不将文件可访问等同AI实际采用。
