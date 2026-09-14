# 当前交接

## Current execution pointer
当前目标：Issue #4 的来源鉴权、真实 Telegram 推送及长期稳定性验收；正式域名接入已完成。
任务 Issue / 负责人：[Issue #4](https://github.com/ohxiyu/fomobtc/issues/4) / Codex 实施，ohxiyu 认领。
工作分支 / 最后提交 / PR：deploy/activate-fomobtc-domain / [PR #8](https://github.com/ohxiyu/fomobtc/pull/8)，最终证据提交以 PR head 为准；已部署前端源码 5f652bf9b1e32c2bc0bd4603fefec17864acb1b7；此前 #3/#5/#6/#7 已合并。
已经完成：仓库已改名 fomobtc；东京 systemd 后台、SQLite 和资源上限运行；Dynadot NS 已切换 Cloudflare，3 条停放解析已确认删除；fomobtc.com 前端与 api.fomobtc.com HTTPS API 已上线；CORS/SSE、证书续期定时器已配置，模拟续期通过。
尚未完成：Telegram/Binance 公告凭据配置、真实推送回执与手机验收；Hyperliquid 当前为公共预览降级模式；24h 稳定性与峰值测试。Issue #4 保持开放。
已运行的验证及结果：既有 34 项测试与实现 CI 通过；PR #8 初次四项 CI 通过；公网前端/API 200、config.js 精确版本、CORS、安全头、HTTP 308、POST 403、SSE 刷新和心跳通过；浏览器显示真实行情和来源降级，行情筛选通过；Certbot 模拟续期成功。
尚未验证的内容：生产自动续期首次执行、24 小时稳定性、端到端 P95/P99、Binance 公告鉴权、Hyperliquid 客户端授权、Telegram API 回执及手机收件；不把本机判断延迟当作推送延迟。
线上版本 / 对应源码提交：前端 https://fomobtc.com / 2.0.0 / 5f652bf9b1e32c2bc0bd4603fefec17864acb1b7 / Worker 641abf82-4aec-49c7-98ed-9ed7c73350b4；后台 https://api.fomobtc.com / 2.0.0 / fe829b4b96002351c8237255bd96b02714d4d124。旧 workers.dev 路由已关闭，API_ORIGIN 已配置。
阻塞与所需权限：SSH、合并部署、域名切换和停放记录删除均已授权并执行；仍缺 Telegram Bot/Chat、Binance 公告密钥及可选 Hyperliquid 会话的位置。配置放 /etc/fomobtc.env（root 0600），密钥不进聊天或仓库。
下一步具体动作：用户提供安全配置位置后写入服务器环境；核对来源和单实例，按 deployment.md 验证一次明确测试通知，再启用常规发送；检查真实回执与手机收件，补充端到端与持续运行证据。不要重复部署或重新修改已生效 DNS。

## 五项状态
- 代码完成：2.0 实现与域名部署配置完成。
- 测试通过：本地和远端 CI 已通过；本次公网与浏览器检查通过，记录见发布文档。
- PR 合并：#3/#5/#6/#7 已合并；本轮 #8 的最终合并状态以 GitHub 为准。
- 部署成功：东京后台、正式域名前端与 HTTPS API 已部署。
- 线上验收通过：页面、采集、API/SSE 通过；来源鉴权与 Telegram 推送未完成，readiness 503 保持真实状态。

历史证据：[首次前端](releases/deploy-20260914-frontend.md)、[东京后台](releases/deploy-20260914-tokyo.md)、[正式域名与 HTTPS](releases/deploy-20260914-domain.md)。
