# 阶段 2：私有仓库调度迁移

Issue: https://github.com/ohxiyu/xiyunews/issues/170

基线为 PR169 合并提交 e12179905981ed2ff5c31811db41f4c5f7b259d1。只修改独立调度器及其测试/现行手册，不改页面结构、采集源、提醒规则、锁、发送预算、密钥或付费计划。

## 改动与验收

仓库改为 ohxiyu/xiyunews；私有 gh-pages 从 Contents API 鉴权读取，认证请求不跟随跳转，公共页面探测不附带 PAT。响应保留 2 MB 上限。/health 返回实际 repository 和 public_site_url；/ready 检查 Actions 写权限及 Contents 读权限，不创建工作流。

来源目录的只读配置也改为既有 Access 保护的同源 /api/admin/source-config，由服务器读取私有仓库，不把令牌暴露到浏览器；未更改任何来源配置。旧 OAuth 中继仍仅供 public_repo，不扩大为全私有仓库 scope；当前 Quick Post 使用 Access，不依赖它。

本地验证：npm ci、npm run check（类型生成一致、tsc、64 项 Vitest、deploy dry-run）、完整 929 项 pytest 和治理通过；新增后台读取用 Node 测试验证。最终结果以 PR 检查为准，不能把本地检查称为生产验收。已有 npm 开发依赖审计报告 7 项（2 moderate、5 high），本阶段未用 force 自动升级或声称全量安全扫描通过。

## 部署与域名过渡

运营者已授权本轮部署。新域 NS 传播未完成时，配置的正式 PUBLIC_SITE_URL 仍为 https://xiyu.news，但部署临时显式覆盖公共检查为 https://bmt.news，避免健康探测误判；不能把该临时地址描述为新域已上线。保留所有现有 Secrets/仪表盘变量。

```bash
cd ops/daily-dispatcher
npm ci
npm run check
npx wrangler deploy --keep-vars --var GITHUB_REPOSITORY:ohxiyu/xiyunews --var PUBLIC_SITE_URL:https://bmt.news
```

新域 Pages/HTTPS 就绪后执行正常 `npx wrangler deploy --keep-vars --var GITHUB_REPOSITORY:ohxiyu/xiyunews --var PUBLIC_SITE_URL:https://xiyu.news`，并核验 `/health` 两字段和 `/ready` 的两种权限。下一次 Feed Collection 的 event 应为 workflow_dispatch；未出现自然运行前不称定时验收完成。如果现有 PAT 缺少 Contents: Read，只调整该仓库既有令牌权限，不扩大到所有私有仓库、不输出密钥。

Source commit: 待本阶段合并 SHA。
Worker version: 本阶段尚未部署。
Deployment: 待 CI 通过及合并后部署。
Verification: 新域与自然触发尚未验证。
Rollback: 仅按运营者授权恢复上一 Worker 版本，保留 RecoveryGate 和所有迁移数据；本轮不执行回滚。
