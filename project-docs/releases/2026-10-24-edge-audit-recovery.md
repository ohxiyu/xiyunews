# 10-24 网站未更新：统一部署依赖公告恢复

Issue: https://github.com/ohxiyu/xiyunews/issues/300；branch agent/edge-audit-recovery，当前会话唯一 owner。运营者报告"今天的日报还是没生成"，要求排查并解决。

PR: https://github.com/ohxiyu/xiyunews/pull/301

## 现象与根因

- 日报本身已生成：Daily 2026-10-24（run 40039703759）07:26–07:32 上海成功，gh-pages `api/latest.json` 为 2026-10-24、14 条，generated_at 2026-10-23T23:31:34Z。
- 网站没有更新：之后的 xiyunews Cloudflare 统一部署 222、223、225、226、228、229 全部 failure（224、227 为跳过）。正式域停在上一期。
- 失败位置：deploy job 的 `npm run audit`（`npm audit --audit-level=low`），在渲染和上传之前退出。报告 5 个漏洞（3 high、2 moderate）：
  - undici 7.0.0–7.30.0：GHSA-4qv8-2p9j-2685、GHSA-f72v-6w45-q472、GHSA-xjj6-f33q-929c。package.json overrides 把它固定在 7.29.1。
  - zod < 4.6.6：GHSA-mrhx-c7xc-m3w5。@cloudflare/vitest-pool-workers 0.22.0 精确依赖 4.4.3。
- 与 10-22 的 PR294 同一类问题：开发/构建依赖出现新公告，发布门槛阻断部署。日报 AI、采集和发送都没有出错。

## 修复

- `ops/daily-dispatcher/package.json` overrides：undici 7.29.1 → 7.30.1，新增 zod 4.6.7（同一大版本内的最小修复版）。
- 用 CI 同版本 npm 11.11.1 重新生成 lockfile，差异只有这两个包的 version/resolved/integrity（避免 npm 10 删除 libc 字段造成无关改动）。
- 不改 Worker 代码、Cron、DNS、Access、密钥、AI、数据和状态分支；没有重跑日报或重置发送状态。

## 验证

- `npm audit --audit-level=low`：found 0 vulnerabilities（npm 11.11.1）。
- `npm ci`、`types:check`、`tsc --noEmit` 通过；Worker 测试 8 个文件 135 项全部通过。
- `wrangler deploy --dry-run`（wrangler.jsonc 与 wrangler.unified.jsonc，后者用占位资产目录）通过。
- `uv run pytest` 1118 passed / 4 skipped；治理检查通过。

## 上线

- PR301 于 2026-10-24 14:29Z 合并为 3b5ee933e9d40e9a3fdbf0f0fe34f1759b15793d，合并前全部适用检查通过（governance、realtime-paths、edge-build、web）。
- 会话令牌无权调用 workflow_dispatch（403），重跑旧失败运行仍会使用旧 lockfile，因此请运营者手动运行。
- 运营者手动运行的统一部署 230（40103860043，workflow_dispatch）success：`npm run audit` 通过，渲染 artifact c70b818a93114abe5b550b36fe9a2777fdafbfdb（含 2026-10-24），上传 1216 个变更资产，14:49:16Z 部署到 xiyu.news 自定义域，Worker 版本 f8099963-2bb3-42e5-bb44-2cda6435d1ca，三条 Cron 不变。群组快照步骤输出 "Prepared published group snapshot for 2026-10-24; no AI, no sends"。
- 随后由采集触发的统一部署 231（40110483140）也 success（16:17Z）。

Source commit: 3b5ee933e9d40e9a3fdbf0f0fe34f1759b15793d。
Artifact commit: gh-pages c70b818（含 2026-10-24，14 条）。
Worker version: f8099963-2bb3-42e5-bb44-2cda6435d1ca（部署 230）。
Deployment: complete。
Verification: 部署日志确认 10-24 产物已上传到正式域；本环境代理无法直接访问 xiyu.news，页面显示以运营者浏览为准。
Rollback: 恢复 overrides 原值即可，但会重新被审计拦截；不涉及状态或数据。
