# 托管执行与出版状态

xiyu.news 的采集、出刊、网站发布和 X 分发在 GitHub 托管执行。Cloudflare Durable Object 保存现用 SQLite 快照，通过短时 OIDC 身份和单写者租约提供访问。公开日报归档仍由出版工作流维护。东京实时应用与自托管 Runner 已退出该产品的发布路径，历史数据库、发送回执和归档继续保留。

参见 [发布与监控](product-release.md) 及 [历史执行器记录](https://github.com/ohxiyu/xiyunews/blob/2ae5030c994eb23911c8619a7f6930fdf98e74ba/project-docs/self-hosted-runner.md)。
