# 待办

| 优先级 | 范围 | 任务 | 验收 |
| --- | --- | --- | --- |
| P0 | 改名、公告、实时行情、前端与部署 | [#4](https://github.com/ohxiyu/fomobtc/issues/4)，Codex / ohxiyu | 测试、CI、合并、前端和 VPS 分别验收 |
| P0 | 推送与公告源凭据 | #4 所需输入 | Telegram、Binance 公告 Key；Hyperliquid 客户端会话可选 |
| P1 | 长时间与峰值验收 | 尚未完成 | 24h 连续运行、行情峰值回放、真实收件与故障恢复 |
| P1 | 公告断线补全 | 后续独立 Issue | OKX 分页追赶、Binance 官方可用重放、Hyperliquid 深历史覆盖 |
| P2 | 滚动 180 秒策略 | 后续独立 Issue | 影子对比，不默默替换现有分钟桶口径 |

当前进度唯一来源为 [交接](handoff.md)，历史证据见 [发布记录](releases/README.md)。

实现 PR #5 已合并，Cloudflare 前端已发布；Issue #4 仅保留来源鉴权、真实推送与长期端到端验收未完成项。详见当前交接与发布证据。
