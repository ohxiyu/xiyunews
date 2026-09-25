# 网页前端下线

2026-09-25 用户确认产品只通过 Telegram 群组交付，“删掉 fomobtc 前端，前端没有存在的必要”。

## 变化
- 删除 web/（React + Vite 静态看板与前端测试）；CI 去掉 frontend 任务；仓库契约不再校验 web/package.json 版本；README、AGENTS、agent、部署、呈现规则、数据契约同步。历史发布记录不改写。
- 保留 VPS 只读 API（/api/health、/api/ready、/api/events、/api/stream）用于健康检查与排查；运行代码无变化，无需重新部署后端。
- Cloudflare Worker `fomobtc`（fomobtc.com）属于删除线上服务，由用户执行 `npx wrangler delete --name fomobtc`；api.fomobtc.com 的 DNS 记录与 VPS 不受影响。

## 验证
Python 91 项、Ruff、Mypy、仓库契约通过。
