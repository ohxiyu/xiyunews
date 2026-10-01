# 稀有News 品牌与域名迁移

## 发布顺序

网页站名为 xiyu.news，中文品牌为稀有News。运营者于 2026-10-01 更改决定：不保留旧域入口，也不要旧域跳转。当前仅 xiyu.news 是正式入口，旧域 bmt.news/www.bmt.news 在 Worker 返回 410，无 Location；不再提供网站、后台、API 或订阅入口。原“旧文章全站 301”目标已被撤销，历史发布记录不改写。

旧域 DNS、注册、TLS 与 Pages 绑定保留，未删除任何资源；停用入口由正常 Actions 发布的 Worker 实现，可经授权代码修改恢复。LEGACY_REDIRECT_ENABLED 已废弃，任意值都不再开启 301，不创建 Redirect Rule，也不手动写 gh-pages。

Cloudflare Free zone 的 NS 为 ignat.ns.cloudflare.com 和 shaz.ns.cloudflare.com。保存后核对注册商回读、权威 DNS 和 Cloudflare active；创建 zone 不等于上线。Pages 内部项目名可保留 bmtnews，关联仓库须核对为 ohxiyu/xiyunews，生产分支仍为 gh-pages。

## 旧域停用

docs/_worker.js 精确匹配两个旧 Host，在认证、API、资产和缓存之前返回 410。不存在的路径与管理路径也不能访问原资源；不会带私有令牌请求仓库。新主域 canonical、订阅和对外文案统一为 https://xiyu.news。

## 私有仓库兼容

运营者已要求主仓库及实时服务仓库保持私有，导入历史前必须以 GitHub API 再核对两仓 private=true。Cloudflare Git 集成支持私有仓库，但仍须实测其已安装应用可以拉取发布分支；不要恢复公开来修复权限。自动发布继续写 gh-pages 分支，不依赖公开 GitHub Pages 站点。

GitHub CodeQL 私有扫描需要已有 Code Security 授权，本轮不新增付费产品。CodeQL 默认只在公开仓库运行；如运营者以后已有授权，可显式设置仓库变量 CODEQL_PRIVATE_ENABLED=true。私有状态下不能把跳过 CodeQL 说成扫描通过；pytest、Worker 检查、治理和 pip-audit 仍运行。阶段 2 须把调度器未认证 raw 读取改为认证的 GitHub 内容 API，且禁止将仓库令牌发送到公共网站或重定向后的域名。

## 后台与 Quick Post 配置

既有 Access 应用仅保留新域六路径 /s、/s/*、/admin、/admin/*、/api/admin、/api/admin/*，旧域六路径已按操作时确认移除。允许邮箱、验证方式、策略与 AUD 保持，不扩大用户或设置公开绕过。Pages 的既有认证与仓库写入 Secrets 保持，只核对权限存在，不抄写值或重发密钥。

匿名 /s/ 应进入 Access 验证，公开 /api/quick-posts.json 应读取已有内容。登录后验证列表、同源请求与既有图片；不发布一条生产测试消息。存量草稿、收藏与离线页属于旧 origin，不承诺自动跨域迁移，不清空旧缓存；新域 PWA 需重新打开或安装。

## 验收

1. 新域首页、某期日报、/api/latest.json、/feed.xml、/sitemap.xml 返回 200，canonical 为 xiyu.news。
2. 旧域及 www 的首页、文章、API、feed、openapi、llms、/s 和 /x?y=1 都返回 410，且无 Location。
3. 代码合并、产物发布、域名生效、自然调度分别验收；测试不真实调用 AI、X 或 Telegram。
4. 保留历史 releases、验证证据、版本化旧媒体包、LICENSE、内部包/命令与兼容存储标识；它们不是当前品牌展示。
