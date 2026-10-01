# 稀有News 迁移：私有仓与生产回读

Issue: https://github.com/ohxiyu/xiyunews/issues/179

## 已合并、部署及验证

阶段 1 PR169（e12179905981ed2ff5c31811db41f4c5f7b259d1）和阶段 2 PR171（d5360740bb571c6bf95d3fcb631a54ac00634e9f）顺序合并。两仓 private=true、archived=false，协作者仅 ohxiyu；私有仓的 Pages Git 构建和生产部署实际成功，不只依赖历史公开仓链接。没有开通付费 Code Security 或套餐；当前 GitHub API 返回私有仓分支保护需升级，CodeQL 已跳过，不写成通过。合并仍逐项检查 main 同步、治理、CI 与预览。

Dynadot NS 为 ignat.ns.cloudflare.com 与 shaz.ns.cloudflare.com；新 zone active，xiyu.news 和 www.bmt.news 已绑定既有 bmtnews Pages。主站首页、2026/10/01/summary-zh、api/latest.json、feed.xml、openapi.json、llms.txt、about/contact/legal/media-kit 等 HTTPS 200，站名和 canonical 新域。域名配置未删除旧域，站点结构未改变。

存量 XML PR176（d115e7debbf70e8d4dfe6629592f283f5783e746）通过完整 931 项 pytest、治理、CI/预览；Deploy Docs 36825452488 成功，gh-pages 产物 09a14bf7c435a915f911c57e0b5f280331d446a9，对应 Pages 生产 cafb3ffc-9d8a-4c37-be2d-c3ca79a7cd1c，GitHub Pages 检查 completed/success。新部署地址和新域带校验查询的 sitemap、crypto-zh 200、旧域引用为 0；policy/technology/crypto-en 普通订阅亦为新域。普通 sitemap/crypto-zh 请求曾命中之前的 600 秒边缘缓存，过期后最终回读仍需补充，不将查询旁路验收写成普通请求已更新。

调度器部署版本 dd126dda-3c13-4e8d-b582-e2550c08cb98，health repository=ohxiyu/xiyunews、public_site_url=https://xiyu.news，ready 验证 actions:write 和 contents:read。2026-10-01 14:30:33 上海时间自然 workflow_dispatch 触发 Feed Collection 36825148528，head d12dfb1e355206f462d7e6752989a82dcbb72f3a；采集和事件发布成功，缓存分支持久化被 workflow 权限检查拒绝，整次运行 failure，未标全成功。

缓存修复 PR178 已合并 e83ecc29af080adda7e3ee4e91e765f04d060293：只更新缓存 blob，保留分支树和父历史，不 force、不扩大 GITHUB_TOKEN 权限、不手动写缓存分支、不重跑 AI。6 项本地裸仓回归和完整 937 项 pytest、治理、远端 CI 36826017262 均通过；Pages 预览 84ac5469-5f85-434c-8068-d9d37648be94 在 Safari 回读状态 success。合并后主分支的新脚本已可用于正常工作流，但首次自然缓存成功仍待实际运行。

## 明确未完成的部分

旧域 301 暂停，Pages 生产变量 LEGACY_REDIRECT_ENABLED=false；旧域首页仍可用，但任意未存在路径仍为 404，不声称所有旧路径 200/301。新域 /s/ 匿名 401 是 Worker fail-closed，不是已经可登录的 Access 页面。需操作时确认后保留原 owner email 策略和 AUD，追加新域 /s、/s/*、/admin、/admin/*、/api/admin、/api/admin/*，不扩大用户；实际登录和 Quick Post 成功后才启用旧域 301 并正常重新部署。阶段 1 Issue168 保持打开。

阶段 3 本地提交 1e6395f3a410233b817ce0c2ddaf9bd64fdf6f78，旧 main 7807126d8c7cdb51e18f0b91ba27f500271f9f08 为 unsquashed subtree 祖先；没有推送该历史或创建阶段 3 PR。历史扫描两份已删除 README 有同一疑似 Telegram Token，未读取到输出、未调用、未上传，需运营者确认已撤销；不以私有化代替撤销、不擅自 squash 或改写历史。Python 3.11/3.12 各 61 项、ruff/mypy/compileall/契约、3 项看门狗 Node 与当时根 929 项通过；同步最新 main 后重跑，阶段 3 合并必须使用 merge commit 保留祖先。

本机没有原 SSH 配置，不读取私钥或尝试不明连接。实时生产仍为 2.6.0、source_commit=b226b625cf3875b6693e0768d75d88d50b33c08d，三个现货分片在线；新仓 SHA、自然 message_id、看门狗无告警尚未验收，旧仓未归档。阶段 4 必须在原 SSH 电脑按 realtime 部署文档备份/切换/核对/回退。阶段 5 群名建议“稀有News · 实时快讯”，频道“稀有News”，简介加入 https://xiyu.news；措辞和实际改名仍由运营者确认，不提前改推送规则或目标。

Source commit: 网站 d115e7debbf70e8d4dfe6629592f283f5783e746；采集缓存脚本 e83ecc29af080adda7e3ee4e91e765f04d060293。
Worker version: dd126dda-3c13-4e8d-b582-e2550c08cb98（独立调度器）。
Deployment: Pages cafb3ffc-9d8a-4c37-be2d-c3ca79a7cd1c；artifact 09a14bf7c435a915f911c57e0b5f280331d446a9；正常 Actions，未手动 gh-pages 写入。
Verification: 主站/new XML/调度 ready 通过；普通 XML 旧缓存过期、Access/301、首次修复后自然缓存和实时新 SHA 未验证。
Rollback: 未执行回滚、删除、历史改写或旧仓归档；现有服务与群/频道保持。
