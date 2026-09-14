# 当前交接

## Current execution pointer
当前目标：完成 FomoBTC 2.0 改造、合并与部署，跟进 Issue #4 的生产接入验收。
任务 Issue / 负责人：[Issue #4](https://github.com/ohxiyu/fomobtc/issues/4) / Codex 实施，ohxiyu 认领。
工作分支 / 最后提交 / PR：`feat/fomobtc-platform`；基线 `00c5c6c`；最终实现提交以该分支 PR head 为准，PR 创建后更新记录。
已经完成：PR #3 已合并，仓库改名 fomobtc；异步行情、三家公告适配、SQLite 发件箱、只读 API 与静态前端、部署配置和测试实现完成；真实公共源本地试运行。
尚未完成：本轮 PR 创建与 CI 合并；Cloudflare 前端发布；VPS 后台部署与真实推送验收。
已运行的验证及结果：本地 34 项 pytest、Ruff、Mypy 通过；前端构建与 Wrangler dry-run 通过；真实行情约 100 秒接收 6.6 万条，队列无积压，计算 P99 约 0.04ms；详见发布验证记录。
尚未验证的内容：生产资源占用与端到端 P95/P99、24 小时稳定性、Binance 公告鉴权、Hyperliquid 客户端授权、Telegram API 真实回执及手机收件。
线上版本 / 对应源码提交：后台未知且未迁移；前端待本轮发布，不能用仓库 2.0.0 代替生产证明。
阻塞与所需权限：等待服务器 SSH 地址或别名、用户、安装路径及环境配置位置；Telegram Bot/Chat、Binance 公告密钥与可选 Hyperliquid 会话配置在服务器安全环境中。合并部署已获用户授权，不需重复批准。
下一步具体动作：检查最新 CI 后合并并部署静态前端，记录实际 SHA/Worker 版本；取得服务器接入后停止旧服务、迁移冷却、启动单实例、验收 API 与真实通知。

## 五项状态
- 代码完成：是，首版范围实现；公告覆盖限制见数据契约。
- 测试通过：本地通过，远端以 PR Checks 为准。
- PR 合并：PR #3 已合并；本轮实现待合并。
- 部署成功：本轮尚未部署；后台接入资料缺失。
- 线上验收通过：未完成。

历史交接存于 [2026-09-08 记录](releases/handoff-20260908.md)。
