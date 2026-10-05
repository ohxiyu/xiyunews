# 2026-10-05 实时 API 域名迁移

任务：[Issue216](https://github.com/ohxiyu/xiyunews/issues/216)，唯一负责人为当前 Codex 会话，分支 agent/realtime-api-domain。用户明确授权 DNS、证书、nginx 和统一 Worker 部署，不包括旧域删除、密钥/队列/数据库修改或服务重启。

## 原因与范围

主站与统一 Worker 已迁到 xiyu.news，实时看门狗仍写死 api.fomobtc.com，东京 nginx 和证书仍对应旧域。旧 api 的 DNS 缺失触发无响应提醒，但实时采集进程持续在线。先恢复旧域只是应急止血，并非完整迁移。新 api.xiyu.news 原无专用记录，命中 *.xiyu.news 到185.53.179.128，实测health522。

本次新增专用 DNS-only A api.xiyu.news→47.79.36.171（自动TTL回读300），主站/www/通配符记录不变。新域使用独立证书和同等 read-only nginx 限制，旧 API 原配置保留。看门狗仅换健康URL及提醒链接，不改变5分钟Cron、两次失败确认、2小时提醒、STATE、Bot或目的地。

## 验证与阶段

- uv frozen dev成功；根 pytest1044 passed（1条现有依赖弃用warning）。
- Node watchdog7 passed，新增 mocked 新域请求、503与网络失败、告警新链接；无真实AI或渠道调用。
- Worker102 passed、typecheck、npm audit0通过；部署模板测试核对新旧域TLS、ACME、GET/OPTIONS、限速、no-store和未知路径404。
- DNS保存回读及Google/Cloudflare DoH均为47.79.36.171；HTTP ACME bootstrap nginx-t通过。独立新证书签发成功，到期2027-01-03，原certbot timer为enabled/active；未注册新服务或修改密钥。
- 东京迁移前MainPID235825/NRestarts0，应用源码d6a9d3f29ef93c138842342c973b3049fb7bc252。保留独立服务器SHA，不将新WorkerSHA当应用重部署。

Source commit: 4e3862117671db962798fc305622a476f07e5ec7（业务[PR217](https://github.com/ohxiyu/xiyunews/pull/217)，15:01:31Z合并）；发送应用仍d6a9d3f29ef93c138842342c973b3049fb7bc252，不混淆两种SHA。
Worker version: fb50c31c-7ca6-4339-b1f6-9929bd12ae74；之前496f3131-144e-4a25-ae59-44f5b47b6b34。静态产物3670b9beeba36078fe0b47343070e6f073da76c0不变。
Deployment: 已完成，[现有统一部署37329563017](https://github.com/ohxiyu/xiyunews/actions/runs/37329563017)成功，15:04:23Z回读Worker ID、原三组Cron、--keep-vars。没有恢复旧独立watchdog、手改gh-pages或任何缓存/队列分支。
Verification: 2026-10-05T15:05:32Z新版本自然*/5 Cron outcome=ok、exceptions=[]、watchdog:ok；collection not_due，X/Square idle。随后STATE只读仍failing0/alertedfalse/lastAlert0，未重置；实际Telegram手机收件尚未独立验证。既有Hyperliquid degraded/ready503不因域名迁移消失。
Rollback: 东京原nginx完整备份/opt/fomobtc/backups/api-domain-20261005-GtQ56kQj/nginx-fomobtc.conf；旧API保留。需要明确回退授权后，恢复原代理配置、nginx-t/reload，并通过reviewed PR把监控目标改回旧API及原统一Worker部署流程；不回滚发送应用、不动env/SQLite/STATE。

## 生产验收补录（Issue218，仅文档）

业务[CI37329100332](https://github.com/ohxiyu/xiyunews/actions/runs/37329100332)全绿：test、edge-build、governance、realtime两版本（各61 passed、ruff/mypy/契约/Node）及Pages通过；CodeQL analyze由于原私有套餐授权被跳过，不称为已完成扫描。

原nginx备份SHA256为2da5dbc26a72eb35e5363999db81e6dee28d9a345300c21269d3e502cef64c73；安装的reviewed新配置SHA256为f8a93aaa4bc8341ff8110cf762fa2af3ea4f6b434790200619b9eb9697942ef3，与业务PR文件逐字节一致。临时ACME vhost已移动到上述备份目录，nginx-t成功后仅reload nginx。发送应用MainPID235825/NRestarts0未变；新旧域都返回同一应用SHA。

公网DNS两家DoH一致；东京按正常域名且严格TLS验证：新旧health200、no-store、三spot分片live、ingestion_queue0，HTTP308保留路径，未知路径404，POST health403，ready503保留既有来源限制。运营者电脑另以新域SNI/Host固定源IP严格校验证书成功（不使用-k，避免本机Shadowrocket假IP缓存干扰）。这些验收不等于每条历史失败事件已修复或手机通知已收件。

迁移期间STATE首次CLI只读受本机已有Cloudflare凭据环境影响返回401；仅对只读CLI进程移除覆盖变量、使用现有OAuth后回读成功，未读取/修改任何凭据值。全部回读都是健康零故障状态；没有通过清KV伪造恢复。

本次没有发送测试消息、制造故障、调用真实AI、触发出刊/重刊/编辑重建或人工渠道工作流。保留旧域/旧证书过渡，删除属于新的具体授权；没有新增付费套餐。文档PR自身不需要部署，合并文档不能误触发第二次生产发布。
