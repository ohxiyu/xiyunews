# 当前交接

## Current execution pointer
当前目标：无进行中的开发任务。系统已稳定运行“采集 → Telegram 群组话题推送”，接手后先核对线上状态，再按用户新需求开工。
任务 Issue / 负责人：无开放 Issue；运营者 ohxiyu，最近一轮开发为 Claude（2026-09-24/25）。
工作分支 / 最后提交 / PR：仓库只有 main；最近合并为本交接更新 PR（docs/handoff-current-state）；线上后端源码 8f1751ef7f7ce403007965ab136d039657420461。
已经完成：2.5.1 精简上线（仅采集与推送）；资金流向并入（原 cex.top 已从 Cloudflare 与 GitHub 彻底删除）；推送切换到开启话题的群组且成员只读；网页前端下线，fomobtc.com 由服务器 nginx 302 到群组；Cloudflare 只剩 DNS 与看门狗；服务器只保留当前与上一版 release；已合并分支与过时 Issue 已清理。
尚未完成：Solana 资金流向（公共 RPC 在东京被拒/限流，需带 Key 的免费 RPC）；币安地址簿按新一期储备金证明更新；24 小时稳定性与误报评估；看门狗故障演练。
已运行的验证及结果：线上 health 为 2.5.1/8f1751e、Telegram 开启、各来源 live/polling（Hyperliquid 按设计为 degraded）；fomobtc.com 与 www 的 http/https 任意路径 302 到群组；证书续期演练成功；看门狗读取 health 无异常项；cex.top 的 3 个 Worker、D1 与仓库均已不存在。
尚未验证的内容：看门狗在真实故障时的私聊提醒；24 小时连续稳定性；各交易所自然公告的端到端延迟统计。
线上版本 / 对应源码提交：后端 2.5.1 = 8f1751ef7f7ce403007965ab136d039657420461（上一版 2.5.0 = 1739fe3e97f077ed5d4e2dbe4ecb3cebbd55e7c6，可回滚）；nginx = scripts/deploy/nginx.conf；看门狗 Worker 版本 55671d87-29c2-4225-8bdf-176cb4712ed3。
阻塞与所需权限：Cloudflare DNS 只能由用户在后台修改（wrangler 登录没有 DNS 权限）；永久删除（Cloudflare 资源、GitHub 仓库、服务器文件）由用户本人执行；Solana 需要 RPC Key。
下一步具体动作：按用户新需求开工；可选：安排一次约 12 分钟的计划内停服验证看门狗提醒与恢复通知，或按新 PoR 扩充 config/exchange_addresses.json。

## 系统现状

| 位置 | 内容 |
| --- | --- |
| 东京服务器 fomobtc-tokyo（47.79.36.171） | systemd `fomobtc`：全部采集、去重、推送；nginx：`api.fomobtc.com` 只读接口，`fomobtc.com`/`www` 302 到群组；certbot 定时续期两张证书 |
| Cloudflare（账号 Drminutes） | DNS：A `@`、`www`、`api` → 47.79.36.171，全部 DNS only；看门狗 Worker `fomobtc-watchdog`（每 5 分钟，KV `STATE`） |
| GitHub `ohxiyu/fomobtc` | 只有 main；CI：Python 3.11/3.12 测试、仓库契约、看门狗 node 测试 |

Telegram 群组 fomobtc（`-1004364162227`，已开启话题，成员只读，仅保留表情回应；入口邀请链接 https://t.me/+mdTufn9GK1UyODk0 ，名称 fomobtc.com）：
- 📈 行情异动（话题 3）：币安 USDT 现货突发（1/3 分钟）与趋势（6/24 小时）；单条为 K 线图 + 中英双语 + 市值，同时到期多条合并为文字。
- 📢 交易所公告（话题 5）：Binance（官方流 + 中文官网）、OKX、Bybit、Bitget、Bithumb、Hyperliquid；Upbit、Bithumb 新交易对。优先官方中文，“标题 + 摘要 + 要点”。
- 💰 资金流向（话题 7）：币安地址簿（168 个地址）在 Ethereum、BNB Chain、Arbitrum、Base、TRON 上 ≥ 1000 万美元的单笔流入/流出。
- 运维提醒不进群：看门狗通过同一机器人私聊运营者。

## 配置与密钥位置
- 服务器 `/etc/fomobtc.env`（root 0600）：机器人 Token、群组 ID、三个话题 ID、币安公告只读 Key、SOURCE_COMMIT 等；历次修改前的备份为 `/etc/fomobtc.env.bak-*`（话题切换前的备份含运营者私聊 ID）。
- Cloudflare Worker 密钥：`fomobtc-watchdog` 的 TELEGRAM_BOT_TOKEN、ALERT_CHAT_ID（由 `scripts/setup_watchdog.sh` 从服务器写入）。
- 门槛与策略：`config/thresholds.yaml`；币安地址簿：`config/exchange_addresses.json`。
- SSH：运营者电脑 `~/.ssh/fomobtc_tokyo_config`（主机 fomobtc-tokyo，私钥只在运营者电脑）。

## 部署与回退
- 后端：git archive 已合并的 main SHA → `/opt/fomobtc/releases/<SHA>` → 在该目录 `python3 -m venv venv` 并 `pip install --require-hashes -r requirements.lock`（每个 release 独立 venv）→ 编译与导入检查 → 停服务、SQLite 备份 API 备份到 `/opt/fomobtc/backups/<时间>-before-<SHA>` → 原子切换 `/opt/fomobtc/current`、更新 SOURCE_COMMIT → 启动并核验 `/api/health`。失败或回退：指回上一版 release 并重启（数据库备份保留）。
- nginx：改 `scripts/deploy/nginx.conf` → 安装到 `/etc/nginx/sites-available/fomobtc` → `nginx -t` → reload；旧文件备份在 `/opt/fomobtc/backups/nginx-fomobtc-*.conf`。
- 看门狗：`scripts/deploy/watchdog` 目录内 `npx wrangler deploy`。
- 一次性配置脚本：`setup_telegram_topics.sh`（群组话题）、`setup_binance_announcements.sh`（币安只读 Key）、`setup_watchdog.sh`（看门狗凭据）；`setup_telegram.sh` 为早期私聊配置。
- 详细步骤见 [部署与回退](deployment.md)、[Telegram 运行与验收](telegram-runbook.md)。

## 已知限制（按设计）
- Hyperliquid 公告来自公开频道网页，约 15 秒，health 显示 degraded，因此 `/api/ready` 返回 503。
- Upbit 韩国站、Gate、MEXC 的公告接口在东京 403，只监测新交易对（Gate/MEXC 只记录不推送）；Bithumb 公告接口有 CDN 缓存，可能晚几分钟。
- 只推官方中英文，不做机器翻译；Bithumb 显示韩文原文，Hyperliquid 显示英文。
- 资金流向覆盖取决于地址簿；BSC/Base/Arbitrum 不扫原生币完整区块；Solana 暂不扫描。

最近证据：[单机运行与看门狗](releases/single-host-watchdog.md)、[2.5.1](releases/2.5.1.md)、[全部发布记录](releases/README.md)。
