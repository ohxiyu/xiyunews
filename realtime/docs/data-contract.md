# 数据契约

## 行情（policy_version=3，2.6.0）
唯一规则（用户 2026-09-25：“行情有异动的时候，及时关注”）：任一币种最近 3 分钟涨跌超过门槛并持续 3 秒，立即提醒。

| 24h 成交额 | 3 分钟涨跌门槛 |
| --- | --- |
| ≥1 亿 USDT | 2% |
| ≥1000 万、<1 亿 | 3% |
| ≥50 万、<1000 万 | 5% |

范围：仅 Binance USDT 现货，24h quoteVolume ≥ 50 万 USDT 进入、低于 40 万才移出（滞回）；ticker closeTime 超过 1 小时视为已下架/暂停并排除（Binance 仍返回已下架币的旧统计）。每 600 秒更新成交额分组与 24 小时高低价。只订阅逐笔聚合成交（@aggTrade）。
分片成员稳定：新币只加入最后一个有空位的分片并只重启该分片；移出的币保留订阅但数据忽略，单分片累计超过 30 个才裁剪重启。成交额换组只更新门槛、清空确认候选，不清空价格窗口。
分片状态：ready 为窗口已预热的币数（安静币种两笔成交之间仍有效），括号内为 10 秒内有成交的数量；连接满 180 秒即为 live。
入口 [app.py](../src/platform/app.py)，采集 [market.py](../src/platform/market.py)，纯检测器与门控 [signals.py](../src/platform/signals.py)，参数 [配置](../config/thresholds.yaml)。

检测：参考价为 t−180 秒时刻及之前的最后成交价（不是分钟 K 线近似），涨跌对称；超过门槛后连续确认 3 秒，相邻观测超过 2 秒重置确认。
冷启动、断线、成交 ID 缺口后需重新积累 180 秒连续成交序列；不回放历史。重复/乱序不参与；过期超过 10 秒或超前超过 2 秒的成交清空窗口。每个窗口最多 50000 个价格变化点，同价压缩，超上限清空并预热，不使用截断参考。逐笔不落盘。
频率：同一币种同一方向 1 小时内只提醒一次；1 小时内价格较上次提醒价再涨（跌）≥ 10% 且仍满足 3 分钟门槛时立即再提醒，标题注明“较上次提醒再涨/跌 X%”，之后以这次的价格为准。上涨与下跌各自独立。门控持久化在 market_alert_state（提醒时间与价格），重启不重复；Telegram 关闭期间也记录门控，开启后不补发。采集端只在门控会放行时才生成事件，存储端在同一事务内再次判定。
24 小时新高/新低：每次刷新取 ticker 的 highPrice/lowPrice，之后用每笔成交延伸；24 小时最高（最低）价出现在本次 3 分钟窗口内时，标题附“创 24 小时新高/新低”。统计区间比严格 24 小时最多多一个刷新周期（10 分钟）。不称历史新高。
2.6.0 取消：60 秒窗口、15 分钟 K 线趋势（6h/24h、区间位置、突破追加）、回到门槛之下再越线（rearm）、1 秒合并缓冲。没有任何 3 分钟急动的缓慢涨跌不再提醒。
升级首次读取最近 1 小时内已提醒的币种与方向，冷却到期前不再提醒（旧记录没有价格，不能靠再涨 10% 提前）；旧 pending 行情通知置 expired，sending/unknown 不重放；保留历史事件。停机备份数据库后升级，不同时运行两份服务。
API 与 Telegram 使用同一个规范标题，行情无正文；公告规则独立。单条行情 Telegram 为最近 5 小时的 1 分钟 K 线图片（sendPhoto）+ 中英双语说明 + 市值（币安产品列表流通量×价格），多条为合并文字，图片失败时发送文字。

Telegram 行情合并（market_alerts.digest）：行情通知入队后保留 hold_seconds（默认 1 秒）再发送，发送时同一聊天所有已到期行情通知（最多 max_items=30 条）合并为一条消息，共享一个 message_id 与送达结果。按方向分节、按涨跌幅排序；同方向涉及 ≥ market_wide_symbols（默认 4）个币种时加标题“市场联动下跌/上涨 · N 个币种”。只有一条时发图片。网页不合并，仍每币一条事件；门控不变。

