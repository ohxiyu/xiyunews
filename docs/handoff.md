# 当前交接

## Current execution pointer
当前目标：完成 FomoBTC 2.0 改造、合并与部署，跟进 Issue #4 的生产接入验收。
任务 Issue / 负责人：[Issue #4](https://github.com/ohxiyu/fomobtc/issues/4) / Codex 实施，ohxiyu 认领。
工作分支 / 最后提交 / PR：实现 [PR #5](https://github.com/ohxiyu/fomobtc/pull/5) 已合并，源码 `206c616aa56971f9331f8b1c84f7d52b6deec4ef`；部署证据分支 `docs/fomobtc-deployment-evidence`，最终文档提交以该 PR head 为准。
已经完成：PR #3 已合并，仓库改名 fomobtc；异步行情、三家公告适配、SQLite 发件箱、只读 API 与静态前端、部署配置和测试实现完成；真实公共源本地试运行。
尚未完成：VPS 后台部署、来源鉴权与真实推送验收；Issue #4 保持开放。
已运行的验证及结果：本地 34 项测试、Ruff/Mypy/compileall/仓库契约通过；PR #5 的 Python 3.11/3.12、frontend、repository 四项 CI 全通过；Cloudflare 页面与 config.js HTTP 200，源码版本一致，安全头有效；本地筛选搜索与移动端检查通过。
尚未验证的内容：生产资源占用与端到端 P95/P99、24 小时稳定性、Binance 公告鉴权、Hyperliquid 客户端授权、Telegram API 真实回执及手机收件。
线上版本 / 对应源码提交：[Cloudflare 前端](https://fomobtc.drminutes.workers.dev) 2.0.0，源码 `206c616aa56971f9331f8b1c84f7d52b6deec4ef`，Worker `f1ae7fad-3b5e-449e-ada4-054fb57c2b62`；API_ORIGIN 未配置，显示“待接入后端”。后台未迁移，旧线上版本未知。
阻塞与所需权限：等待服务器 SSH 地址或别名、用户、安装路径及环境配置位置；Telegram Bot/Chat、Binance 公告密钥与可选 Hyperliquid 会话配置在服务器安全环境中。合并部署已获用户授权，不需重复批准。
下一步具体动作：取得服务器 SSH 接入与安全配置位置后，按 deployment.md 停止旧服务、迁移冷却、部署上述源码、配置前端 API_ORIGIN 并重新发布，验收健康与真实通知；无需再次请求合并部署批准。

## 五项状态
- 代码完成：是，首版范围实现；公告覆盖限制见数据契约。
- 测试通过：本地 34/34；PR #5 四项远端检查通过。
- PR 合并：PR #3 与本轮实现 PR #5 均已合并。
- 部署成功：前端已部署；后台接入资料缺失，未部署。
- 线上验收通过：前端页面、版本与缺失数据提示通过；采集与推送未完成。

历史交接存于 [2026-09-08 记录](releases/handoff-20260908.md)。
