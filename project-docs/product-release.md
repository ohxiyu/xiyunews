# xiyu.news 发布与监控

生产范围为中文网站日报和 X 改写分发。GitHub Actions 执行采集、出刊和分发，Cloudflare 托管网站与私有出版 SQLite。运维入口查询每日刊期、正式版本与运行环境，也可请求已有 Cloudflare 工作流发布审核后的 `main`。

```sh
python3 ops/release/xiyunewsctl.py status
python3 ops/release/xiyunewsctl.py deploy
```

纯代码发布从现有公开归档渲染。X 只处理经正式域核验的当天刊期，保留内容质量门、字数上限和持久回执，未知发送结果不自动重试。历史实时模块、发布脚本与文档见 [退役前提交](https://github.com/ohxiyu/xiyunews/tree/2ae5030c994eb23911c8619a7f6930fdf98e74ba/realtime)。
