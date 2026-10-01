# 币安官方公告流推送与中英副本去重

背景：2026-09-24 用户配置只读 Key 后，binance_announcements 变为 live，但官方流只有英文、推送要求中文正文，且中文轮询被替换，币安公告不再推送到 Telegram（发现时尚无新公告受影响）。

## 变化
- 有 Key 时官方流与官网中文列表轮询并行（binance_catalog，polling）。
- announcement_alias：catalogId 相同且发布时间 ≤5 秒视为同一篇，只通知一次；官网副本后到则升级事件为 cms:code、详情链接并重新抓取中文（仅网页），先到则忽略官方流副本。
- 币安英文正文（官方流或仅英文文章）直接 ready/en 并可推送；推送门槛由仅中文放宽为中文或币安英文。
- 营销关键词补充 tournament/voucher/carnival/win up to/瓜分，英文活动公告与中文一致只归档。

## 验证
- Python 75 项（新增官方流英文推送后官网副本升级不重发、官网先到抑制官方流、不同目录/时间不合并）、Ruff、Mypy、仓库契约通过。
- 官网列表字段 catalogId/releaseDate（毫秒）已在东京服务器实测；官方流 publishDate 与 releaseDate 是否逐毫秒一致尚未实测，容差 5 秒；不一致时退化为中英各推一次，不会漏推。
