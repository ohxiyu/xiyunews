# 清理失效信源

- Issue: [#160](https://github.com/ohxiyu/bmtnews-standalone/issues/160)
- Branch: `agent/source-cleanup`
- Scope: `data/config.github.json` 信源、`GoogleNewsConfig.extra_queries` 与 Google News 抓取、配置文档。

## 依据

Feed Collection 164、168、169、170（9/27–9/29）：

| 信源 | 结果 |
| --- | --- |
| GDELT | 4/4 次 429 限流，0 条 |
| Bitcoin Magazine RSS | 4/4 次 403 |
| The Block、The Defiant 正文抓取 | 每次 7–21 个请求全部 403（标题与摘要正常） |
| Wu Blockchain Substack、Kraken Blog | 已停用，403/429 |

## 变更

| 项 | 内容 |
| --- | --- |
| GDELT | 删除；由 Google News 第二条搜索接替：加密关键词 × 路透、彭博、FT、WSJ、CNBC、美联社、Axios、Fortune、纽约时报、经济学人（`site:`），并保留原 20 家主流外媒域名白名单，归入加密市场 |
| Google News | 新增 `extra_queries`（每条独立的分类、条数与域名过滤；一条失败不影响其他；同一篇只保留一次）；链接还原上限 40 → 60 |
| RSS | 删除 Bitcoin Magazine、Wu Blockchain Substack（吴说已用 Telegram）、Kraken Blog |
| 正文 | The Block、The Defiant 不再抓正文，使用 RSS 自带摘要 |
| 分级 | Google News 中主流外媒的名称（AP News、The Economist、POLITICO 等）归入原创报道 |

RSS 由 33 个减为 30 个（启用 26 个）。

## 验证

- 新增测试：多条搜索各自分类与过滤、跨搜索去重、一条失败不影响其他。
- `uv run pytest` 全部通过；治理检查通过。

## 尚未验证

- 主流外媒搜索在生产中的实际条数（本环境无法访问 Google News）。
