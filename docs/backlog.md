# 待办

| 优先级 | 范围 | 任务 | 验收 |
| --- | --- | --- | --- |
| P0 | 监控摘要、冷却分离、采集心跳 | [#9](https://github.com/ohxiyu/fomobtc/issues/9) | 已上线，最终合并状态见PR #10；现货取舍见spot-only-assessment.md |
| P0 | 改名、公告、实时行情、前端与部署 | [#4](https://github.com/ohxiyu/fomobtc/issues/4)，Codex / ohxiyu | 测试、CI、合并、前端和 VPS 分别验收 |
| P0 | 推送与公告源凭据 | #4 所需输入 | Telegram、Binance 公告 Key；Hyperliquid 客户端会话可选 |
| P1 | 长时间与峰值验收 | 尚未完成 | 24h 连续运行、行情峰值回放、真实收件与故障恢复 |
| P1 | 公告断线补全 | 后续独立 Issue | OKX 分页追赶、Binance 官方可用重放、Hyperliquid 深历史覆盖 |
| P2 | 滚动 180 秒策略 | 后续独立 Issue | 影子对比，不默默替换现有分钟桶口径 |

当前进度唯一来源为 [交接](handoff.md)，历史证据见 [发布记录](releases/README.md)。

实现 PR #5 已合并，Cloudflare 前端已发布；Issue #4 仅保留来源鉴权、真实推送与长期端到端验收未完成项。详见当前交接与发布证据。

P1 后续：增量订阅避免全量重建、分组阈值缓冲、尖峰确认影子对比；本轮不改变策略阈值。

## 当前优先级（无头服务）
1. P0：Telegram安全配置、中文消息格式、Bot API回执与手机收件、自然事件自动推送。验收按[运行手册](telegram-runbook.md)。
2. P1：官方中文缺失时的翻译配置与失败状态；不回填历史。
3. P2：24小时稳定性、断线恢复、端到端P95/P99。
2026-09-16 用户重新指定：前端与 Telegram 并行；Issue #31 先实现 bmt.news 风格信息流。Telegram 先私聊，安全配置与真实收件仍待完成。
