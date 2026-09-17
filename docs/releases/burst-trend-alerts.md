# 突发与趋势预警重做（Issue #33）

基线：main 782e45341fdb0b41a00c0e3d3b567595a4d23d43（UI PR #32 已合并）。
用户确认替换旧规则；实现分支 feat/burst-trend-alerts。

## 变化
- USDT 现货滚动 60/180 秒涨跌、成交额分组阈值、3 秒确认。
- 15 分钟收盘判断 6h/24h 强弱及突破前 24h 高低点。
- source/symbol/type/direction SQLite 原子门控，取消同币24小时限制。
- 同方向同秒命中合并，门控后的实际分量生成统一网页/Telegram中文标题。
- 启动与缺口预热、过期不报、历史只种参考；旧 pending 行情置过期，不重放 unknown。

## 验证
合成逐笔及 K 线回放覆盖短针、双向、精确滚动、强窗口选择、慢涨、前24h极值、未收盘、缺口、重复、过期、未来事件、冷却边界、持久化重启、突破追加、合并部分过滤及旧策略迁移。
模拟 Binance WebSocket+REST→检测器→合并→SQLite→Telegram 格式链路验证两个检测器合为一条、网页与通知标题一致；未发送真实 Telegram 消息。
本地 Python 67 项、Ruff、Mypy、compileall、仓库契约及前端回归/构建通过；这些测试不是真实 ZEC 历史回放，不证明准确率或生产延迟。

## 线上与限制
2026-09-17 公开 /api/health 仍报告 2.1.0 / 185fabf590abe65cf7f943433d85a9ce69889d13，policy 仍为 86400 秒，Telegram disabled。本轮尚未部署。
Cloudflare whoami 未认证；Safari 为登录页；本机缺少服务器 SSH 配置，已有 Workbench 尚未用于本轮部署。不能将构建或合并称为上线。
部署前停服务并备份 SQLite。保留旧 release 及其虚拟环境；迁移不删除历史，新 policy state 表可与旧表共存。回滚会恢复旧行为，旧 24h 门控也可能读取新预警；回滚源码后必须单独核验。
每币双窗口最多各 50000 价格变化点，超限暂停并重建；需后续真实负载观察。低频成交无法满足连续3秒观测时不报突发；趋势仍可独立工作。新上市历史不足24h时只有突发可用。

实现提交 ee0e0071542640dbddad4892e89842471ecc997e 的 [CI #62](https://github.com/ohxiyu/fomobtc/actions/runs/35175051363) 与 [Repository contracts #59](https://github.com/ohxiyu/fomobtc/actions/runs/35175051385) 成功；最终 head 和合并状态见 [PR #34](https://github.com/ohxiyu/fomobtc/pull/34)。
