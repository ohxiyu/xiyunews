# 数据契约

## 行情（Issue #33 / policy_version=2）
仅 Binance USDT 现货，24h quoteVolume ≥ 50 万 USDT 进入、低于 40 万才移出（滞回）；ticker closeTime 超过 1 小时视为已下架/暂停并排除（Binance 仍返回已下架币的旧统计）。每 600 秒更新成交额分组。
分片成员稳定：新币只加入最后一个有空位的分片并只重启该分片；移出的币保留订阅但数据忽略，单分片累计超过 30 个才裁剪重启。成交额换组只更新阈值、清空确认候选，不清空价格窗口。
分片状态：burst ready 为窗口已预热的币数（安静币种两笔成交之间仍有效），括号内为 10 秒内有成交的数量；连接满 180 秒且趋势历史齐全（上市不足 24h 的新币除外）即为 live。
入口 [app.py](../src/platform/app.py)，采集 [market.py](../src/platform/market.py)，纯检测器 [signals.py](../src/platform/signals.py)，参数 [配置](../config/thresholds.yaml)。

| 24h 成交额 | 滚动 60 秒涨跌 | 滚动 180 秒涨跌 |
| --- | --- | --- |
| ≥1 亿 USDT | 1.5% | 2.5% |
| ≥1000 万、<1 亿 | 2.5% | 4% |
| ≥50 万、<1000 万 | 4% | 6% |

突发：使用 t−60s / t−180s 时刻及之前最后成交价作为参考，涨跌对称，超阈连续确认 3 秒。两个窗口取变化/阈值比最大的一个；一秒内同币同方向突发与趋势合并。
冷启动、断线、成交 ID 缺口后需重新积累 180 秒连续成交序列；不回放突发历史。重复/乱序不参与；过期超过 10 秒或超前超过 2 秒事件清空窗口；相邻观测超过 2 秒重置确认候选。分组过期或换组重新预热。
每个窗口最多 50000 个价格变化点；同价压缩，超上限清空并预热，不使用截断参考。逐笔不落盘。

趋势：仅 15 分钟收盘时检查 6h 涨幅≥5% 或 24h≥8%，且收盘价位于最近 24h 高低区间顶部 10%；下跌镜像。取超阈比例更高的时间窗。突破必须收盘价超过当前 K 线之前连续 96 根 15m K 线的最高价；新低镜像。称“24 小时新高/低”，不称历史新高。净涨跌与区间位置捕捉持续强弱，不代表每根 K 线单调上涨或下跌。
Binance 不返回无成交的 15m K 线：REST 历史内部空缺及同一连接内两根收盘之间的空缺按前收盘价补平线；末尾连续无成交（最近成交早于最后一根 K 线结束）不视为历史缺失。连接中断重建窗口，不跨连接补线。REST 只补完整已收盘历史，不生成旧预警；历史不足或中断不判定。新收盘事件超过 10 秒不发；未收盘不判定；重连仅未来新收盘评估。历史缺失重试每币不快于 60 秒，共享最多 3 个 REST 并发。

持久化去重：source+symbol+类型+方向独立。突发同方向 15 分钟冷却，且必须回到两个阈值之下后重新越线，越线时刻需在冷却结束后。趋势同方向 6 小时一次，期间可额外追加一次未报过的突破；追加不延长原 6 小时窗口。合并事件逐分量检查，标题按实际通过分量重新生成。Telegram 关闭也记录相同门控，启用不补推。旧 24h 限制废止。
升级首次读取近期旧预警方向，继承 15 分钟冷却并要求重新越线；旧 pending 行情通知置 expired，sending/unknown 不重放；保留历史。停机备份数据库后升级，不同时运行两份服务。
前端和 Telegram 使用同一个规范标题，行情无正文；公告规则独立。

Telegram 行情合并（market_alerts.digest）：行情通知入队后保留 hold_seconds（默认 3 秒）再发送，发送时同一聊天所有已到期行情通知（最多 max_items=30 条）合并为一条消息，共享一个 message_id 与送达结果。按方向分节、按涨跌幅排序；同方向涉及 ≥ market_wide_symbols（默认 4）个币种时加标题“市场联动下跌/上涨 · N 个币种”。只有一条时仍只发规范标题。网页不合并，仍每币一条事件；门控不变。

接口依据：[Binance 官方 WebSocket 协议](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md)、[REST 行情接口](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)。
阈值是初始规则参数，合成测试不证明真实行情准确率，真实 ZEC 回放和自然事件验收另行记录。

