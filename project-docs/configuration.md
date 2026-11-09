# 日报配置

生产参数以 `data/config.github.json` 为准，Pydantic 字段与约束见 `src/models.py`。本地复制为忽略追踪的 `data/config.json`；凭证只通过环境变量注入，不写入 JSON。

## AI

- 供应商：`siliconflow`；模型：`deepseek-ai/DeepSeek-V3.2`；兼容地址：`https://api.siliconflow.cn/v1`。
- 密钥变量：`SILICONFLOW_API_KEY`。旧 DeepSeek 账户不再是默认供应商。
- 输出为中文，`ai.languages: ["zh"]`。模型只能做评分去重、背景扩写、X 文案。
- 当前 `analysis_concurrency` 与 `enrichment_concurrency` 均为 5；预筛候选上限 140；保持既有输出预算与缓存。未经用户授权不调整模型、并发、候选上限、付费套餐。
- 标题或摘要不含中文时只修复一次，仍不合格则排除。HTTP 401/402/403 立即停止该客户端的新调用，不以翻译重试绕过账户错误。
- 评分缓存按输入、模型和评分提示生成键；扩写缓存额外包含输入分数/标签及背景提示。扩写输出标签不替代输入缓存身份。

## 来源与选稿

仅保留 GitHub、Hacker News、RSS、Telegram、Google News 五类采集器。`sources` 下的列表/开关控制实际启用情况；未启用的 Reddit、Twitter、OpenBB、OSSInsight、GDELT 实现和依赖已删除。

RSS 可使用同域 Google News 回退，必须保留原始抓取失败和回退身份，不能宣称已读到一手正文。`extractors` 仍支持可选 trafilatura，默认安装不包含它。

`filtering` 控制业务时区、24小时窗口、评分门槛、类别配额、来源层级和来源上限。当前仍为门槛 7.0、最多 14 条，数值调整留到内容阶段；不会因本次拆分更改模型分数或选稿顺序。

- `source_tiers`：一手、原创媒体名单；未匹配默认其他来源。
- `category_groups`、`primary_groups`、`max_items_per_source`：保留原有配额和来源分散约束。
- `minimum_display_items`、`fallback_window_hours`：只允许未发布且通过既有检查的补充项。
- `low_signal_minimum_items`：低信号短刊单独标记，与故障简版不同，不用未打分内容补足。

## 刊期与持久状态

Asia/Shanghai 前日 07:00 至当日 07:00，右端不包含；07:26 启动，目标约07:30发布。来源时间不能用抓取或运行时间代替。

```
uv sync --frozen --extra dev
cp data/config.github.json data/config.json
uv run bmtnews --mode fetch --hours 24
uv run bmtnews --mode publish --cutoff-hour 7
```

采集、评分去重、扩写、出版分别由 `collection.py`、`selection.py`、`enrichment.py`、`publication.py` 负责，`orchestrator.py` 只协调每日刊期。X 队列在 `x_distribution.py` 中独立执行。

- 原始暂存：`data/staging-items.json`。
- AI缓存：`data/analysis-cache.json`。
- 经过评分、语义去重的简版候选：`data/qualified-cache.json`；必须与刊期、阈值和模型契约一致。
- 生产 SQLite：由 `XIYUNEWS_STATE_DIR` 指定的受信任持久目录；与独立 realtime 数据库隔离。
- 既有刊期和投递回执不重写、不重发。静态修复只恢复缺失入口，不调用来源、模型或发送器；补旧刊不倒退 latest。

## 分发与告警

Telegram 日报须通过同一期真实生产验证凭证，使用 `TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHANNEL_ID`；发布后任务先落盘一次性回执，再发送。未知结果不能自动重试。

运维告警使用同一日报 bot，目的地由 `TELEGRAM_ALERT_CHAT_ID`、`TELEGRAM_ALERT_THREAD_ID` 指定（Actions Secret 或仓库变量）。当前目的地为用户指定群的“日报运维”话题，不能回退到通用群、读者频道或独立 realtime 目的地。统一 Worker 中日报 bot 使用独立的 `DAILY_TELEGRAM_BOT_TOKEN` 绑定，避免与 realtime watchdog 混用。

用户已取消余额检查和余额预警。费用台账只将真实 token 用量换算为估计金额，未知模型标记未计价，不伪造账户余额或可用天数。

X 沿用 OAuth 1.0a 四项 Actions 凭证。用户已授权跳过三天试运行；质量门和现有账号只读验证通过后，默认开关已开启。只有当前新刊部署证明及合格文案才能发送，账号读取不等于写权限。不开通或升级套餐。Premium 未确认时按280加权字符限制，详见 [X 分发](x-distribution.md)。

## 部署边界

只通过 Actions 发布生成分支，正常 PR 走既有自动部署。CI 与生产共用 `scripts/overlay_core_site.py`；缺失必要文件必须失败，可选 `_sass` 不影响构建。

`realtime/` 的采集、配置、依赖、数据库与目的地独立，本次不修改。其他运维参数见 [调度](daily-dispatcher.md) 与 [执行器](self-hosted-runner.md)。
