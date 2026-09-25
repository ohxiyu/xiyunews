# 2026-09-25 2.3.0–2.5.0 部署、Telegram 群组话题与 cex.top 停用

部署状态：deployed
源码提交：1739fe3e97f077ed5d4e2dbe4ecb3cebbd55e7c6
运行版本：后端 2.5.0 systemd fomobtc（话题切换后 PID 169976），/opt/fomobtc/current 指向该 SHA，release 自带 venv（含 Pillow）；前端最后发布 Worker 48a8a997-0cc5-4c5d-bb44-079b95f15e95，之后按用户要求下线。
验收结果：2.3.0（c36d671，2026-09-24 16:03 UTC）双语公告上线无推送积压；2.4.0（47e47ec，2026-09-25 02:51 UTC）首条行情图片推送 SAGA 10:58:08 发现、10:58:12 API 确认；2.5.0（1739fe3，03:31 UTC）flow_ethereum/bsc/arbitrum/base/tron 全部 polling 且落后 0 块。03:59 UTC 切换到超级群组 -1004364162227（fomobtc，已开启话题），话题 📈 行情异动=3、📢 交易所公告=5、💰 资金流向=7，各发送测试消息 API 成功；切换后通知继续 sent。
回退信息：备份 /opt/fomobtc/backups/20260924T160333Z-before-c36d671、20260925T025155Z-before-47e47ec、20260925T033135Z-before-1739fe3（SQLite integrity ok）；话题切换前配置 /etc/fomobtc.env.bak-20260925T035911Z，恢复该文件并重启即回到私聊推送；各旧 release 与其 venv 保留。
授权记录：用户 2026-09-24/25“合并部署”“直接帮我整合进项目 fomobtc”“方案a”“已经配置好了bot权限，帮我配置好telegram”“继续配置，然后停用 cex.top”；未输出任何密钥。

## cex.top 停用
- 2026-09-25 约 04:00 UTC 用 `wrangler triggers deploy` 将主 Worker `cex-top` 的 Cron 改为空（Arbitrum/alt Worker 只由主 Worker 调度）；Cloudflare 说明 Cron 变更最多 15 分钟全网生效，04:03 仍观测到一次扫描。
- GitHub 仓库 ohxiyu/cex.top 已归档（只读）。
- 永久删除（Worker cex-top / cex-top-arbitrum / cex-top-alt、D1 `cex-top`、GitHub 仓库）按安全规则由用户执行。
