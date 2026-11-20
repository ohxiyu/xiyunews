# Telegram 候选频道转正与翻页抓取

- Issue: [#154](https://github.com/ohxiyu/bmtnews-standalone/issues/154)
- Branch: `agent/telegram-sources`
- Scope: `data/config.github.json` 的 Telegram 频道、`src/scrapers/telegram.py` 翻页、`TelegramChannelConfig.pages`、诊断输出。其他信源不变。

## 依据

2026-09-28 19:46Z Feed Collection（run 36474557082）频道诊断，维护者 2026-09-29 确认「按建议调整」。

## 变更

| 频道 | 变更 |
| --- | --- |
| @wublockchainenglish、@lookonchainchannel、@investigations（ZachXBT） | 转正（去掉 `probe`） |
| @theblockbeats、@foresightnews | 转正，`pages: 3`、`fetch_limit: 60` |
| @peckshieldalert（冒名账号）、@wublockchain、@PANewsLab（无法抓取） | 删除 |
| @whale_alert_io、@TreeNewsFeed、@Bitget_Announcements | 保持候选 |

翻页：公开预览每页约 20 条。`pages > 1` 时按 `?before=<最早消息号>` 向前翻页，某页已早于采集窗口起点、翻页失败或没有更早消息时停止；已抓到的内容保留。相邻页重复的消息只保留一次。诊断日志与运行报告增加 `pages`。

## 成本

新增的 5 个频道进入采集，BlockBeats 与 Foresight 为中文快讯、频率较高，预筛与分析的模型调用会相应增加（沿用现有模型与额度，未提高上限）。

## 验证

- 新增测试：繁忙频道翻页直到覆盖窗口，窗口外消息不收录、不重复；首页已覆盖窗口时不翻页；默认只取一页。
- `uv run pytest` 全部通过；`uv run python scripts/check_governance.py` 通过。

## 尚未验证

- 上线后首次采集中两个中文频道的实际翻页数与收录量、分析成本变化。