接口依据：[Binance 官方 WebSocket 协议](https://github.com/binance/binance-spot-api-docs/blob/master/web-socket-streams.md)、[REST 行情接口](https://github.com/binance/binance-spot-api-docs/blob/master/rest-api.md)。
门槛依据 2026-09-25 对 337 个交易对最近 24 小时 1 分钟 K 线的回放：旧规则实际约 286 条消息/天（趋势占 76%），新规则估算约 132 条/天（约每小时 5.5 条），大盘币 7 次。K 线回放是近似，线上逐笔结果以自然事件为准。

## 公告
[采集器](../src/platform/announcements.py) 使用官方来源。
- [Binance 公告](https://developers.binance.com/zh-CN/docs/products/announcements/announcement)：英文签名 WebSocket，需 API Key。文档没有文章 ID/URL，使用目录+发布时间+标题作为近似身份，只链接官方公告目录，不能假装是文章原文。标题修订无法可靠关联为同一篇。无断线重放，需标识覆盖缺口。
  配置只读 Key 后官方流与官网 CMS 中文列表（每 30 秒，状态 binance_catalog）并行：官方流英文正文立即就绪并推送；两份副本按 catalogId 相同且发布时间相差 ≤5 秒识别为同一篇（announcement_alias），只通知一次。官网副本后到时把该事件升级为 cms:code、详情链接并重新抓取中文正文，仅更新网页，已发送的通知不重发；官网副本先到则忽略官方流副本。只有英文版的官网文章也按英文就绪。
- [OKX 更新记录](https://www.okx.com/docs-v5/log_en/)：REST /api/v5/support/announcements，每 6 秒读取第一页；URL 路径作 ID，pTime 是首次发布时间，businessPTime 不用于延迟计算。第一页以外的长时间积压不保证补齐。
- [Hyperliquid 官方来源](https://hyperliquid.gitbook.io/hyperliquid-docs/support)：hyperliquid_announcements；公开预览每 15 秒轮询，有限历史和媒体内容缺失，明确 degraded。

首次采集仅基线归档，不推历史。source + source_id + 正文哈希去重，内容变化保存修订。分类是规则启发式，未知分类仍通知；营销类仅归档。标题与原文优先，未引入阻塞通知的 AI 摘要。推送要求正文就绪（2.3.0 起官方详情暂不可用最多等待 3 分钟后发送原文）：中文，或币安英文原文（官方流/仅英文文章），或交易所列表 API 的英文/韩文原文；OKX 与 Hyperliquid 英文仍等待翻译。去重摘要为标题+正文+链接，不含类别。

## 其他交易所（2.2.0）
[exchanges.py](../src/platform/exchanges.py)。公告 API：Bybit /v5/announcements/index（publishTime）、Bitget /api/v2/public/annoucements（cTime）、KuCoin /api/v3/announcements（cTime）每 5 秒；HTX support getList/v2（showTime）、Bithumb feed-api /v1/notices（published_at，KST，CDN 缓存）每 10 秒。均只取第一页，身份为交易所文章 ID 或 URL 路径，时间为交易所给出的发布时间。
新交易对：Upbit /v1/market/all、Bithumb /v1/market/all、Gate /api/v4/spot/currency_pairs、MEXC /api/v3/defaultSymbols。进程启动后首个列表只基线；之后新增的交易对生成“新增交易对”事件（category=listing），表示已开放或即将开放交易，不等于公告发布时刻。Gate/MEXC 为 quiet，只记录网页。
分类先用标题关键词，未命中再用交易所类型字段；活动/奖励类只归档。

## 语言版本与摘要（2.3.0）
announcement_i18n(event_id, lang, title, summary, points, url, method)。只保存交易所官方版本（official）或来源原文（original），不做机器翻译。Binance CMS 详情 zh-CN/en（英文专属文章在中文区返回英文，不计为中文）；OKX /zh-hans/help 与 /help 页面；Bybit en-US 与 zh-TW 列表按 art 编号对应；Bitget en_US 与 zh_CN 按 annId 对应；翻译晚到时后续轮询补写（不重复通知）。摘要为开头两句，要点为之后含日期、时刻、UTC、交易对或数值的最多两句。推送优先中文，其次英文，否则原文。HTX、KuCoin 已停止，历史行不列出。

## 资金流向（2.5.0）
[flows.py](../src/platform/flows.py)，地址簿 [exchange_addresses.json](../config/exchange_addresses.json)。只报币安地址簿与外部地址之间、按价格折算不低于 flows.threshold_usd 的单笔转账；地址簿之外的币安地址（如海量充值地址）不会被识别，覆盖率取决于地址簿。检查点只前进不跳块；以太坊原生 ETH 需回执 status=0x1；Solana 暂不扫描。事件发现时间为本机扫描到的时间，不是区块时间。

## 事件与交付
事件字段：id、kind、source、source_id、title、url、body、category、symbol、published、detected、updated、status、attempts、sent、error、telegram_id、dispatch_ms。
published 未知为 null，不填发现时间；detected 是本机首次保存时间。API 不暴露 chat 或 cooldown_key。
状态包括 baseline、archived、pending、sending、sent、failed、unknown、expired。
市场待发送事件 120 秒后过期，公告 1 小时；超时结果未知不自动重发；重启中的 sending 变为 unknown。行情门控从事件生成计时，与发送成功与否无关。行情可有最多 1 秒合并等待；默认同聊天 3.1 秒节流。429 遵守 retry_after；API 确认不是用户已读，5xx 重试不能承诺绝不重复。

## 查询
GET /api/events 支持 kind/source/q/before/limit，limit 最大 100；GET /api/health 返回运行版本与来源状态；GET /api/ready 对 blocked/degraded/error/warming 返回 503。只读 API 仅供健康检查与排查，没有浏览器客户端（无 CORS、无 SSE）。


## 历史兼容
旧的分钟桶、2小时分级冷却、同币24小时规则只保留在历史记录中，旧版 CoinSignal 源码已于 2026-09-25 删除（见 git 历史）。历史合约事件仍在数据库中；公告不受行情门控限制。

## 交付时间
行情列表在notification_status之外返回notification_sent（关联通知的API确认时间，未确认为null）；公告使用sent。确认不是手机已读。网页前端已于 2026-09-25 下线，这些字段仍由只读 API 提供。
