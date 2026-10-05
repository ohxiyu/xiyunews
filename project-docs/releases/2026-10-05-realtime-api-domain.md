# 2026-10-05 实时 API 域名迁移

任务：[Issue216](https://github.com/ohxiyu/xiyunews/issues/216)，唯一负责人为当前 Codex 会话，分支 agent/realtime-api-domain。用户明确授权 DNS、证书、nginx 和统一 Worker 部署，不包括旧域删除、密钥/队列/数据库修改或服务重启。

## 原因与范围

主站与统一 Worker 已迁到 xiyu.news，实时看门狗仍写死 api.fomobtc.com，东京 nginx 和证书仍对应旧域。旧 api 的 DNS 缺失触发无响应提醒，但实时采集进程持续在线。先恢复旧域只是应急止血，并非完整迁移。新 api.xiyu.news 原无专用记录，命中 *.xiyu.news 到185.53.179.128，实测health522。

本次新增专用 DNS-only A api.xiyu.news→47.79.36.171（自动TTL回读300），主站/www/通配符记录不变。新域使用独立证书和同等 read-only nginx 限制，旧 API 原配置保留。看门狗仅换健康URL及提醒链接，不改变5分钟Cron、两次失败确认、2小时提醒、STATE、Bot或目的地。

## 验证与阶段

- uv frozen dev成功；根 pytest1044 passed（1条现有依赖弃用warning）。
- Node watchdog7 passed，新增 mocked 新域请求、503与网络失败、告警新链接；无真实AI或渠道调用。
- Worker102 passed、typecheck、npm audit0通过；部署模板测试核对新旧域TLS、ACME、GET/OPTIONS、限速、no-store和未知路径404。
- DNS保存回读及Google/Cloudflare DoH均为47.79.36.171；HTTP ACME bootstrap 已安装，nginx-t通过；证书/TLS、PR合并、Worker部署和自然Cron仍待后续验收。
- 东京迁移前MainPID235825/NRestarts0，应用源码d6a9d3f29ef93c138842342c973b3049fb7bc252。保留独立服务器SHA，不将新WorkerSHA当应用重部署。

Source commit: pending：基于744791f5f6eab5dddc5a6f0ccd62aaa682018fe3，业务PR合并后记录实际SHA。
Worker version: not changed，目前496f3131-144e-4a25-ae59-44f5b47b6b34；新URL尚未部署。
Deployment: pending；仅按现有cloudflare-unified.yml部署，禁止恢复旧独立watchdog。
Verification: 2026-10-05，DNS确认；TLS、自然Cron与实际Telegram收件尚未验证。既有Hyperliquid degraded/ready503不因域名迁移消失。
Rollback: 东京原nginx完整备份/opt/fomobtc/backups/api-domain-20261005-GtQ56kQj/nginx-fomobtc.conf；旧API保留。需要明确回退授权后，恢复原代理配置、nginx-t/reload，并通过reviewed PR把监控目标改回旧API及原统一Worker部署流程；不回滚发送应用、不动env/SQLite/STATE。

服务器和自然Cron最终证据在生产完成后通过独立文档PR追加，不把本记录的pending称为上线完成。
