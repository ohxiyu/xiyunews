# xiyu.news

中文加密与 AI 日报，由 [xiyu / @ohxiyu](https://x.com/ohxiyu) 维护。[阅读网站](https://xiyu.news/) · [往期](https://xiyu.news/history/)

每天以 **Asia/Shanghai 07:00** 为截止，覆盖此前 24 小时，**07:26** 启动出刊，目标约 07:30 发布。日报面向希望用一份内容了解重要进展的读者，保留必要背景与来源。

## 当前状态与重构目标

当前实现为单期中文日报首页、往期、日期页和关于页。后台每五分钟检查来源，只评分去重并写私有缓存，不更新首页、不扩写、不构建、不发送。入选内容在每日出刊时扩写。实际耗时受执行队列和供应商影响。生产模型为硅基流动 `deepseek-ai/DeepSeek-V3.2`，并发和候选上限保持原值；当前上限仍是14条、评分门槛7.0，待内容阶段调整。

发布链为 Daily Edition 保存出版快照 → 单一 Cloudflare 工作流重建并核对真实生产 → Telegram 校验精确生产凭证后单次发送。代码部署不构成新一期，不会重发历史。CSS与JS逐页预算20KB，无JS可完整阅读。

重构后的唯一对外产品为每天一期中文日报，目标 8–10 条、AI 最多 3 条。采集只写评分缓存，入选内容才扩写背景；网站、Telegram、X 引用同一期。用户已明确授权 X 跳过试运行；质量门和现有账号只读校验已完成，默认正式开关已开启，仍须当前新刊部署验证及合格文案才能发送。实际首次写入与首周结果待观察。余额检查已按用户要求取消，仅保留 token 费用台账。重构进度和验收门见[当前交接](project-docs/handoff.md)。

## 开发与运行

应用使用 Python 3.11+、uv 和固定依赖。站点发布经过 GitHub Actions 与统一 Cloudflare Worker；自托管执行器和持久缓存是实际运行链路的一部分。

```bash
uv sync --frozen --extra dev --extra trafilatura
cp data/config.github.json data/config.json
# 通过环境变量配置 SILICONFLOW_API_KEY，不提交密钥。
uv run bmtnews --mode fetch --hours 24
uv run bmtnews --mode publish --hours 24 --cutoff-hour 7
```

发布命令会生成出版内容；生产只走既有 Actions 流程，不从本地手写生成分支。

- [配置](project-docs/configuration.md) · [数据口径](project-docs/data-contract.md) · [界面规则](project-docs/ui-rules.md)
- [调度与恢复](project-docs/daily-dispatcher.md) · [X 分发](project-docs/x-distribution.md) · [执行器](project-docs/self-hosted-runner.md)
- 仓库协作从 [AGENTS.md](AGENTS.md) 和 [agent.md](agent.md) 开始。一个任务一个 PR，相关检查通过后合并，不再要求每 PR 编写五阶段证据或提交截图。
- `realtime/` 是独立 Telegram 实时应用，这次日报重构不修改它。

## 权利与来源

代码遵循 [MIT License](LICENSE)。第三方新闻和生成期刊不适用软件授权，见[内容与数据权利](CONTENT-LICENSE.md)及[第三方声明](THIRD_PARTY_NOTICES.md)。
