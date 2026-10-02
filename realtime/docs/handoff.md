# 当前交接

## Current execution pointer
当前目标：阶段 3 将实时提醒并入私有 ohxiyu/xiyunews/realtime，保留历史、独立依赖、原运行方式及全部业务规则。
任务 Issue / 负责人：https://github.com/ohxiyu/xiyunews/issues/172；本轮唯一迁移整合负责人。
工作分支 / 最后提交 / PR：agent/xiyunews-realtime；主项目基线 d5360740bb571c6bf95d3fcb631a54ac00634e9f；导入旧仓 main 7807126d8c7cdb51e18f0b91ba27f500271f9f08，未 squash；PR 待建立。
已经完成：原项目完整历史以 git subtree add 导入；根 CI 为 realtime 增加路径门控及 3.11/3.12 独立矩阵；治理兼容子目录；新部署从主仓完整 SHA 的 realtime 前缀打包。历史证据保留，提醒阈值、地址簿、信源、队列与目的地没有更改。
尚未完成：远端 CI、merge commit合并及祖先核验；阶段4原可信SSH入口恢复和新仓实际重新部署；Cloudflare单项目切换。运营者2026-10-02确认原Token已撤销，并报告Bot已换、原频道改名；安全历史上传门槛已解除，不调用或输出旧凭据。旧仓退役仍必须等待新仓实际部署验收，不提前删除。
已运行的验证及结果：2026-10-01 公网 health 回读仍为 2.6.0/b226b625cf3875b6693e0768d75d88d50b33c08d，Telegram 开启、三个 spot 分片 live；这是旧部署，不是本次迁移部署验收。离线验证执行结果见本阶段发布记录及 PR。
尚未验证的内容：新仓合并 SHA 部署、自然推送 message_id、服务器进程与看门狗状态；历史手机回执不作为本次证据。
线上版本 / 对应源码提交：后端 2.6.0 = b226b625cf3875b6693e0768d75d88d50b33c08d（上一版 2.5.1 = 8f1751ef7f7ce403007965ab136d039657420461，可回滚；2.5.0 = 1739fe3e97f077ed5d4e2dbe4ecb3cebbd55e7c6 仍在服务器）；nginx = scripts/deploy/nginx.conf；看门狗 Worker 版本 55671d87-29c2-4225-8bdf-176cb4712ed3。
阻塞与所需权限：仅确认两个已知 fomobtc_tokyo_config 路径不存在，尚不能断言本机没有私钥；目标主机没有已验证的known_hosts条目，原配置路径待提供，不猜用密钥或关闭指纹验证。旧Token撤销已获运营者确认，不再作为上传阻塞；不生成替代访问权限、不修改密钥，不清理旧release。Cloudflare统一项目尚未切换，现役服务保留。
下一步具体动作：检查全绿后以 merge commit 合并（禁止 squash/rebase），核对导入的旧 main 是新 main 的祖先；再按 deployment.md 从新仓发布。上轮已完成事项归档于 releases，旧 backlog 不授权顺带执行。

## 系统现状

| 位置 | 内容 |
| --- | --- |
| 东京服务器 fomobtc-tokyo（47.79.36.171） | systemd `fomobtc`：全部采集、去重、推送；nginx：`api.fomobtc.com` 只读接口，`fomobtc.com`/`www` 302 到群组；certbot 定时续期两张证书 |
| Cloudflare（账号 Drminutes） | DNS：A `@`、`www`、`api` → 47.79.36.171，全部 DNS only；看门狗 Worker `fomobtc-watchdog`（每 5 分钟，KV `STATE`） |
| 本地 `ohxiyu/xiyunews` 的 `realtime/` 导入候选 | 原项目历史及独立测试已准备，远端 main 尚无 realtime/；旧仓待部署验证后归档 |

