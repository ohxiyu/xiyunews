# 当前交接

<!-- execution-pointer -->
```json
{
  "goal": "将公开站点从每日出刊切换为 Eqn API 驱动的加密快讯",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/380",
  "owner": "当前 Codex 聊天",
  "branch": "agent/eqn-news-redesign",
  "base": "ce9006ffdac8ff22c147719a9279ff9333c6d213",
  "status": "站点重构、本地 Worker 打包、99 期归档及 Chromium 模拟接口验证完成；生产待验证",
  "next": "核对最终日报快照、验证 Eqn API 与浏览器跨域访问、观察现有 Cloudflare 工作流部署结果",
  "blockers": ["当前执行环境的代理拒绝访问 api.eqn.news，真实接口联调由 GitHub CI 执行"]
}
```

- 活跃内容使用 Eqn REST，订阅使用 Eqn RSS。历史日报从固定的 `gh-pages` 提交构建，保留条目锚点和冻结的 `/api/latest.json`。切换前对照 `gh-pages` 的最终出版提交；若有更新，更新构建和 CI 的归档引用并重新验证。
- 日报采编、缓存、模型、发布与分发代码移除。保留分支历史、已发布内容及现有 Durable Object 数据。切换时确认先前启动的日报工作流已经结束。
- 东京实时告警和边缘看门狗属于现有实时服务。现有 Worker、域名、KV、DO 和五分钟看门狗 Cron 见 [Cloudflare 部署](cloudflare-single-project.md)。
- 此次重构之前的生产迁移记录见 [原交接](https://github.com/ohxiyu/xiyunews/blob/ce9006ffdac8ff22c147719a9279ff9333c6d213/project-docs/handoff.md)。
