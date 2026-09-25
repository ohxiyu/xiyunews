# 待办

2026-09-25：网页前端已下线，下表中与前端相关的条目仅作历史保留。

| 优先级 | 范围 | 任务 | 验收 |
| --- | --- | --- | --- |
| P0 | 监控摘要、冷却分离、采集心跳 | [#9](https://github.com/ohxiyu/fomobtc/issues/9) | 已上线，最终合并状态见PR #10；现货取舍见spot-only-assessment.md |
| P0 | 改名、公告、实时行情、前端与部署 | [#4](https://github.com/ohxiyu/fomobtc/issues/4)，Codex / ohxiyu | 测试、CI、合并、前端和 VPS 分别验收 |
| P0 | 推送与公告源凭据 | #4 所需输入 | Telegram、Binance 公告 Key；Hyperliquid 客户端会话可选 |
| P1 | 长时间与峰值验收 | 尚未完成 | 24h 连续运行、行情峰值回放、真实收件与故障恢复 |
| P1 | 公告断线补全 | 后续独立 Issue | OKX 分页追赶、Binance 官方可用重放、Hyperliquid 深历史覆盖 |
| P0 | 突发与趋势策略 | [#33](https://github.com/ohxiyu/fomobtc/issues/33)、PR #34 | 用户批准替换；本地与CI通过，生产部署及真实行情验收待完成 |
| P0 | 行情覆盖与推送降噪 | 本轮 PR fix/burst-readiness-market-digest | 剔除下架币、滞回与增量分片、就绪口径修复、Telegram 大盘合并；部署后核验分片 live |

当前进度唯一来源为 [交接](handoff.md)，历史证据见 [发布记录](releases/README.md)。

实现 PR #5 已合并，Cloudflare 前端已发布；Issue #4 仅保留来源鉴权、真实推送与长期端到端验收未完成项。详见当前交接与发布证据。

P1 后续：真实负载与误报评估；2026-09-17 用户批准的新阈值和确认机制见数据契约。

## 当前优先级（无头服务）
1. P0：Telegram安全配置、中文消息格式、Bot API回执与手机收件、自然事件自动推送。验收按[运行手册](telegram-runbook.md)。
2. P1：官方中文缺失时的翻译配置与失败状态；不回填历史。
3. P2：24小时稳定性、断线恢复、端到端P95/P99。
2026-09-16 用户重新指定：前端与 Telegram 并行；Issue #31 先实现 bmt.news 风格信息流。Telegram 先私聊，安全配置与真实收件仍待完成。
