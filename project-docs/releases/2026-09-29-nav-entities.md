# 导航收缩与实体页收录

- Issue: [#144](https://github.com/ohxiyu/bmtnews-standalone/issues/144)
- Branch: `agent/nav-entities`
- Scope: 站点导航、PWA 快捷方式、读者可见的「事件线」文案、实体页生成规则。事件数据、周报内容不变。

## 变更

| 项 | 基线 | 现在 |
| --- | --- | --- |
| 导航 | 信息流 / 事件线 / 实体 / 周报（顶部、App 底部、PWA 快捷方式） | 信息流 / 追踪 / 周报；底部导航改为 3 列；公共 CSS 改动已同步 `asset_version` |
| 文案 | 「事件线」「全部事件线」「查看事件线」等 | 「追踪」「全部追踪」「查看追踪」等；旧链接迁移说明保留原措辞 |
| 实体 | 28 个实体，15 个占位页；Claude 与 Anthropic、HYPE 与 Hyperliquid 分开 | 按资料库别名折算后，只保留有资料的主体（生产归档模拟：11 个）；此前发布、现不收录的实体页改为 `noindex` 跳转到 `/entity/`；sitemap 只含收录主体 |
| 资料库 | Hyperliquid 别名 HyperCore/HyperEVM | 增加 HYPE |

生产归档模拟保留：Coinbase、Anthropic、OpenAI、SEC、Solana、CFTC、Kraken、Hyperliquid、Cosmos、Bybit、EVM。Tether、Circle、Robinhood 等因无资料不再生成实体页；如需收录，在 `src/entity_profiles.json` 补资料与别名。

## 验证

- `uv run pytest` 与 `node --test tests/test_pwa_reader.mjs` 全部通过；新增别名折算与未收录过滤、跳转页 `noindex` 测试；PWA 测试改为三项导航且不含实体入口。
- `uv run python scripts/check_governance.py` 通过。

## 尚未验证

- 上线后首期日报生成的实体索引与跳转页，需在 gh-pages 上确认。
