# 2026-09-25 2.6.0 行情单一规则部署

部署状态：deployed
源码提交：b226b625cf3875b6693e0768d75d88d50b33c08d
运行版本：后端 2.6.0 systemd fomobtc（PID 177730，2026-09-25 14:57:49 UTC 启动），/opt/fomobtc/current 指向该 SHA，release 自带 venv（requirements.lock 按哈希安装）；nginx 与看门狗 Worker 55671d87-29c2-4225-8bdf-176cb4712ed3 未改动。
验收结果：见下方“线上验收”。
回退信息：备份 /opt/fomobtc/backups/20260925T145749Z-before-b226b62（SQLite integrity ok，含部署前 /etc/fomobtc.env 与 previous_release）；回退即把 /opt/fomobtc/current 指回 /opt/fomobtc/releases/8f1751ef7f7ce403007965ab136d039657420461 并重启。2.5.1 代码会忽略新表 market_alert_state；回退时若有新格式的待发行情通知，旧代码读不到旧字段，会标记为结果不明而不重发。
授权记录：用户 2026-09-25“我要的是，行情有异动的时候，及时关注，请你给我优化简化逻辑”，确认方案后“改完直接部署”；未输出任何密钥。

## 部署过程（UTC）
- 14:56:40 PR #51 CI 全部通过（repository、test 3.11/3.12、watchdog）后 squash 合并为 b226b62。
- git archive 该 SHA 上传；服务器解压到新 release 目录，关键文件（app/market/signals/store、thresholds.yaml、requirements.lock）sha256 与本地一致；新建 venv 按哈希安装依赖、compileall、导入检查（VERSION 2.6.0）。
- 14:57:49 停服务 → SQLite 在线备份（integrity ok）→ 切换 current 与 SOURCE_COMMIT → 启动（同一秒内完成），8 秒后确认 active。服务器保留 2.5.0、2.5.1、2.6.0 三个 release。

## 部署前发现
- 2.5.1 线上 spot_stream_2（39 个交易对）自约 18:09（北京时间）起 stale：18:09 的成交额范围刷新让该分片因新币加入重启，分片内有已移出范围的币，建窗口时 KeyError，任务直接退出且不再重连，状态停在旧值。约 4.8 小时这 39 个币没有行情监控。2.6.0 已修复此问题（本次部署即恢复）。
- 看门狗按设计工作：连续 57 次检查失败（约 4.75 小时），已私聊提醒运营者（最后一次提醒 22:20:33 北京时间，Telegram 接口已受理）。

## 线上验收
- health：version 2.6.0、source_commit b226b62、telegram_enabled true；market_notice_policy 为 policy_version 3（180 秒、3 秒确认、2/3/5%、3600 秒、10%）。
- 迁移：meta alert_policy_v3 已写入；market_alert_state 带入最近 1 小时已提醒的 9 个币种方向（价格为空，只能等冷却结束）；部署时没有待发行情通知，expired 0 条。日志无错误。
- 15:01 UTC 三个 spot 分片（150 + 150 + 28 = 328 个交易对）全部 live；除 Hyperliquid 按设计 degraded 外其余来源 live/polling。
- 看门狗 15:00 UTC 检查无异常，KV 状态重置为 failing 0 / alerted false，即“✅ 已恢复正常”私聊已被 Telegram 接口受理（发送失败时状态会保留 alerted 以便重试）。首次完成真实故障的提醒与恢复闭环；手机收件由运营者确认。
- 首条自然行情推送：15:10 UTC QUICK 3 分钟内下跌 5.90%（小盘门槛 5%，非 24 小时新低），Telegram 接口受理，message_id 212。越线到确认 4.36 秒（该币成交稀疏，3 秒后的第一笔成交才完成确认），入库后按 hold_seconds 等 1 秒，请求（取 1 分钟 K 线、绘图、sendPhoto）1.41 秒，越线到送达共 6.79 秒。群内图片与文案由运营者查看确认。
