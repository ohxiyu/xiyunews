# 迁移审计修复与架构回读

Issue: https://github.com/ohxiyu/xiyunews/issues/185

## 已完成的前序工作

PR182 全绿合并 21c96d4281e1cec771c7516d3722ea6ba6688c62，公开许可和 X 联系入口通过正常 Deploy Docs 36851300087 发布；Pages edf84841-0af3-470d-9a4e-47ec879e4a16，artifact d4958131d9066268eef025fb07f912b25ea2b54a。站内三份许可 200，llms/关于/法律说明已回读；普通联系页存在 600 秒旧缓存，继续等待普通链接更新，不将旁路算最终验收。

PR184 全绿合并 f0a2dc89d2fbcd702904379ffe0b7d197de88d02，私有队列到期调度部署到既有 Worker，版本 9774435b-1c72-4dad-9552-0440e2ab574f。部署工作树与合并 main 的树逐字一致（853b0d5c131ae64e571c467eb447e474a5e2dcab），health 返回 private-queue-due-v1，ready 确认 Actions:write 与 Contents:read；五分钟自然日志和首次到期派发继续验收。没有更换 Secrets、绑定、Cron 或付费方案。

新域 Access 六路径已保存且回读，旧六路径移除，原策略和 AUD 保留；匿名 /s 与管理 API 302 到验证码页，旧域管理入口拒绝。运营者已被提示在 Safari 完成验证码登录，不索取验证码或发布测试新闻。登录显示名修订仅准备，尚待操作时确认。

## 本阶段

按最新决定取消旧域入口与跳转：两个旧 Host 在 Worker 直接 410，无 Location、no-store、noindex，先于认证、缓存及私有读取；废弃变量不能恢复 301。没有删除域名注册、DNS、TLS、Pages 绑定或浏览器缓存。更新当前迁移手册，保留历史证据不改写。

Pages 预览发现状态分支误构建，已保存并重新打开设置回读：自定义预览包含 *，排除 staging-cache、x-queue、square-queue，生产 gh-pages 自动发布不变。新增 [系统架构](../system-architecture.md)，明确已运行与计划 realtime/ 导入的边界，记录缓存、发布、Quick Post、分发与安全成本口径。

Source commit: 本阶段基于 f0a2dc89d2fbcd702904379ffe0b7d197de88d02，尚未合并。
Worker version: 独立调度器 9774435b-1c72-4dad-9552-0440e2ab574f；本站 Worker 的 410 尚未发布。
Deployment: 前序 Pages edf84841-0af3-470d-9a4e-47ec879e4a16；本阶段待正常 Actions 发布。
Verification: 已通过 942 项 pytest 和 79 项站点 Node 回归；19:00 上海时间的真实 Cron 为采集 fresh、广场 idle、X idle、今日日报 healthy（14 条）。普通联系页 200 且使用 X @ohxiyu，旧缓存已自然过期。治理、CI、生产 410 和首次自然到期派发继续核验。
Rollback: 未回滚、删除资源或写入生产状态分支；恢复旧入口须另行授权代码变更。

## 不可跳过的条件

旧历史疑似凭据撤销状态、原 SSH 配置、新仓实时部署及自然回执、Telegram 实际改名、登录后 Quick Post 尚未完成。私有仓分支保护和 CodeQL 是套餐限制，本轮未购买升级，不将跳过写成安全扫描通过；现有 CI、依赖审计与逐项合并检查继续。

## 正式生产回读（2026-10-01 11:12 UTC）

本节为 Issue187 的纯文档跟进，更新前述“待发布”快照。PR186 于 11:06 UTC 全绿合并为 3b8f2b5cd82e257783c99501e6494e495bb20ca7；Deploy Docs 36853256492 正常 success，没有重跑 AI。gh-pages 产物 c74d90926376852660aa8b56ab2deb35fc624c9e，对应 Pages 生产 216fd183-cd53-4140-a744-ff6b48ff1bd6，产物提交的 Cloudflare Pages 检查 completed/success。站点 Worker 源文件与 main 对应 blob 均为 0540e73a1b1b7609bde67d58d84247175faa6f40。

首次回读的旧域仍为 200/403/404，当时生产构建 in_progress，未当作验收通过；完成后重新检查两个 Host，各 13 个首页、文章、API、RSS、sitemap、openapi、llms、后台、带查询参数与不存在路径，全部 410、无 Location、Cache-Control=no-store。新域首页、日报、latest API、RSS、sitemap、openapi、llms、contact 在普通无校验查询链接 200，HTML canonical 为新域，contact 使用 https://x.com/ohxiyu。前序关于、法律、媒体、开发者、追踪、实体、周报、PWA 与三份许可共 23 个公开路由均 200；后台匿名请求仍跳至既有 Access，实际验证码登录后 Quick Post 尚未验收。

后续自然 schedule 采集 36853175538 success，事件发布和 staging-cache 持久化步骤均 success。缓存提交 926e93c07a066b9bbb2b003a1c14c747c4482769 的父为前序 2fc2aca12acc21fb53255c7cd201976811bef127，未 force；该状态提交无 Pages check，与已保存的排除配置一致。调度器 ready 200，19:00 上海时间真实 Cron 已验证 fresh/idle/idle/healthy；首次自然到期发帖仍未发生，不用测试消息代替。

实时服务健康接口仍为原仓 source_commit=b226b625cf3875b6693e0768d75d88d50b33c08d、三个现货分片 live，链上检查零区块延迟；Hyperliquid 为既有 degraded，ready 503，不宣称全系统健康或新仓已部署。原仓未归档，两仓仍 private=true、archived=false。Access 显示名仅准备修改，待操作时确认；安全条件与套餐限制仍按上节保留。

Source commit: 3b8f2b5cd82e257783c99501e6494e495bb20ca7
Worker version: 独立调度器 9774435b-1c72-4dad-9552-0440e2ab574f；站点 Worker 随 Pages 216fd183-cd53-4140-a744-ff6b48ff1bd6 发布。
Deployment: Deploy Docs 36853256492 success；gh-pages c74d90926376852660aa8b56ab2deb35fc624c9e；Pages 正式检查 success。
Verification: 942 项 pytest、79 项站点 Node、84 项调度器测试及治理/远端 CI；新域 200 与旧域 26 路径 410 验收通过，未完成项如上。
Rollback: 没有回滚、强推、手工写生产状态分支、删除基础设施或更换 Secrets；未修改实时服务规则与目标群。
