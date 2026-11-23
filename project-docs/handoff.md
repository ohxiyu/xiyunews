# 当前交接

xiyu.news 只展示最新一期中文日报。首页、刊期页、最新 API 与 RSS 由 Cloudflare 静态资产直接交付。后台每 30 分钟采集和去重，06:30 北京时间预评分，07:26 出刊。候选、评分及简版缓存在私有 SQLite。X 在刊期通过线上核验后规划，后续按队列到期时间唤醒。

<!-- execution-pointer -->
```json
{
  "goal": "压缩日报首屏并简化目录与来源",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/412",
  "owner": "当前 Codex 聊天",
  "branch": "agent/compact-reader-navigation",
  "base": "ab391e45a6b3e0b5ff0d7cbc52b67bed736623ca",
  "status": "单行页头可回到目录，桌面指示当前资讯，来源行隐藏采集类型",
  "next": "验证首页和当期页的目录跳转、触控区与正文复制",
  "blockers": []
}
```

[发布与监控](product-release.md) · [X 分发和质量门](x-distribution.md)
