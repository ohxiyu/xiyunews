# 品牌迁移已上线部分与安全阻塞

Issue: https://github.com/ohxiyu/xiyunews/issues/173

本次为授权部署后的纯文档回写，不包含实时服务历史、密钥或新运行代码。历史扫描发现的值没有输出、没有测试其权限、没有推送；两仓私有不等于凭据安全问题已解决。

## 已合并和发布

PR169 合并为 e12179905981ed2ff5c31811db41f4c5f7b259d1，Deploy Docs 36823514928 成功，gh-pages 7fe7ed4c15610534c3d1609552616cf6dfc9cd4a、Cloudflare Pages c8c57131-fafc-4db1-bcb7-efea8feb0317 成功。

PR171 合并为 d5360740bb571c6bf95d3fcb631a54ac00634e9f，Deploy Docs 36824000303 成功，gh-pages a0f1608927767690964ed734b99d74fc8008829d 的 Cloudflare Pages check 为 completed/success。

Source commit: d5360740bb571c6bf95d3fcb631a54ac00634e9f。
Worker version: dd126dda-3c13-4e8d-b582-e2550c08cb98（调度器）。
Deployment: 原账户 wrangler deploy --keep-vars，显式 GITHUB_REPOSITORY=ohxiyu/xiyunews、PUBLIC_SITE_URL=https://xiyu.news，原 Secrets 未改；保留三条 Cron。过渡版本 ac52cef1 使用旧域检查，现已正常前进到新域，不是回滚。
Verification: 2026-10-01 06:25 UTC；https://xiyu.news 首页、2026/10/01/summary-zh、api/latest.json、feed.xml、sitemap.xml、api/quick-posts.json 均 200；title/canonical 为 xiyu.news。日报 14 条、generated_at=2026-09-30T23:28:59.968601Z，没有重跑 AI。调度 health 为新仓/新域、ready 为 actions:write 和 contents:read。下一次自然采集派发尚未记录。
Rollback: 未执行；不得自动回滚、重置队列或删除锁数据。实时旧版本与部署路径保持不变。

## 尚未完成

1. 旧域跳转开关 LEGACY_REDIRECT_ENABLED=false 仍保持过渡状态；bmt.news/www.bmt.news 继续 200，不声称 301 已完成。新域 Access 应用尚未迁移，/s/ 匿名 401 是 Worker 拒绝，不是登录页面。需确认复用既有应用的原策略保护新域六个后台路径，登录可用后再开启 301。
2. realtime 以不 squash 的 subtree 在本地准备；旧仓 main 7807126d8c7cdb51e18f0b91ba27f500271f9f08 是本地祖先。常见凭据模式扫描 654 个历史 blob，两份已删除 README 第 346 行含同一疑似 Telegram Token，非明显占位符；不能确认已撤销，因此本地提交 1e6395f3a410233b817ce0c2ddaf9bd64fdf6f78 不推送。需运营者确认撤销后，才能按要求保留完整历史继续；不擅自强推改写历史。
3. 本机没有原 fomobtc_tokyo_config，服务器仍是 2.6.0/b226b625cf3875b6693e0768d75d88d50b33c08d；只读 health 回读三个现货分片 live。新仓 SHA 切换、下一条自然 message_id 和看门狗状态未验证，旧仓不归档。
4. Telegram 群/频道实际改名尚未执行；保持两路目的地分开，不改 nginx fomobtc.com 跳转。建议文案仍为待确认：群名称“稀有News · 实时快讯”，简介“币安现货异动、交易所公告与链上资金流向。主站：https://xiyu.news”；日报频道名称“稀有News”，简介“每日加密与 AI 热点、事件追踪与周报：https://xiyu.news”。

## 验证边界

阶段 1–2 929 项 Python、64 项调度器、22 项后台 Node、治理/类型/dry-run 和远端 CI/Pages 均通过；私有 CodeQL 无付费许可时跳过，没有启用付费安全产品。本地 realtime 在 Python 3.11/3.12 各 61 项测试、ruff、mypy、compileall、仓库契约和 3 项看门狗 Node 通过；根 929 项再次通过。尚无阶段 3 远端 CI 或 PR，不把本地验证说成合并/服务器部署。

两仓 GitHub API 均 private=true、archived=false，协作者均仅 ohxiyu；Cloudflare Git 集成已经实测能拉取私有仓库并发布 gh-pages。未修改阈值、地址簿、数据库、systemd、服务路径、依赖或旧许可。
