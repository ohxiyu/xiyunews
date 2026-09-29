# 加密媒体同质化：来源分级与选稿

- Issue: [#156](https://github.com/ohxiyu/bmtnews-standalone/issues/156)
- Branch: `agent/source-diversity`
- Scope: `FilteringConfig.source_tiers` / `source_tier_limits`、话题去重的代表稿选择、平衡选稿的来源与分级上限、生产配置。信源本身不增减。

## 问题

9/10–9/29 共 251 条日报条目中，CryptoSlate 44、Decrypt 33、CoinDesk 26、Cointelegraph 23、The Defiant 20、Protos 12，6 家合计 158 条（63%）；单期 14 条里常有 8–11 条来自这几家。同一新闻多家报道时，去重保留的是候选列表中第一个出现的版本。

## 变更

| 项 | 内容 |
| --- | --- |
| 分级 | 一手：交易所官方频道、白宫/美联储/SEC/CFTC、公司博客与状态页、GitHub 版本、编辑精选；原创：CoinDesk、The Block、Blockworks、DL News、The Defiant、Protos、Glassnode、吴说英文、BlockBeats、Foresight、Lookonchain、ZachXBT、主流外媒、AI 媒体；其余为转述 |
| 去重代表稿 | 分数不低于最高分 1 分的版本中，一手 > 原创 > 转述，再按分数、发布时间 |
| 每家上限 | 3 → 2；按媒体名计数，RSS 与 Google News 共用 |
| 转述上限 | 加密版块最多 4 条转述稿；加密 9 条目标先在上限内选，不够再放开；AI 与政策版块不受影响 |
| 兜底 | 日报不足最低条数时仍放开每家与分级上限（与原规则一致） |

文档：`max_items_per_source` 的说明原写"只作用于借调"，与代码不符，已更正。

## 验证

- 新增 `tests/test_source_diversity.py`：分级查找与校验、转述上限与最低条数兜底、同一媒体跨渠道共用上限、去重保留一手/原创、加密目标优先且不挤占其他版块。
- `test_ranking_audit` 的补位测试使用未分级的虚构来源，关闭分级上限后只测补位机制。
- 暂存池（9/25–9/28，降噪前）旧/新规则对比：14 条全为转述 → 10 条转述 + 3 条原创。
- `uv run pytest` 全部通过；治理检查通过。

## 尚未验证

- 上线后连续几期日报的来源分布（目标：单期转述稿明显少于 8 条、每家不超过 2 条）。
