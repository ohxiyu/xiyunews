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

## 验证与交付状态

- git fetch origin / git merge origin/main：与f5499e86同步，Already up to date；uv sync --frozen --extra dev成功，锁文件无变化。
- 定向agent readiness/edge/private-public测试26 passed；完整uv run pytest为1050 passed /4 skipped /1条既有Google SDK弃用警告，19.23s。四项skip为基础环境未装可选multidict，与任务无关。
- 治理与git diff --check通过；格式/6KB上限、HTTPS公开目标、优先顺序、时效/证据/整组边界均离线测试。构建fixture验证缺失拒绝与原字节保留。
- 新文件5785 UTF-8字节；18条完整链接全部只读GET200，JSON/Markdown/XML/HTML/plain类型符合。正式文件本身仍为旧版，不能用链接200代替新文件上线；新版本与字节哈希待发布后验证。
- 发布前最新日报API完整字节SHA256为d5cd3df385773b104cdbcf3043f485b0103a6accdda472358d6133452a8a1353，发布后再比对；不因文档任务重跑新闻。

待记录：精确head CI、合并及生产新文件验收。测试不联网，使用现有schema/源码/临时构建fixture；公开URL另用只读GET验证。

开工生产：源码f5499e869a3a910ecaae8d7cb6246c74796759ee，产物6c53108e0af414c5fd6e08ab4c131fca78a0fe4d，Worker5961e838-9999-4736-a5d3-df39e1dc8a00，2026-10-07期14条，generated_at2026-10-06T23:30:18.069638Z。这是只读基线，不能当任务部署结果；正常采集可能自然更新产物。

代码完成；本地测试通过；精确head CI/PR合并/部署/生产验收待完成。部署走既有Deploy Docs→统一Worker，结果通过后续文档PR记录，不直接改main/gh-pages。回退需授权，在独立PR中回退本任务文件，再走同一路径，不清空缓存、历史或队列。

未验证/非目标：实际AI提供商采纳程度、搜索排名变化、CodeQL许可跳过、真实AI/发送/后台/手机功能。
