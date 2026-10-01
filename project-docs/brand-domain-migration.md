# 稀有News 品牌与域名迁移

## 发布顺序

先确认 xiyu.news DNS 委派与 Pages 自定义域可用，再发布品牌与 Worker 301。网页站名为 xiyu.news，中文品牌为稀有News。旧域名仍需留在同一 Pages 项目并保留 TLS；不要先解绑旧域，不直接写 gh-pages。

Cloudflare Free zone 的 NS 为 ignat.ns.cloudflare.com 和 shaz.ns.cloudflare.com。保存后核对注册商回读、权威 DNS 和 Cloudflare active；创建 zone 不等于上线。Pages 内部项目名可保留 bmtnews，关联仓库须核对为 ohxiyu/xiyunews，生产分支仍为 gh-pages。

## 301 二选一

默认使用 docs/_worker.js，精确匹配 bmt.news、www.bmt.news，在认证、API 和缓存之前返回 301，目标为 https://xiyu.news 加原 pathname 与 search。旧文章、feed、API、OpenAPI 和 llms 路径不改。新域不可用时不能发布强制跳转。

备选：Cloudflare Single Redirect Rule，表达式 `(http.host eq "bmt.news") or (http.host eq "www.bmt.news")`，动态目标 `concat("https://xiyu.news", http.request.uri.path)`，状态 301，勾选保留查询字符串。二选一承担入口跳转，不设置指回旧域的规则；保持旧域代理和 TLS。

## 后台与 Quick Post

既有 Access 应用增加新主机的等效路径 /s、/s/*、/admin、/admin/*、/api/admin、/api/admin/*，保持允许邮箱、验证方式、策略与 AUD，不扩大用户或设置公开绕过。Pages 的 ADMIN_ACCESS_ISSUER、ADMIN_ACCESS_AUD、ADMIN_ALLOWED_EMAIL、ADMIN_GITHUB_TOKEN 保持已有安全配置；只核对权限存在，不抄写值或擅自重发密钥。

匿名 /s/ 应进入 Access 验证，公开 /api/quick-posts.json 应读取已有内容。登录后验证列表、同源请求与既有图片；不发布一条生产测试消息。存量草稿、收藏与离线页属于旧 origin，不承诺自动跨域迁移，不清空旧缓存；新域 PWA 需重新打开或安装。

## 验收

1. 新域首页、某期日报、/api/latest.json、/feed.xml、/sitemap.xml 返回 200，canonical 为 xiyu.news。
2. 旧域及 www 同类路径返回 301，/x?y=1 的 Location 为 https://xiyu.news/x?y=1。
3. 代码合并、产物发布、域名生效、自然调度分别验收；测试不真实调用 AI、X 或 Telegram。
4. 保留历史 releases、验证证据、版本化旧媒体包、LICENSE、内部包/命令与兼容存储标识；它们不是当前品牌展示。
