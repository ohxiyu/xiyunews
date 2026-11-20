# Cloudflare 调度器触发采集

- Issue: [#158](https://github.com/ohxiyu/bmtnews-standalone/issues/158)
- Branch: `agent/dispatcher-collection`
- Scope: `ops/daily-dispatcher/`（新增 `src/collection.ts`，五分钟回调改为全天）、`feed-collection.yml` 注释、调度手册。采集工作流本身不变。Worker 版本 1.0.0 → 1.1.0。

## 问题

`feed-collection.yml` 依赖 GitHub 定时，最近多次晚 1–3.5 小时或漏跑（9/28 北京时间 20:30、00:30 两轮未跑，下一次 03:46 才开始）。

## 变更

| 项 | 内容 |
| --- | --- |
| 回调 | `*/5 0-15 * * *` → `*/5 * * * *`；广场（09:00–23:30）与日报检查（08:00–23:00）时间窗不变；旧 Cron 仍被接受以兼容配置传播 |
| 采集派发 | 每个整十分钟：`main` 上最近一次 Feed Collection 开始超过 4 小时、且无排队或运行中的采集时，派发 `workflow_dispatch` |
| 避让 | 北京时间 07:00–07:45 不派发（日报自行采集，共用并发组） |
| 可见性 | Workers Logs `collection_dispatch`；`/health` 增加 `collection_workflow`、`collection_max_age_hours` |
| 成本 | 每 10 分钟一次 GitHub API 列表请求（约 144 次/天）；采集频率回到设计的约 4 小时一次，新增条目才会进入模型分析 |

## 验证

- `npm run check`（类型、typecheck、61 个测试、`wrangler deploy --dry-run`）通过；新增 `tests/collection.spec.ts`：超时派发、未超时不派发、运行中不叠加、从未运行即派发、非整十分钟与日报窗口静默、API 失败报错、夜间回调只做采集检查。
- `uv run pytest` 与治理检查通过。

## 部署（需维护者执行）

```bash
cd ops/daily-dispatcher
npm ci
npx wrangler deploy --keep-vars
```

部署后：`/health` 应返回 `schedule_crons_utc` 含 `*/5 * * * *` 与 `collection_max_age_hours: 4`；Cloudflare Workers Logs 出现 `collection_dispatch`；GitHub Actions 中出现 `workflow_dispatch` 触发的 Feed Collection。

## 尚未验证

- 生产 Worker 部署与首次自动派发。
