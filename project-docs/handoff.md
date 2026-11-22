# 当前交接

xiyu.news 网站只展示最新一期中文日报，保留 #306 的正文、排行和背景块，并提供单期 RSS。Cloudflare 从单条公开刊期记录提供内容，当前部署首期同时提供静态回退。日报与 X 过渡期继续使用现有快照与发送校验。后台预采每 30 分钟检查一次。

<!-- execution-pointer -->
```json
{
  "goal": "轻量版最新一期",
  "issue": "https://github.com/ohxiyu/xiyunews/issues/398",
  "owner": "当前 Codex 聊天",
  "branch": "agent/latest-edition-only",
  "base": "ca936d144d478b8e8c2ff264fadaa738a7843870",
  "status": "切换正式域单期阅读和 Cloudflare 单期记录",
  "next": "验证实时读取与旧地址，继续切换写入及 X 证明，再清理旧正文",
  "blockers": []
}
```

[发布与监控](product-release.md) · [X 分发和质量门](x-distribution.md)
