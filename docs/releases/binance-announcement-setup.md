# 币安公告只读 Key 一键配置

背景：对比 1ms.news，线上币安公告走公开接口轮询，发布到发现中位 129 秒、p90 180 秒（最近 60 条）；只请求 zh-CN 列表，只有英文版的公告会漏（例：2026-09-24 20:00 Trade bStocks 24/7）。官方公告 WebSocket 实现已存在，缺 Key。

## 变化
- scripts/setup_binance_announcements.sh：隐藏输入 Key/Secret；签名调用 /sapi/v1/account/apiRestrictions，未开读取或开启交易、提现、划转类权限即拒绝；备份 env（0600）后写入并重启；40 秒内 binance_announcements 未 live 自动恢复。

## 验证
- bash -n 通过；服务器 GNU date 支持毫秒时间戳；上传到服务器 /tmp 的副本 SHA-256 与仓库一致。
- 尚未用真实 Key 运行；运行后需记录 live 状态与后续公告延迟。
