# 当前交接

xiyu.news 只展示最新一期中文日报。首页、刊期页、最新 API 与 RSS 由 Cloudflare 静态资产直接交付。后台每 30 分钟采集和去重，07:00 北京时间截稿，07:26 出刊任务内统一评分。候选、评分及简版缓存在私有 SQLite。X 在刊期通过线上核验后规划，后续按队列到期时间唤醒。

<!-- execution-pointer -->
```json
{
  "goal": "日报 V3.2 单轮评分与精评预算",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/415",
  "owner": "当前 Codex 聊天",
  "branch": "agent/single-pass-daily-scoring",
  "base": "608a0d0b3df0bedfe23097a76c65c8209a69b35c",
  "status": "合并评分，常态精评 60 条，单期最多 80 条",
  "next": "回放三期并检查漏选、事实、X 质量门和实际耗时",
  "blockers": []
}
```

[发布与监控](product-release.md) · [X 分发和质量门](x-distribution.md)
