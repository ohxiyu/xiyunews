# 2026-09-14 Cloudflare 前端部署

部署状态：deployed
源码提交：206c616aa56971f9331f8b1c84f7d52b6deec4ef
运行版本：Cloudflare Worker fomobtc / f1ae7fad-3b5e-449e-ada4-054fb57c2b62 / 应用 2.0.0
验收结果：2026-09-14 04:22 UTC，首页浏览器打开成功；config.js HTTP 200 且 revision 与源码一致，Cache-Control no-store、CSP、nosniff、DENY 生效；API_ORIGIN 为空，页面显示“待接入后端”，全部指标为缺失占位，无伪造实时数据。仅前端验收通过，后台采集和真实推送未投产。
回退信息：首次创建同名 Worker，创建前查询确认不存在（10007）；无历史可回退版本。需要撤回时停用该 Worker 的公开路由；保留代码和后台状态，后续版本记录旧 Worker ID 再切换。
授权记录：用户 2026-09-14 明确要求“一次完成改造并且合并部署”；沿用免费边界，未购买服务器。

访问地址：[FomoBTC](https://fomobtc.drminutes.workers.dev)。
实现：[PR #5](https://github.com/ohxiyu/fomobtc/pull/5)，四项 CI 全通过后 squash merge。
发布命令：web/ 中使用上述 SOURCE_COMMIT 构建，wrangler deploy --keep-vars。
后台阻塞：缺服务器接入与 Telegram/Binance 公告安全配置；Hyperliquid 完整客户端接入另需已授权会话。
本地公共源试运行进程已停止，8097/8098 无监听；未把用户电脑当生产服务器。
