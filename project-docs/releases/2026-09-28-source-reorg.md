# 信息源重组（第一步）

- Issue: [#140](https://github.com/ohxiyu/bmtnews-standalone/issues/140)
- Branch: `agent/source-reorg`
- Scope: Telegram 抓取诊断与试运行模式、`data/config.github.json` 的 Telegram 与 RSS 信源、运行摘要。评分、分组、Google News/GDELT 不变。

## 背景

暂存区 568 条候选中 Telegram 只占 1.6%；4 个交易所频道 3 天共 9 条，但抓取没有报错。旧代码对「频道关闭网页预览」「窗口内无新消息」「消息只有图片」都静默返回 0，无法区分。

## 变更

| 项 | 内容 |
| --- | --- |
| 诊断 | 每个频道记录名称、订阅数、页面可见条数、窗口内条数、保留条数、最新消息时间，写入 Actions 日志（`· @频道: …`）与运行摘要「Telegram 频道」表 |
| 试运行 | `TelegramChannelConfig.probe`：照常抓取与诊断，内容不进入选稿；试运行频道全部失败不会让 Telegram 来源判为失败 |
| 新增试运行频道（11） | `wublockchainenglish`、`wublockchain`、`theblockbeats`、`PANewsLab`、`foresightnews`、`whale_alert_io`、`lookonchainchannel`、`peckshieldalert`、`investigations`、`Bitget_Announcements`、`TreeNewsFeed` |
| AI 信源 | 启用 Simon Willison（改用只含正式文章的 `/atom/entries/`）、量子位；新增 Google DeepMind、The Verge AI、TechCrunch AI、MIT Technology Review AI。启用的 AI 类 RSS 从 4 个增至 10 个 |
| 暂停 | Kraken Blog、吴说 Substack（持续 403；吴说由 Telegram 候选接替） |

频道名来自公开资料，本环境无法访问 t.me 核实，因此全部以试运行上线。转正方法：看运行摘要中的名称、订阅数与最新消息时间，确认是官方频道且有产量后，删除该频道的 `"probe": true`。

## 验证

- `uv run pytest` 全部通过（离线；Telegram 页面用 MockTransport 模拟）。新增：频道诊断计数与身份、试运行内容不进入结果、仅试运行频道失败不影响来源状态、运行摘要表格。
- `uv run python scripts/check_governance.py` 通过。

## 尚未验证

- 新频道名与新 RSS 地址均未做真实请求；上线后第一次 Feed Collection 的「Telegram 频道」表和 RSS 计数会给出结果，失败或名称不符的再调整。
- 现有 4 个交易所频道产量低的原因，待诊断表给出。

## 下一步（需维护者决定）

1. 根据诊断表转正真实的频道、删除不存在或冒名的。
2. 若交易所频道因关闭网页预览而无法抓取，改用交易所官方公告接口或页面。
3. Telegram 稳定后评估缩减 Google News。
