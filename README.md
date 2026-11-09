# xiyu.news

中文加密与 AI 日报，由 [xiyu / @ohxiyu](https://x.com/ohxiyu) 维护。[阅读网站](https://xiyu.news/) · [往期](https://xiyu.news/history/)

每天以 **Asia/Shanghai 07:00** 为截止，覆盖此前 24 小时，**07:26** 启动出刊，目标约 07:30 发布。日报面向希望用一份内容了解重要进展的读者，保留必要背景与来源。

## 当前状态与重构目标

2026-11-09 正按日报版方案串行重构。当前生产仍有滚动精选和事件流，尚未在这一文档 PR 中关闭；日报与 Telegram 频道独立运行。生产模型为硅基流动 `deepseek-ai/DeepSeek-V3.2`，后台采集目标每五分钟检查，实际耗时受队列和供应商影响。当前上限仍是 14 条、评分门槛 7.0。

重构后的唯一对外产品为每天一期中文日报，目标 8–10 条、AI 最多 3 条。采集只写评分缓存，入选内容才扩写背景；网站、Telegram、X 引用同一期。X 先试运行三天，只向作者私人 Telegram 发预览，未经确认不在主号发布。重构进度和验收门见[当前交接](project-docs/handoff.md)。

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
