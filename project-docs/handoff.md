# 当前交接

xiyu.news 只展示最新一期中文日报。首页、刊期页、最新 API 与 RSS 由 Cloudflare 静态资产直接交付。后台每 30 分钟采集和去重，06:30 北京时间预评分，07:26 出刊。候选、评分及简版缓存在私有 SQLite。X 在刊期通过线上核验后规划，后续按队列到期时间唤醒。

<!-- execution-pointer -->
```json
{
  "goal": "正文后直接显示背景并恢复排行序号",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/410",
  "owner": "当前 Codex 聊天",
  "branch": "agent/visible-story-background",
  "base": "0a0392915b08c2d2a3dc1a7b79a263069b0a1f3c",
  "status": "背景淡色常显，参考资料继续折叠，卡片与本期目录共用排行序号",
  "next": "核对首页与当期页的背景和序号，观察首轮定时出刊与 X 到期分发",
  "blockers": []
}
```

[发布与监控](product-release.md) · [X 分发和质量门](x-distribution.md)
