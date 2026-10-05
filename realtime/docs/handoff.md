# 当前交接

## Current execution pointer

当前目标：实时 API 从旧域迁到 api.xiyu.news；唯一执行指针为根[交接](../../project-docs/handoff.md)。

任务 Issue / 负责人：https://github.com/ohxiyu/xiyunews/issues/216；当前 Codex 会话为唯一编辑和生产整合负责人。

工作分支 / 最后提交 / PR：agent/realtime-api-domain，基于744791f5f6eab5dddc5a6f0ccd62aaa682018fe3；PR待创建，不编辑此前旧分支。

已经完成：确认旧监控/API未迁移；新增专用DNS-only A到47.79.36.171，独立api.xiyu.news证书签发（到期2027-01-03）；nginx完整配置备份。根1044项、Worker102项、watchdog7项和typecheck/audit0通过，无真实AI/测试消息。

尚未完成：新TLS配置安装及边界验证、业务PR合并、统一Worker部署与自然Cron核验、上线证据文档PR。

已运行的验证及结果：Google/Cloudflare新域A回读正确；nginx-t及HTTP-only ACME404通过，证书签发成功。旧服务MainPID235825/NRestarts0保持，没有重启、切换源码或数据库。

尚未验证的内容：新域HTTPS/ready/POST/未知路径、Worker新URL部署、自然Cron和手机告警收件；不因健康200宣称全部来源ready。

线上版本 / 对应源码提交：发送应用2.6.0/d6a9d3f29ef93c138842342c973b3049fb7bc252不变；Worker仍496f3131-144e-4a25-ae59-44f5b47b6b34/744791f5，未部署本次变更。

阻塞与所需权限：本次明确授权已覆盖DNS、证书、nginx及监控Worker部署；不包含旧域删除、密钥/发送目标修改或回滚，不再询问同一授权。

下一步具体动作：PR同步main全绿后合并，安装新旧API共存配置并nginx-t/reload（不重启fomobtc），新API正常后用根现有cloudflare-unified.yml发布；自然Cron/STATE只读核验，不重置KV或造故障。详见[本次记录](../../project-docs/releases/2026-10-05-realtime-api-domain.md)。

## 系统现状

迁移停用保护已实际部署：旧watchdog的XIYUNEWS_LEGACY_DISABLED=true，Cron为空，延迟回调跳过网络/KV/通知；新统一Worker不设置该旧服务专用变量。STATE仍同一个KV，不能因旧项目退役删除或重置。自然运行与收件证据分开记录。

| 位置 | 内容 |
| --- | --- |
| 东京服务器 fomobtc-tokyo（47.79.36.171） | systemd `fomobtc`：全部采集、去重、推送；新主API `api.xiyu.news` 与旧 `api.fomobtc.com` 过渡共存；独立证书由原certbot timer续期。TLS安装阶段见根交接。 |
| Cloudflare（账号 Drminutes） | 专用A api.xiyu.news→47.79.36.171 DNS-only；主站由统一Worker提供，其他DNS保持。统一Worker看门狗每5分钟/原STATE，业务变更后目标为新API，实际部署阶段见根交接；旧watchdog停用。 |
| 私有 `ohxiyu/xiyunews/realtime/` | 原历史及独立测试通过 PR195 进入 main；服务器新仓 SHA、新 Bot 管理员和三类自然回执已核验，Cloudflare 接管已完成，自然运行/后台读取与旧仓退役继续验收 |

