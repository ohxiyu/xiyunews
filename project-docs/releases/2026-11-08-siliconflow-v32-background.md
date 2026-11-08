# 2026-11-08 硅基流动DeepSeek V3.2与背景补全

[Issue338](https://github.com/ohxiyu/xiyunews/issues/338)，本聊天Codex唯一编辑与整合负责人。
分支agent/siliconflow-v32-background，独立快照work/siliconflow-v32-background/source，
基线main7840448d145d5cb65fe88339c77f1aee8706c8af。用户明确授权本次模型切换与背景改善，
沿既有正常合并、自动部署与发布路径；不修改独立realtime服务、密钥、权限或费用上限。

## 原因与实现

核对上轮成功日报14条生成字段与正式HTML，第一/第三条中英背景均为空，另12条有背景，
HTML与字段一致。公开摘要API不提供背景字段，不用API缺字段推断生成失败。
旧概念提取仅寻找不知名技术，明确跳过知名主体；写作又允许看似自明新闻直接不写背景。
提取为空、格式错误或失败时不搜索，可能遗漏可检索的上下文。这是可确认的策略问题，
不把全部缺失归因于模型能力，也不保证任何模型能为无证据新闻补背景。

生产配置与AIProvider.SILICONFLOW默认模型改为deepseek-ai/DeepSeek-V3.2，仍用
https://api.siliconflow.cn/v1与SILICONFLOW_API_KEY，不使用DeepSeek官方账户。
参见[硅基流动文本生成](https://docs.siliconflow.cn/docs/userguide/capabilities/text-generation)、
[思考参数文档](https://docs.siliconflow.cn/docs/userguide/capabilities/reasoning)。
经济模式JSON保持关闭额外思考，复杂最终输出8192、120秒请求/30分钟任务上限及并发不变。

背景检索优先主体身份、事件前因和必要机制，查询只用原文主体和术语，不因熟悉而跳过。
过滤非字符串、空白与重复查询，最多3条；无有效查询或提取失败时用标题构造1条定向查询，
复用既有搜索/缓存，不增加模型调用。写作优先1–3句有证据且不重复正文的双语背景；
来源/搜索均无可靠背景时两侧可空，不造占位、历史或链接。非文本或只写一种语言不能
冒充完整双语扩写，沿既有重试/翻译降级；引用仍限实际搜索URL。

背景缓存键纳入CONCEPT_EXTRACTION_USER，与已有模型、写作和概念system提示共同隔离。
旧Qwen结果不复用为V3.2，不手改缓存或历史归档。更新默认模型测试及配置文档，
同时改正该文档中PR334/336后已过时的思考策略描述。

## 验证与边界

新增回归：空/错误/异常提取仍搜索且不增加AI调用，最多3条且去重、URL约束，
双语字段不完整拒绝、无证据留空、模型和查询/写作提示变更使缓存失效。
既有分段和失败诊断测试注入空搜索，防止测试意外联网。
本机AST和JSON配置检查通过；完整适用CI、正常合并和真实调用待验收。

Source commit: 11a24fb22bdb9bd5a89b95bc386cbdd4ee48dc16。

Worker version: 9543b00f-b717-45e1-a24c-a333a5cb91fa，最终自动部署日志与正式health一致。

Deployment: [Cloudflare42465256718](https://github.com/ohxiyu/xiyunews/actions/runs/42465256718)，success；2026-11-08T09:06:24Z部署完成。

Verification: 2026-11-08T09:06:46.674234Z，普通正式域API/归档/中英HTML与浏览器核验，最终14条/13双语背景，详见末尾。

Rollback: 不自动回滚、改状态/队列/回执或重发渠道；需要时另由维护者授权确认目标。

以下为实施时的历史状态；最终五阶段见末尾。
后续沿原07:00刊期验收当前日报中英背景和页面；重建时按原流程跳过已发送Telegram，
不放宽X时效。生成不是独立事实核验，不承诺未来外部服务永久稳定。


## 第一轮真实V3.2验收与时间修正

[PR339](https://github.com/ohxiyu/xiyunews/pull/339)head2377e5dedb13edb66ee9a4559832b5c2575caf00，
[CI42461965112](https://github.com/ohxiyu/xiyunews/actions/runs/42461965112)1228 passed、4既有skipped，
48.60秒，审计无已知漏洞、治理及Pages预览通过；正常合并c0e938dd4c9878f8ddf64867e659429ca5e4ff1b，
确认祖先后删除已合并分支。

[Daily42462273927](https://github.com/ohxiyu/xiyunews/actions/runs/42462273927)source=c0e938d，
edition_date=2026-11-08、cutoff=7、force_publish=true（更新本期背景），diagnostic=false，
trigger=siliconflow-v32-background-update。08:18:02.922170Z至08:34:25.384728Z，982.463秒，
283候选、140分析、14展示，score_models为siliconflow:deepseek-ai/DeepSeek-V3.2共140。
所有实际AI调用均为同模型，14条全部新扩写，140.386秒、降级0。gh-pages中14条都有双语背景。
报告error=null，警告仅启动晚及部分来源失败；telegram_rebuild_skipped明确不重复Telegram。

字段齐全未通过事实抽查：MEXC背景把监管事件写2024-11-06，引用
[The Block](https://www.theblock.co/news/regulation/2026-11-06-treasury-cuts-off-mexc-global-over-alleged-16-billion-in-transactions-linked-to-iran-north-korea-and-russia-435957)
明确2026-11-06；Anthropic背景写2024年融资/申请，引用
[SmartAsset](https://smartasset.com/investing/anthropic-ipo-date-investor-timeline-valuation-and-expectations)
正文没有2024年，且不同融资/申请日期被拼接。不能宣称14条都有背景就是质量已通过。

[Issue340](https://github.com/ohxiyu/xiyunews/issues/340)同一负责人，
分支agent/background-date-grounding、独立快照work/background-date-grounding/source，
串行从c0e938d继续。背景查询与扩写传入published_at，仅作时间参照，不当事件时间证据；
提示要求保留每个事件的明确年份，不给裸月日猜年份，不混接融资/申请/上市的日期。
背景出现原文、原摘要、标题与搜索证据中没有的19xx/20xx年份，沿既有重试/翻译降级拒绝，
不静默纠正为当前年；有证据的真实历史年份继续允许。该窄检查不验证其他事实，也不证明
年份确实与对应事件绑定。ENRICHMENT_POLICY_VERSION升至news-editorial-v5-date-grounding，
原评分缓存可复用，旧背景自然失效，不手改缓存。

新增回归覆盖来源时间确实传入、无证据年份拒绝、证据内历史年份可用、
publication timestamp不可独自证明事件年份。Issue340 code complete，完整CI/合并/
更新后的生成与自动部署/内容验收pending。第一轮V3.2成功运行只证明可用性和字段生成。


## 最终交付与正式域验收

[PR341](https://github.com/ohxiyu/xiyunews/pull/341)最终head
96f3afe522355767cd94e0e8443d6d0ce2a512c9；
[CI42463832690](https://github.com/ohxiyu/xiyunews/actions/runs/42463832690)
1232 passed、4既有skipped，46.87秒；审计无已知漏洞、治理与Pages预览通过。
正常合并11a24fb22bdb9bd5a89b95bc386cbdd4ee48dc16，确认祖先后正常删除任务分支。
额外回归证明模型自己生成的搜索查询不是年份证据；年份集合只取源标题、源摘要、源正文
及实际搜索结果title/url/body，不取published_at或查询词，避免自证。该有限检查仍不证明
每个年份对应正确事件，不构成全面事实核验。

[最终Daily42464381027](https://github.com/ohxiyu/xiyunews/actions/runs/42464381027)，
source=11a24fb22bdb9bd5a89b95bc386cbdd4ee48dc16，
trigger=siliconflow-v32-background-dates，edition_date=2026-11-08、
cutoff=7、force_publish=true、diagnostic=false。
08:47:54.776517Z至08:58:21.051973Z，626.275秒；
283候选、140分析、14展示（Crypto9/AI3/政策2）、2条高优先级。
评分缓存140，新分析35；score_models175含缓存，全部为siliconflow:deepseek-ai/DeepSeek-V3.2；
报告实际AI调用也只有该模型。14条新扩写、0扩写缓存、249.176秒。

13条背景中英完整，Loopscale条目最终ValueError后按既有路径翻译降级，未保留背景。
报告enrichment_degraded=1，不能将其说成14条完整扩写。日志只记录安全异常类型，
无法仅凭ValueError确定最后一次具体失败分支，不把它断言成某个校验错误。
报告error=null，status=warning：启动晚、部分来源失败（顶层0/5完全失败）、
1条扩写降级；telegram_rebuild_skipped明确本期重建不重复Telegram。
报告event_classifier_errors=2、event_evidence_deferred=10、历史event_texts_untranslated=6，
不把本次日报成功当历史事件全部修复。原始报告与日志仅本地保存，不提交密钥、临时URL或原始生产状态。

自动[Cloudflare42465256718](https://github.com/ohxiyu/xiyunews/actions/runs/42465256718)
job128683185436 success，09:06:24Z部署触发器完成。
最终产物gh-pages10738b70effd0aca8aea4d5e815e259c6528e5ed。
2026-11-08T09:06:46.674234Z普通正式URL（无cache-bust，跟随正常规范化重定向）验收：

- [latest](https://xiyu.news/api/latest.json)与[当期JSON](https://xiyu.news/editions/2026-11-08/edition.json)完全相等，date=2026-11-08、items=14、generated_at=2026-11-08T08:58:08.694761Z。
- [归档索引](https://xiyu.news/api/editions.json)首项11月8日14条。窗口2026-11-06T23:00:00Z至2026-11-07T23:00:00Z，即上海11月7日07:00至11月8日07:00。
- [中文首页](https://xiyu.news/)与[英文首页](https://xiyu.news/en/)首期均为11月8日。
- [中文详情](https://xiyu.news/2026/11/08/summary-zh.html)、[英文详情](https://xiyu.news/2026/11/08/summary-en.html)、[中文fragment](https://xiyu.news/editions/2026-11-08/zh.html)及[英文fragment](https://xiyu.news/editions/2026-11-08/en.html)均14条、13个background区块。
- 浏览器可见头条背景与完整正文，英文详情实际DOM14条/13背景。本地截图outputs/edition-20261108-v32-background-published.png。
- [health](https://xiyu.news/health)：source11a24fb22bdb9bd5a89b95bc386cbdd4ee48dc16、artifact10738b70effd0aca8aea4d5e815e259c6528e5ed、Worker9543b00f-b717-45e1-a24c-a333a5cb91fa，与部署日志一致。

抽查新Anthropic背景已不含前次错误2024年；新MEXC入选条目也没有该误写。
本期重建重新评分/选稿，不能声称只给旧14条加背景或原榜单完全不变。
年份检查允许证据中的历史年，不宣称所有19xx/20xx文字均为已核实事实。

只读核对X当前期skipped_late、jobs=[]，不放宽时效。
[Square42465256744](https://github.com/ohxiyu/xiyunews/actions/runs/42465256744)
结果attempted=0、sent=1（累计既有回执）、due=false、remaining=14、attention=0、
unscheduled=0，不把累计sent当本次新发送，也不手改队列或回执。

应用code/tests/pr_merged/deployed/production_verified五阶段均complete，限制如上。
部署后证据由同一负责人在agent/v32-background-production-evidence、
独立快照work/v32-background-production-evidence维护，仅交接及本发布记录。
未来定时刊期未发生；1条翻译降级留待独立编辑复核，不为版面补造背景或重复发送历史日报。
