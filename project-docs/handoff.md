# 当前交接

xiyu.news 只展示最新一期中文日报。首页、刊期页、最新 API 与 RSS 由 Cloudflare 静态资产直接交付。后台每 30 分钟采集和去重，06:30 北京时间预评分，07:26 出刊。候选、评分及简版缓存在私有 SQLite。X 在刊期通过线上核验后规划，后续按队列到期时间唤醒。

<!-- execution-pointer -->
```json
{
  "goal": "让日报正文优先并支持复制正文",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/408",
  "owner": "当前 Codex 聊天",
  "branch": "agent/reader-content-hierarchy",
  "base": "e509a553e15fd1b1e0234f7b0f2b1fd214bb70e7",
  "status": "正文优先，移除本期脉络，保留折叠的背景和参考资料",
  "next": "核对现行刊期的剪贴板、阅读顺序和线上版式，观察首轮定时出刊与 X 到期分发",
  "blockers": []
}
```

[发布与监控](product-release.md) · [X 分发和质量门](x-distribution.md)
