# 2026-11-08 日报迁移硅基流动

[Issue329](https://github.com/ohxiyu/xiyunews/issues/329)，分支 agent/siliconflow-qwen27b，
本聊天 Codex 唯一编辑与整合负责人。GitHub connector 固定 main
9fdcd9fe58e32dca65c57dd9d0e1441814431b6e 读取隔离源码快照；不用旧失效
worktree，不修改 main 或状态分支。应用依赖未变，不更新版本或锁文件。

## 行为

日报配置从 DeepSeek 官方 API 切到硅基流动 `https://api.siliconflow.cn/v1`，
模型精确为 `Qwen/Qwen3.5-27B`，Secret 为 `SILICONFLOW_API_KEY`。
显式新增 provider，用现有 OpenAI SDK；设置向导自动提供新选项与默认值。
日报（含诊断）、采集和 X 分发四个 AI 步骤均映射新 Secret；其他服务不变。

选择侧重中文新闻分析、指令遵循和长文理解，依据
[27B官方模型卡](https://huggingface.co/Qwen/Qwen3.5-27B)及
[35B-A3B官方模型卡](https://huggingface.co/Qwen/Qwen3.5-35B-A3B)，
不是跨所有模型所有任务的统一排名，也未进行生产A/B。

遵循[硅基流动推理参数](https://docs.siliconflow.cn/docs/userguide/capabilities/reasoning)，
简单任务在经济模式关闭思考，其他任务启用并限制 thinking_budget=4096；
最终输出 max_tokens 仍为原值，保留现有精确提示词预算策略。
不发送 DeepSeek 官方 thinking 对象或 reasoning_effort。
JSON与文本请求按原调用方选择，拒绝空/截断输出，不返回 reasoning_content。
计量、评分来源与缓存使用新 provider/model，历史评分不重算，旧缓存不清空。
401/402/403 的运行内熔断、取消并等待并发和脱敏动作提示继续生效。

没有新增自动fallback、放宽7分门槛、调整刊期/并发/调度/重试次数或调用
独立 realtime 服务。不能保证外部余额、权限或供应商稳定性。

## 验证与交付

新增测试覆盖工厂/默认URL和密钥、旧密钥不被误用、思考协议和限额、JSON/正文
差异、动态评分计量来源、推理内容不泄露、空/截断拒绝、三个工作流Secret
映射、向导默认值、新旧缓存隔离；现有账户熔断回归增加siliconflow参数。
本机AST语法检查通过；完整功能回归与治理待远端CI。

用户明确“先完成代码，稍后配置密钥”。本次不改Secrets，不调用真实AI，
不重跑生产或发送测试消息。Draft PR保持待密钥，不合并激活缺密钥配置。
配置后先验证精确模型权限、真实JSON/正文和当期出刊，再观察评分分布与去重。

Source commit: 基线9fdcd9fe58e32dca65c57dd9d0e1441814431b6e；应用提交0cb6c8b731a5a580e6a110a000e95da95c4823ce；[PR330](https://github.com/ohxiyu/xiyunews/pull/330)。

Worker version: unchanged，未修改或手工部署Worker。

Deployment: pending，Draft PR待密钥配置后正常合并。

Verification: pending，未验证真实API、当期刊期或网站恢复。

Rollback: 不自动回退到余额不足的旧账户；不手工改状态分支或消息回执，回退另按授权处理。
