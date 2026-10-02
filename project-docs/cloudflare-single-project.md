# xiyunews 单项目迁移

本文件对应 [Issue196](https://github.com/ohxiyu/xiyunews/issues/196)。最终只有一个 `xiyunews` Worker，提供网站、原后台和 API，以及日报调度和实时看门狗；东京服务仍独立运行，不合并 Python 依赖、数据库或目的地。当前三个边缘项目仍在生产，不可先删后迁。

## 迁移基础与自动发布

`ops/daily-dispatcher/src/unified.ts` 直接复用原网站、dispatcher 和 watchdog，未重做 UI。统一配置名为 `xiyunews`，所有请求先经原鉴权；默认两个开关关闭且 Cron 为空。RecoveryGate 暂时外部绑定原命名空间，STATE 复用原 KV，不能新建空状态代替。

`cloudflare-unified.yml` 在出版工作流成功后串行读取最新 `gh-pages` 固定 SHA，Jekyll 渲染、校验资产后部署；不依靠 GITHUB_TOKEN 推送触发另一 push 工作流，不采集、不用 AI、不写状态分支。只有 `XIYUNEWS_EDGE_ENABLED=true` 才可部署，目前变量和自动部署凭据均未配置。新增 CI 真实构建出版快照并 dry-run，不以占位文件证明上线。

此配置只作过渡：自动部署启用前，最终切换 PR 必须把 DO 改为迁入的本地绑定，并填写正式 Cron，否则后续发布会恢复过渡配置、移除 Cron。`src/schedule_watchdog.py` 的 `check_coordinator` 固定旧端点同时须改为 `https://xiyu.news/publication/check`，相关回归同步更新。免 AI 的部署恢复已支持固定新工作流，不再使用旧 Pages hook。

## 安全配置缺口

只读过 Secrets 名称，未读取值。新 Worker 需要运营者从原安全保管位置注入 GitHub dispatch、recovery、Admin 写权限凭据，以及原实时私聊的 Bot/目标 ID；不能用日报频道替代看门狗私聊。保持现有 Access issuer/AUD/单账号邮箱校验与新域六路径，不扩大白名单。旧 Worker 加密 Secrets 不能从名称列表恢复，本机 Wrangler OAuth 也不能复制成 Actions Token。

GitHub 环境 `xiyunews-production` 需要最小权限 `CLOUDFLARE_API_TOKEN` 和 `CLOUDFLARE_ACCOUNT_ID`；持久权限新建与 Secret 修改需确认，不在聊天中发凭据。目前环境尚不存在，仓库 Secrets 也没有这两项，不能把本机 OAuth 当成自动发布权限。服务器专用可信 SSH 已恢复并完成新仓 SHA 切换；新 Bot 为原群管理员，已有行情、公告和资金流向共 11 条自然发送成功回执。步骤与实际记录见 [服务器清单](realtime-server-migration.md) 和 [新 Bot 记录](../realtime/docs/releases/deploy-20261002-xiyunews-bot.md)，不再等待失效旧配置、重复 /start 或要求给旧 Bot 授权。

## 切换与验收

1. 基础 PR 全部可用 CI 通过后合并，再从新 main 建立串行生产切换 Issue/分支/PR。确认 Worker 部署授权后可先发布无 Secret、无 Cron、双开关关闭的暂停预览，验证静态资源/API/RSS/sitemap/历史页/404/PWA；此步骤不接管主域或推送，不关闭非正式 origin 的后台拒绝。
2. 保持新 Cron 暂停，核对 `/health` 项目与 source/artifact SHA、`/ready` 和免 AI 发布路径，内容须与现生产一致。
3. 选无活跃日报/分发任务窗口，先停旧 dispatcher/watchdog Cron，保留代码、Secrets 和状态并等回调结束，不双调度。
4. 串行切换 PR 使用锁定 Wrangler 支持的 transfer migration 迁入 RecoveryGate，去掉 `script_name`；禁止先 new_sqlite_classes 目标类。保持 STATE 同一 KV ID，回读命名空间归属/租约/预算；失败停下，不重置。
5. 经确认将新主域从 Pages 转入 Worker Custom Domain，保持同路径、查询参数与 Access；验收匿名拦截和登录 Quick Post 读取，不发布测试新闻。
6. 最终统一配置填回原三组 Cron：`26 23 * * *`、`36,46,56 23 * * *`、`*/5 * * * *`。确认双开关开启后才启用自动部署变量，验证自然 workflow_dispatch 和至少两次自然 watchdog 检查。
7. 新主域公开输出与后台、服务器新仓完整 SHA/三现货分片/自然 message_id 全部核验后，才退役旧项目与旧仓。浏览器删除需操作时确认；保留仍使用的 DO/KV、实时域/API、SQLite、环境文件和备份。

状态迁移依据 [Cloudflare transfer migration](https://developers.cloudflare.com/durable-objects/reference/durable-object-class-migrations-legacy/#transfer-migration)，网站迁移依据 [Pages → Workers](https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/)。保留现役服务不等于迁移完成，HTTP 200 不等于自然推送；失败时不擅自回滚或启动第二发送者。

## 工具链安全验证

原锁定 Node 开发依赖 audit 报告 7 项（5 high、2 moderate，Wrangler/Miniflare/Undici/Sharp/Vitest 链）。本轮已锁定 Vitest 4.1.11、Wrangler 4.131.0 和配套 workers-types 5.20260910.1，并用 overrides 锁定 Undici 7.29.1、Sharp 0.35.4；保留测试池 0.22.0，不用 force/legacy-peer-deps。重新安装后完整 npm audit 为 0，94 项边缘测试、类型检查和原调度器 dry-run 通过。

`npm run check` 与统一生产发布工作流均包含覆盖开发依赖的低级别审计门槛，不以 omit-dev 隐藏工具链问题。32a838fb 的 CI37012988502 已完成真实 Jekyll/资产构建及新版本 dry-run，全部可用检查成功；这不是实际部署，也不据原告警宣称主站曾被攻击。没有新增收费服务或模型。服务器连接、版本、Bot 管理员及三类自然回执已验证；Cloudflare 安全配置与生产切换仍未完成，现役边缘服务保留至接管和自然验收。
