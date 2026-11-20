# Cloudflare 部署

公开站点与东京实时服务的看门狗部署在现有 `xiyunews` Worker。根目录 `wrangler.json` 保留原主域、`STATE` KV 和 `RecoveryGate` Durable Object。旧快讯书签通过只读方式读取原 DO。五分钟 Cron 调用既有 [实时看门狗](../realtime/scripts/deploy/watchdog/worker.js)。

合并到 `main` 后，现有 GitHub Actions 使用固定的已发布快照构建站点。发布前从 GitHub 执行器验证 Eqn 新闻、频道、详情和浏览器跨域权限，再使用已有凭据更新 Worker。部署后检查生产提交与新旧两种页面。站点的 `/health` 与 `/ready` 报告 Worker 版本，Eqn 和东京实时服务有各自的可用性检查。

历史交接见 [2026-10-03 验证记录](releases/2026-10-03-cloudflare-production-verification.md)。
