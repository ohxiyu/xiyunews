# Telegram 名称确认与未完成操作

Issue: https://github.com/ohxiyu/xiyunews/issues/191

运营者确认 Telegram 展示名改为 `xiyu.news`。本次仅更新 [品牌执行清单](../telegram-brand-migration.md) 与 [当前交接](../handoff.md)，替换未采用的频道和实时群建议名称，明确简介仍是建议、实际 Telegram 元数据未修改、看门狗标题代码未发布。日报频道与实时话题群仍独立，不改变目标 ID、话题、权限、消息长度、信源或提醒规则。

本机默认 SSH 配置未找到 fomobtc 或已记录服务器 IP 的入口，只查看配置匹配和文件名，没有读取私钥或试用不明凭据。旧历史疑似 Telegram Token 尚未确认撤销，阶段 3 完整历史禁止上传；可信服务器登录入口仍未恢复。运营者询问是否可删除旧域不是删除授权，本次未删除 DNS zone、Pages 自定义域、项目或 Worker。

Source commit: 5d7dee1dca000777aa77103e9b1e42a806df3e97（本次文档基线）。
Worker version: not changed；最近已验证独立调度器 9774435b-1c72-4dad-9552-0440e2ab574f，网站仍由 Pages 项目 bmtnews 承载。
Deployment: 纯过程文档无需生产部署；Telegram 实际改名、看门狗部署和服务器迁移未执行。
Verification: 2026-10-01 14:44 UTC，普通 xiyu.news 首页 200，bmt.news 首页 410 且无 Location，xiyu.news NS 为 ignat/shaz.cloudflare.com。完整 942 项 pytest、治理与 diff 检查通过；精确 changed-range 与远端 CI 随本次 PR 核验，不将文档合并等同于社交账号改名。
Rollback: 本次未回滚、强推、手工写生产状态分支、修改密钥或删除资源；既有运行服务保持不变。