## 公告
[采集器](../src/platform/announcements.py) 使用官方来源。
- [Binance 公告](https://developers.binance.com/zh-CN/docs/products/announcements/announcement)：英文签名 WebSocket，需 API Key。文档没有文章 ID/URL，使用目录+发布时间+标题作为近似身份，只链接官方公告目录，不能假装是文章原文。标题修订无法可靠关联为同一篇。无断线重放，需标识覆盖缺口。
  配置只读 Key 后官方流与官网 CMS 中文列表（每 30 秒，状态 binance_catalog）并行：官方流英文正文立即就绪并推送；两份副本按 catalogId 相同且发布时间相差 ≤5 秒识别为同一篇（announcement_alias），只通知一次。官网副本后到时把该事件升级为 cms:code、详情链接并重新抓取中文正文，仅更新网页，已发送的通知不重发；官网副本先到则忽略官方流副本。只有英文版的官网文章也按英文就绪。
- [OKX 更新记录](https://www.okx.com/docs-v5/log_en/)：REST /api/v5/support/announcements，每 6 秒读取第一页；URL 路径作 ID，pTime 是首次发布时间，businessPTime 不用于延迟计算。第一页以外的长时间积压不保证补齐。
- [Hyperliquid 官方来源](https://hyperliquid.gitbook.io/hyperliquid-docs/support)：hyperliquid_announcements；公开预览每 15 秒轮询，有限历史和媒体内容缺失，明确 degraded。可选授权 Telegram 客户端订阅新增和编辑，重连补最近 100 条，仍非无限回放。

首次采集仅基线归档，不推历史。source + source_id + 正文哈希去重，内容变化保存修订。分类是规则启发式，未知分类仍通知；营销类仅归档。标题与原文优先，未引入阻塞通知的 AI 摘要。推送要求正文就绪：中文，或币安英文原文（官方流/仅英文文章），或交易所列表 API 的英文/韩文原文；OKX 与 Hyperliquid 英文仍等待翻译。去重摘要为标题+正文+链接，不含类别。

## 其他交易所（2.2.0）
[exchanges.py](../src/platform/exchanges.py)。公告 API：Bybit /v5/announcements/index（publishTime）、Bitget /api/v2/public/annoucements（cTime）、KuCoin /api/v3/announcements（cTime）每 5 秒；HTX support getList/v2（showTime）、Bithumb feed-api /v1/notices（published_at，KST，CDN 缓存）每 10 秒。均只取第一页，身份为交易所文章 ID 或 URL 路径，时间为交易所给出的发布时间。
新交易对：Upbit /v1/market/all、Bithumb /v1/market/all、Gate /api/v4/spot/currency_pairs、MEXC /api/v3/defaultSymbols。进程启动后首个列表只基线；之后新增的交易对生成“新增交易对”事件（category=listing），表示已开放或即将开放交易，不等于公告发布时刻。Gate/MEXC 为 quiet，只记录网页。
分类先用标题关键词，未命中再用交易所类型字段；活动/奖励类只归档。

## 事件与交付
事件字段：id、kind、source、source_id、title、url、body、category、symbol、published、detected、updated、status、attempts、sent、error、telegram_id、dispatch_ms。
published 未知为 null，不填发现时间；detected 是本机首次保存时间。API 不暴露 chat 或 cooldown_key。
状态包括 baseline、archived、pending、sending、sent、failed、unknown、expired。
市场待发送事件 120 秒后过期，公告 1 小时；超时结果未知不自动重发；重启中的 sending 变为 unknown。行情门控从事件生成计时，与发送成功与否无关。行情可有最多 1 秒合并等待；默认同聊天 3.1 秒节流。429 遵守 retry_after；API 确认不是用户已读，5xx 重试不能承诺绝不重复。

## 查询
GET /api/events 支持 kind/source/q/before/limit，limit 最大 100；GET /api/health 返回运行版本与来源状态；GET /api/ready 对 blocked/degraded/error/warming 返回 503。GET /api/stream 仅推送刷新提示，断线后重新查询数据库，不依赖 SSE 内存历史。


## 历史兼容
旧的分钟桶、2小时分级冷却、同币24小时规则仅保留在历史记录及 legacy 源码中，当前入口不使用。实时页隐藏历史合约，历史页保留；公告不受行情门控限制。市值辅助模块不启动。

## 前端交付时间
行情列表在notification_status之外返回notification_sent（关联通知的API确认时间，未确认/null）；公告使用sent。UI分别显示detected采集时刻与推送确认时刻，确认不是手机已读。老后端缺少notification_sent时显示未知，不使用行情归档sent替代。
