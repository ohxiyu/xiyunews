# 当前交接

## Current execution pointer
当前目标：2.6.0 行情异动简化为单一规则并直接部署（用户 2026-09-25：“及时关注，请你给我优化简化逻辑”“改完直接部署”）：最近 3 分钟涨跌超过 2%/3%/5%（按成交额）并持续 3 秒即提醒；同币同向 1 小时一次，再涨跌 10% 立即再提醒；附 24 小时新高/新低。
任务 Issue / 负责人：无 Issue（用户在会话中直接提出）；运营者 ohxiyu，开发 Claude（2026-09-25）。
工作分支 / 最后提交 / PR：feat/simple-move-alerts（本 PR，基于 main b075aa3）；最终提交记录在 PR 中。
已经完成：检测、门控、推送文案、配置与文档改为单一规则；删除趋势、60 秒窗口、rearm、1 秒合并缓冲；修复分片含已移出币时重启即退出的问题。此前事项（2.5.1 精简、资金流向并入、群组话题、网页下线、看门狗）见 [发布记录](releases/README.md)。
尚未完成：合并并部署 2.6.0；线上自然行情推送验收；Solana 资金流向；币安地址簿按新一期储备金证明更新；看门狗故障演练。
已运行的验证及结果：Python 61 项、Ruff、Mypy、仓库契约通过；本机只读运行接入币安实时逐笔流，结果见 [2.6.0](releases/2.6.0.md)。
尚未验证的内容：生产环境的自然行情推送（新格式、约 132 条/天、检测到送达约 5 秒）；看门狗真实故障提醒；24 小时连续稳定性。
线上版本 / 对应源码提交：后端 2.5.1 = 8f1751ef7f7ce403007965ab136d039657420461（上一版 2.5.0 = 1739fe3e97f077ed5d4e2dbe4ecb3cebbd55e7c6）；nginx = scripts/deploy/nginx.conf；看门狗 Worker 版本 55671d87-29c2-4225-8bdf-176cb4712ed3。
阻塞与所需权限：无（用户已授权合并与部署）；Cloudflare DNS 只能由用户在后台修改；永久删除由用户本人执行；Solana 需要 RPC Key。
下一步具体动作：CI 通过后合并；按“部署与回退”发布到 /opt/fomobtc/releases/<SHA>（独立 venv、停服务并备份数据库后切换），核验 health 为 2.6.0、三个 spot 分片 live、market_alert_state 迁移结果；观察首条新格式行情推送；写部署记录并更新本交接。

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
