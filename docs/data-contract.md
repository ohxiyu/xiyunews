# 数据契约

## 行情
新运行入口 [app.py](../src/platform/app.py)，计算实现 [market.py](../src/platform/market.py)。
Binance USDT 现货与合约，24h quoteVolume 为 USDT，不是假定等值的美元。
每 600 秒更新成交额分组（最低 50 万 USDT；spot MID 1000 万/HIGH 1 亿；futures MID 1000 万/HIGH 2 亿）。阈值由 [配置](../config/thresholds.yaml) 读取。
以 aggregate trade 更新当前分钟价格，与前三个分钟桶的收盘价格比较；保留旧分钟桶口径但改为逐事件评估，不称滚动 180 秒收益率。
冷启动/重连用 REST 回填已收盘参考条；当前桶由流更新。非有限价格、非正价格、重复和乱序跳过；交易 ID 缺口清空参考并重新回填，过期 10 秒以上事件不触发。分组超过两次刷新间隔未更新时停止触发。
原始逐笔成交不落盘。环形窗口最多五个分钟桶。本机窗口判断 P99 不含上游网络、持久化、队列或 Telegram 延迟。

## 公告
[采集器](../src/platform/announcements.py) 使用官方来源。
- [Binance 公告](https://developers.binance.com/zh-CN/docs/products/announcements/announcement)：英文签名 WebSocket，需 API Key。文档没有文章 ID/URL，使用目录+发布时间+标题作为近似身份，只链接官方公告目录，不能假装是文章原文。标题修订无法可靠关联为同一篇。无断线重放，需标识覆盖缺口。
- [OKX 更新记录](https://www.okx.com/docs-v5/log_en/)：REST /api/v5/support/announcements，每 6 秒读取第一页；URL 路径作 ID，pTime 是首次发布时间，businessPTime 不用于延迟计算。第一页以外的长时间积压不保证补齐。
- [Hyperliquid 官方来源](https://hyperliquid.gitbook.io/hyperliquid-docs/support)：hyperliquid_announcements；公开预览每 15 秒轮询，有限历史和媒体内容缺失，明确 degraded。可选授权 Telegram 客户端订阅新增和编辑，重连补最近 100 条，仍非无限回放。

首次采集仅基线归档，不推历史。source + source_id + 正文哈希去重，内容变化保存修订。分类是规则启发式，未知分类仍通知；营销类仅归档。标题与原文优先，未引入阻塞通知的 AI 摘要。

## 事件与交付
事件字段：id、kind、source、source_id、title、url、body、category、symbol、published、detected、updated、status、attempts、sent、error、telegram_id、dispatch_ms。
published 未知为 null，不填发现时间；detected 是本机首次保存时间。API 不暴露 chat 或 cooldown_key。
状态包括 baseline、archived、pending、sending、sent、failed、unknown、expired。
市场待发送事件 120 秒后过期，公告 1 小时；发送失败不进入成功冷却，超时结果未知不自动重发；重启中的 sending 变为 unknown。明确无 Telegram 模式的行情只归档并记录处理冷却，避免无限生成相同信号。
发送确认后默认两小时 market/symbol 冷却。首次立即调度，默认同聊天 3.1 秒节流以兼容群组。429 完整遵守 retry_after。API 确认不是用户已读，5xx 重试也不能承诺绝不重复。

## 查询
GET /api/events 支持 kind/source/q/before/limit，limit 最大 100；GET /api/health 返回运行版本与来源状态；GET /api/ready 对 blocked/degraded/error/warming 返回 503。GET /api/stream 仅推送刷新提示，断线后重新查询数据库，不依赖 SSE 内存历史。
