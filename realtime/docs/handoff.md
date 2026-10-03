# 当前交接

## Current execution pointer
当前目标：项目统一为xiyunews，阶段3完整历史已合并；当前准备Cloudflare单项目入口，不改变原实时运行方式和规则。
任务 Issue / 负责人：https://github.com/ohxiyu/xiyunews/issues/198；本轮唯一迁移整合负责人，根交接是唯一执行指针；Issue196 / PR197 基础已完成合并。
工作分支 / 最后提交 / PR：agent/xiyunews-edge-cutover，基线91fb5981cd09a51be7c3ef8c355eb6ee179f60fa；本阶段[PR199](https://github.com/ohxiyu/xiyunews/pull/199)保持Draft。PR195已保留完整历史，服务器运行d6a9d3f，不将文档或边缘基础main SHA当服务器已重新部署。
已经完成：原项目完整历史以 git subtree add 导入；根 CI 为 realtime 增加路径门控及 3.11/3.12 独立矩阵；治理兼容子目录；新部署从主仓完整 SHA 的 realtime 前缀打包。历史证据保留，提醒阈值、地址簿、信源、队列与目的地没有更改。
尚未完成：Cloudflare 单项目生产切换；服务器运行新仓 d6a9d3f，@xiyunewsbot 已取得三类自然回执，最新共18条sent。原群23:22:48已按确认统一名为xiyu.news，简介和话题不变。PR197最终99d2465e全部可用检查通过并已合并，当前串行Issue198；边缘未切换，看门狗私聊目的地及KV保留，新品牌正文代码仍未部署。
已运行的验证及结果：公网 health 为 2.6.0/d6a9d3f29ef93c138842342c973b3049fb7bc252，三 spot 分片 live，MainPID235825/NRestarts0、21:03:05 启动。进程 Token 与配置一致、getMe 为 xiyunewsbot、原群 administrator，排除 Token 后全部配置与备份相同；后续切换时间后的原 SQLite 共 11 条 sent、6 条 archived，无失败状态，最新自然行情 1251、公告 1250、资金流向 1249。历史旧 Bot 失败保留，不重放，证据见新 Bot 发布记录。
尚未验证的内容：手机收件、看门狗实际私聊告警，以及新 Cloudflare 项目的生产接管。新 Bot 自然 message_id 已核验，21:24 也核验收到切换后的私聊 /start 且私聊可读取，不重复要求；未与加密 ALERT_CHAT_ID 直接比对，也没有发送测试告警。现役看门狗 21:10:23/21:15:23 两轮自然 Cron 均 ok，但无告警不能代替实际私聊送达。
线上版本 / 对应源码提交：后端2.6.0 = 新仓d6a9d3f29ef93c138842342c973b3049fb7bc252，源码未再发布；上一release和数据库备份保留，回滚须单独授权。看门狗21:03:11.654的Secret Change版本a5330597-ee57-4a61-91f0-9a34cb431676全量生效，只改TELEGRAM_BOT_TOKEN，未部署新业务代码或统一Worker。
阻塞与所需权限：Cloudflare 统一项目运行 Secret 安全注入与自动部署配置尚缺，现役服务和旧 release 保留。新 Bot 管理员、三类自然消息和 /start 已有证据，不再列为待操作。本次 Token 授权不扩大为新 Cloudflare 持久访问、群权限变更或提前删除旧资源。
下一步具体动作：基础PR197已合并，当前Issue198/PR199已补齐统一暂停Worker的8个运行Secret及仓库部署Secret，实际目标来源与原setup_watchdog.sh一致，详见[本轮记录](releases/cloudflare-settings-20261003.md)。新入口已占用xiyunews，采用transfer路径，不能再原地改为同名；最终配置完成本机回归，远端CI后才合并。保持原服务器/话题/原看门狗Cron与KV，新自然调度尚未启用；正式域/DO/Cron受控切换和手机/实际告警验收继续按根唯一指针执行。

## 系统现状

| 位置 | 内容 |
| --- | --- |
| 东京服务器 fomobtc-tokyo（47.79.36.171） | systemd `fomobtc`：全部采集、去重、推送；nginx：`api.fomobtc.com` 只读接口，`fomobtc.com`/`www` 302 到群组；certbot 定时续期两张证书 |
| Cloudflare（账号 Drminutes） | DNS：A `@`、`www`、`api` → 47.79.36.171，全部 DNS only；看门狗 Worker `fomobtc-watchdog`（每 5 分钟，KV `STATE`） |
| 私有 `ohxiyu/xiyunews/realtime/` | 原历史及独立测试通过 PR195 进入 main；服务器新仓 SHA、新 Bot 管理员和三类自然回执已核验，Cloudflare 接管和旧仓退役尚未完成 |

Telegram 原群保留（话题开启、成员只读；2026-10-02 23:22:48 getChat 回读已更名为 `xiyu.news`，简介未改），机器人为管理员 `@xiyunewsbot`，不合并到日报频道：
- 📈 行情异动（话题 3）：币安 USDT 现货最近 3 分钟涨跌超过 2%/3%/5%（按 24h 成交额）并持续 3 秒；同币同向 1 小时一次，再涨跌 10% 立即再提醒，附 24 小时新高/新低。单条为 1 分钟 K 线图 + 中英双语 + 市值，同一秒到期多条合并为文字。
- 📢 交易所公告（话题 5）：Binance（官方流 + 中文官网）、OKX、Bybit、Bitget、Bithumb、Hyperliquid；Upbit、Bithumb 新交易对。优先官方中文，“标题 + 摘要 + 要点”。
- 💰 资金流向（话题 7）：币安地址簿（168 个地址）在 Ethereum、BNB Chain、Arbitrum、Base、TRON 上 ≥ 1000 万美元的单笔流入/流出。
- 运维提醒不进群：看门狗通过同一机器人私聊运营者。

## 配置与密钥位置
- 服务器 `/etc/fomobtc.env`（root 0600）：机器人 Token、群组 ID、三个话题 ID、币安公告只读 Key、SOURCE_COMMIT 等；历次修改前的备份为 `/etc/fomobtc.env.bak-*`（话题切换前的备份含运营者私聊 ID）。
- Cloudflare Worker 密钥：`fomobtc-watchdog` 的 TELEGRAM_BOT_TOKEN、ALERT_CHAT_ID。2026-10-02新Bot安全切换只更新Token，保留既有ALERT_CHAT_ID；不要重跑会取旧私聊ID和发测试消息的历史setup_watchdog.sh。
- 门槛与策略：`config/thresholds.yaml`；币安地址簿：`config/exchange_addresses.json`。
- SSH：运营者电脑 `/Users/minutesdr/.ssh/xiyunews_tokyo_config`（主机 xiyunews-tokyo，兼容 fomobtc-tokyo；专用私钥只在运营者电脑，严格指纹校验）。连接验证见 [记录](releases/ssh-access-20261002.md)。

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

最近证据：[新Bot切换](releases/deploy-20261002-xiyunews-bot.md)、[新仓部署](releases/deploy-20261002-xiyunews-repository.md)、[2.6.0](releases/2.6.0.md)、[全部发布记录](releases/README.md)。
