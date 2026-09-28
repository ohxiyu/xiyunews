# 周报推送

- Issue: [#146](https://github.com/ohxiyu/bmtnews-standalone/issues/146)
- Branch: `agent/weekly-push`
- Scope: 周报生成后的 Telegram/X 推送、推送收据、周报提示词覆盖面、周报 workflow 密钥。周报页面结构与评分校准不变。

## 变更

| 项 | 内容 |
| --- | --- |
| Telegram | 中文周报：`<b>本周回顾 · 起止</b>`、主线标题与摘要、前 4 条要点、「阅读完整周报」链接。复用日报的发送与错误脱敏（新增 `TelegramEditionPublisher.send_html`，日报发送改为调用它，行为不变） |
| X | 「本周回顾 · 起止｜主线」+ 摘要，不带链接，按加权字数截断到 `max_post_chars`；发送使用 `publish_post` 的结果分类 |
| 防重发 | 收据写入 `_data/weeks.json` 对应周的 `deliveries`（随站点发布、下次运行恢复）；重跑同一周跳过已推送渠道。X `unknown`/`failed` 记录后不再重发并告警；`not_sent`/`rate_limited` 不记收据，可重跑 |
| 提示词 | 周报定位改为 crypto and AI；本周有 AI 进展时至少 2 条 AI 条目，且前三条中至少 1 条 |
| Workflow | `weekly-review.yml` 注入 `TELEGRAM_*` 与 `X_*` 密钥 |

X 在周一会多一条（当天两条新闻 + 周报一条）。

## 验证

- `uv run pytest` 全部通过；新增 `tests/test_weekly_push.py`（文案只来自周报、转义与截断、重跑不重发、unknown 不重试、未创建可重试）。
- `uv run python scripts/check_governance.py` 通过。

## 尚未验证

- 下周一（2026-10-05）周报的真实推送与收据写入。
