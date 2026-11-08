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

Source commit: pending，基线7840448d145d5cb65fe88339c77f1aee8706c8af。

Worker version: not changed；上轮已核验9be81330-37a0-4ca6-892d-d08291c2eb1d，本次未部署。

Deployment: pending，正常合并后沿自动发布路径验收。

Verification: pending，不能把前次Qwen补刊成功当本次V3.2成功。

Rollback: 不自动回滚、改状态/队列/回执或重发渠道；需要时另由维护者授权确认目标。

code complete；tests/pr_merged/deployed/production_verified pending。
后续沿原07:00刊期验收当前日报中英背景和页面；重建时按原流程跳过已发送Telegram，
不放宽X时效。生成不是独立事实核验，不承诺未来外部服务永久稳定。
