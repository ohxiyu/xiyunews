# xiyu.news

[加密快讯](https://xiyu.news/) · [往期日报](https://xiyu.news/history/) · [方程式新闻 API](https://eqn.news/api-docs)

xiyu.news 由 [xiyu / @ohxiyu](https://x.com/ohxiyu) 维护。网站直接使用 Eqn REST 读取快讯、频道、搜索结果及 AI 解读，RSS 订阅转向 Eqn。静态归档保留迁移前已发布的日报和原条目锚点。`/api/latest.json` 是最后一期日报的兼容快照。

## 本地开发

使用 Node.js 24。在仓库根目录运行。

```bash
npm ci
git fetch --depth=1 origin 9cf037ee185b007e37181daf181649b4c834d275
git worktree add --detach .edition-snapshot 9cf037ee185b007e37181daf181649b4c834d275
npm run build
npm test
npm run check
npm run preview
```

网页代码位于 `site/`，Cloudflare 入口位于 `edge/`。浏览器连接公开的 Eqn API，无需 API 密钥。可用 `node scripts/check-upstream.mjs` 验证接口和 CORS。部署使用 [现有 Cloudflare Worker](project-docs/cloudflare-single-project.md)。独立实时告警服务见 [realtime](realtime/README.md)。

## 权利与来源

软件采用 [MIT 许可证](LICENSE)。新闻、归档和素材详情见 [内容与数据权利](CONTENT-LICENSE.md) 及 [第三方声明](THIRD_PARTY_NOTICES.md)。
