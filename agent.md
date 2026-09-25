# FomoBTC 接手入口

先读 [AGENTS.md](AGENTS.md)（长期规则），再读 [当前交接](docs/handoff.md)（唯一当前状态与 Current execution pointer），运维操作见 [Telegram 运行与验收](docs/telegram-runbook.md) 和 [部署与回退](docs/deployment.md)。

## 产品一句话
采集币安现货行情异动、交易所官方公告与链上币安资金流向 → 去重 → 推送到一个开启话题的 Telegram 群组（📈 行情异动 / 📢 交易所公告 / 💰 资金流向）。没有网页；fomobtc.com 只跳转到群组。

## 系统在哪里
- 东京服务器 fomobtc-tokyo：systemd `fomobtc`（全部采集与推送）+ nginx（`api.fomobtc.com` 只读健康检查、fomobtc.com 跳转）。
- Cloudflare：只有 DNS 与看门狗 `fomobtc-watchdog`（服务器外每 5 分钟检查，异常私聊运营者）。
- GitHub `ohxiyu/fomobtc`：只有 main 分支。

## 开工清单
1. `git fetch`，确认 main 与服务器 `/opt/fomobtc/current` 的源码 SHA 一致。
2. 查看 `https://api.fomobtc.com/api/health`：版本、各来源状态、Telegram 开关。
3. 读交接的 Current execution pointer；接新任务时先更新指针，完成后更新交接与发布记录。

## 不要做
- 不重新引入网页前端、不恢复合约监控、不补推历史公告、不做机器翻译、不购买付费服务，除非用户明确要求。
- 不在 git、日志、对话中输出任何密钥；永久删除操作（Cloudflare 资源、GitHub 仓库、服务器文件）请用户本人执行。
- 不同时运行两个服务实例；改 DNS 需用户在 Cloudflare 后台操作。
