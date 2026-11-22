# 当前交接

xiyu.news 只展示最新一期中文日报。首页、刊期页、最新 API 与 RSS 由 Cloudflare 静态资产直接交付。后台每 30 分钟采集和去重，06:30 北京时间预评分，07:26 出刊。候选、评分及简版缓存在私有 SQLite。X 在刊期通过线上核验后规划，后续按队列到期时间唤醒。

<!-- execution-pointer -->
```json
{
  "goal": "降低日报与 X 的运行用量",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/404",
  "owner": "当前 Codex 聊天",
  "branch": "agent/lean-publication-usage",
  "base": "afec92999b40c8255d279b653c66f8fe36d55bad",
  "status": "切换静态直出、私有采集暂存及 X 到期唤醒",
  "next": "观察首轮 06:30 预评分、07:26 出刊和自然 X 到期分发",
  "blockers": []
}
```

[发布与监控](product-release.md) · [X 分发和质量门](x-distribution.md)