Telegram 群组 fomobtc（`-1004364162227`，已开启话题，成员只读，仅保留表情回应；入口邀请链接 https://t.me/+mdTufn9GK1UyODk0 ，名称 fomobtc.com）：
- 📈 行情异动（话题 3）：币安 USDT 现货最近 3 分钟涨跌超过 2%/3%/5%（按 24h 成交额）并持续 3 秒；同币同向 1 小时一次，再涨跌 10% 立即再提醒，附 24 小时新高/新低。单条为 1 分钟 K 线图 + 中英双语 + 市值，同一秒到期多条合并为文字。
- 📢 交易所公告（话题 5）：Binance（官方流 + 中文官网）、OKX、Bybit、Bitget、Bithumb、Hyperliquid；Upbit、Bithumb 新交易对。优先官方中文，“标题 + 摘要 + 要点”。
- 💰 资金流向（话题 7）：币安地址簿（168 个地址）在 Ethereum、BNB Chain、Arbitrum、Base、TRON 上 ≥ 1000 万美元的单笔流入/流出。
- 运维提醒不进群：看门狗通过同一机器人私聊运营者。

## 配置与密钥位置
- 服务器 `/etc/fomobtc.env`（root 0600）：机器人 Token、群组 ID、三个话题 ID、币安公告只读 Key、SOURCE_COMMIT 等；历次修改前的备份为 `/etc/fomobtc.env.bak-*`（话题切换前的备份含运营者私聊 ID）。
- Cloudflare Worker 密钥：`fomobtc-watchdog` 的 TELEGRAM_BOT_TOKEN、ALERT_CHAT_ID（由 `scripts/setup_watchdog.sh` 从服务器写入）。
- 门槛与策略：`config/thresholds.yaml`；币安地址簿：`config/exchange_addresses.json`。
- SSH：运营者电脑 `~/.ssh/fomobtc_tokyo_config`（主机 fomobtc-tokyo，私钥只在运营者电脑）。

## 部署与回退
- 后端：从 ohxiyu/xiyunews 根目录 `git archive <完整合并 SHA> realtime`，服务器 `tar -x --strip-components=1 -C /opt/fomobtc/releases/<SHA>`；后续独立 venv、停服务、SQLite 备份、切换和回退方式保持不变。SOURCE_COMMIT 必须是新仓完整 SHA，不是旧项目 SHA；详见 deployment.md。
- nginx：改 `scripts/deploy/nginx.conf` → 安装到 `/etc/nginx/sites-available/fomobtc` → `nginx -t` → reload；旧文件备份在 `/opt/fomobtc/backups/nginx-fomobtc-*.conf`。
- 看门狗：`scripts/deploy/watchdog` 目录内 `npx wrangler deploy`。
- 一次性配置脚本：`setup_telegram_topics.sh`（群组话题）、`setup_binance_announcements.sh`（币安只读 Key）、`setup_watchdog.sh`（看门狗凭据）；`setup_telegram.sh` 为早期私聊配置。
- 详细步骤见 [部署与回退](deployment.md)、[Telegram 运行与验收](telegram-runbook.md)。

## 已知限制（按设计）
- Hyperliquid 公告来自公开频道网页，约 15 秒，health 显示 degraded，因此 `/api/ready` 返回 503。
- Upbit 韩国站、Gate、MEXC 的公告接口在东京 403，只监测新交易对（Gate/MEXC 只记录不推送）；Bithumb 公告接口有 CDN 缓存，可能晚几分钟。
- 只推官方中英文，不做机器翻译；Bithumb 显示韩文原文，Hyperliquid 显示英文。
- 资金流向覆盖取决于地址簿；BSC/Base/Arbitrum 不扫原生币完整区块；Solana 暂不扫描。

最近证据：[2.6.0 部署](releases/deploy-20260925-simple-moves.md)、[2.6.0](releases/2.6.0.md)、[单机运行与看门狗](releases/single-host-watchdog.md)、[全部发布记录](releases/README.md)。