Telegram 原群保留（话题开启、成员只读；2026-10-02 23:22:48 getChat 回读已更名为 `xiyu.news`，简介未改），机器人为管理员 `@xiyunewsbot`，不合并到日报频道：
- 📈 行情异动（话题 3）：币安 USDT 现货最近 3 分钟涨跌超过 2%/3%/5%（按 24h 成交额）并持续 3 秒；同币同向 1 小时一次，再涨跌 10% 立即再提醒，附 24 小时新高/新低。单条为 1 分钟 K 线图 + 中英双语 + 市值，同一秒到期多条合并为文字。
- 📢 交易所公告（话题 5）：Binance（官方流 + 中文官网）、OKX、Bybit、Bitget、Bithumb、Hyperliquid；Upbit、Bithumb 新交易对。优先官方中文，“标题 + 摘要 + 要点”。
- 💰 资金流向（话题 7）：币安地址簿（168 个地址）在 Ethereum、BNB Chain、Arbitrum、Base、TRON 上 ≥ 1000 万美元的单笔流入/流出。
- 运维提醒不进群：看门狗通过同一机器人私聊运营者。

## 配置与密钥位置
- 服务器 `/etc/fomobtc.env`（root 0600）：机器人 Token、群组 ID、三个话题 ID、币安公告只读 Key、SOURCE_COMMIT 等；历次修改前的备份为 `/etc/fomobtc.env.bak-*`（话题切换前的备份含运营者私聊 ID）。
- Cloudflare Worker 密钥：现役 `xiyunews` 的 TELEGRAM_BOT_TOKEN、ALERT_CHAT_ID；原停用watchdog仍保留旧秘密值但不执行。初始配置已完成，不重跑旧setup_watchdog.sh、复制密文或覆盖私聊目标；实际告警收件另验。
- 门槛与策略：`config/thresholds.yaml`；币安地址簿：`config/exchange_addresses.json`。
- SSH：运营者电脑 `/Users/minutesdr/.ssh/xiyunews_tokyo_config`（主机 xiyunews-tokyo，兼容 fomobtc-tokyo；专用私钥只在运营者电脑，严格指纹校验）。连接验证见 [记录](releases/ssh-access-20261002.md)。

## 部署与回退
- 后端：从 ohxiyu/xiyunews 根目录 `git archive <完整合并 SHA> realtime`，服务器 `tar -x --strip-components=1 -C /opt/fomobtc/releases/<SHA>`；后续独立 venv、停服务、SQLite 备份、切换和回退方式保持不变。SOURCE_COMMIT 必须是新仓完整 SHA，不是旧项目 SHA；详见 deployment.md。
- nginx：改 `scripts/deploy/nginx.conf` → 安装到 `/etc/nginx/sites-available/fomobtc` → `nginx -t` → reload；旧文件备份在 `/opt/fomobtc/backups/nginx-fomobtc-*.conf`。
- 看门狗：由根目录 `cloudflare-unified.yml` 随统一Worker发布；不再在独立watchdog目录执行部署，否则可能恢复第二调度者。组件源码仍独立测试，配置与验收见根单项目清单。
- 一次性配置脚本：`setup_telegram_topics.sh`（群组话题）、`setup_binance_announcements.sh`（币安只读 Key）、`setup_watchdog.sh`（看门狗凭据）；`setup_telegram.sh` 为早期私聊配置。
- 详细步骤见 [部署与回退](deployment.md)、[Telegram 运行与验收](telegram-runbook.md)。

## 已知限制（按设计）
- Hyperliquid 公告来自公开频道网页，约 15 秒，health 显示 degraded，因此 `/api/ready` 返回 503。
- Upbit 韩国站、Gate、MEXC 的公告接口在东京 403，只监测新交易对（Gate/MEXC 只记录不推送）；Bithumb 公告接口有 CDN 缓存，可能晚几分钟。
- 只推官方中英文，不做机器翻译；Bithumb 显示韩文原文，Hyperliquid 显示英文。
- 资金流向覆盖取决于地址簿；BSC/Base/Arbitrum 不扫原生币完整区块；Solana 暂不扫描。

最近证据：[新Bot切换](releases/deploy-20261002-xiyunews-bot.md)、[新仓部署](releases/deploy-20261002-xiyunews-repository.md)、[2.6.0](releases/2.6.0.md)、[全部发布记录](releases/README.md)。
