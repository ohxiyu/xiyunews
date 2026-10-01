# 单机运行与看门狗

用户 2026-09-25 选择“方案a，看门狗也加上”：所有服务集中到东京服务器，Cloudflare 只做 DNS；增加服务器外的健康看门狗。

## 变化
- fomobtc.com / www.fomobtc.com 改由服务器 nginx 302 到群组邀请链接（scripts/deploy/nginx.conf 新增 80/443 两个 server）；删除 Cloudflare 跳转 Worker 及 scripts/deploy/redirect。
- 新增 scripts/deploy/watchdog（Cloudflare Worker fomobtc-watchdog，cron */5，KV STATE）：连续两次异常私聊提醒，2 小时重复提醒，恢复通知；node 测试并入 CI。
- 新增 scripts/setup_watchdog.sh：从服务器配置读取机器人 Token 与切换话题前备份中的私聊 ID，写入 Cloudflare 密钥并发送测试私聊，不输出内容。

## 部署与验证
- 看门狗：KV 469346950dfc4f36b8d9bf9997d960fa，Worker 版本 55671d87-29c2-4225-8bdf-176cb4712ed3，schedule */5 * * * *；用户运行 setup_watchdog.sh 后 secret list 含 TELEGRAM_BOT_TOKEN、ALERT_CHAT_ID。用线上 health 评估无问题项。
- 用户删除 Worker fomobtc，并在 Cloudflare 添加 A @ / A www → 47.79.36.171（DNS only）；1.1.1.1 与权威 NS 均解析到该 IP。
- nginx 先上线 80 端口跳转（备份 /opt/fomobtc/backups/nginx-fomobtc-20260925T044721Z.conf），certbot webroot 签发 fomobtc.com + www（到期 2026-12-24，同一续期定时器），再安装完整模板（备份 nginx-fomobtc-20260925T045248Z.conf），线上文件与仓库模板 MD5 一致。
- 验证：https/http 的 fomobtc.com、www 及任意路径均 302 → https://t.me/+mdTufn9GK1UyODk0；api.fomobtc.com/api/health 200。
- 回退：恢复上述 nginx 备份并 reload；DNS 记录可在 Cloudflare 改回。
