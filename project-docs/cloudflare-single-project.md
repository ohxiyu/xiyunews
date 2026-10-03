# xiyunews 单项目迁移

基础对应已合并 PR197 / [Issue196](https://github.com/ohxiyu/xiyunews/issues/196)，生产接管对应串行 [Issue198](https://github.com/ohxiyu/xiyunews/issues/198)。最终只有一个 `xiyunews` Worker，提供网站、原后台和 API，以及日报调度和实时看门狗；东京服务仍独立运行，不合并 Python 依赖、数据库或目的地。当前三个边缘项目仍在生产，不可先删后迁。

## 迁移基础与自动发布

`ops/daily-dispatcher/src/unified.ts` 直接复用原网站、dispatcher 和 watchdog，未重做 UI。当前线上暂停版本两个开关关闭且 Cron 为空，RecoveryGate 仍外部绑定原 namespace；本阶段最终配置准备了同 namespace 的 transfer、本地绑定、原三组 Cron 和正式域，STATE 仍复用原 KV。最终配置尚未实际上传，不要因为源码有 true 就认为线上已启用，也不能重建空状态。

`cloudflare-unified.yml` 在出版工作流成功后串行读取最新 `gh-pages` 固定 SHA，Jekyll 渲染、校验资产后部署；不依靠 GITHUB_TOKEN 推送触发另一 push 工作流，不采集、不用 AI、不写状态分支。只有 `XIYUNEWS_EDGE_ENABLED=true` 才可部署；2026-10-03两个仓库部署Secret已保存并回读名称/更新时间，变量仍未启用。新增CI真实构建出版快照并dry-run，不以占位文件证明上线。

最终配置现已在同一 Issue198/PR199 准备，不另开重叠任务：保留原 namespace 的本地绑定、transfer tag、正式域和原 Cron，避免后续自动发布恢复过渡状态。check_coordinator 的同一 XIYUNEWS_EDGE_ENABLED 开关精确 true 时才使用正式域和单独暂存的 XIYUNEWS_RECOVERY_CHECK_TOKEN，否则保留旧端点与旧 RECOVERY_CHECK_TOKEN。新密钥缺失时停止，不使用旧密钥/旧端点回退，也不绕过共享锁补发；两条工作流同步传递变量和两个秘密名。免 AI 恢复已支持统一发布工作流。

现役控制台与官方 PATCH API 的原地改名曾作为候选，但状态和秘密值保留未验证，未执行。2026-10-03已采用下述新项目 transfer 路径的第一步：实际部署独立、无 Cron、双开关关闭的 xiyunews 暂停预览，版本8b365058-fc4b-46db-9a52-0bc3e156f81b；原三个项目仍生产。不要再尝试把旧项目改为已占用的同名项目，或创建空目标 DO。

## 安全配置缺口

2026-10-03运营者已隐藏输入单仓库 GitHub 运行 Token，独立回读两个 Secret 名称和 /ready=ready。随后安全复用原 Pages 三个 plaintext Access 设置、服务器现役新 Bot 和话题切换前备份中的唯一私聊 ID，保存到暂停 Worker；当前共8个运行 Secret 名称已回读。原 Worker 的加密值没有导出，单账号邮箱/issuer/AUD原值保留，不进公开文档或 Git；原 CF ALERT_CHAT_ID 的密文仍无法读取直接比对，新的目标来源与原 setup_watchdog.sh 一致，不以此宣称实际告警收件已验证。

GitHub仓库级 CLOUDFLARE_API_TOKEN 和 CLOUDFLARE_ACCOUNT_ID 已通过隐藏输入配置，运行8个 Secret 也已补齐，自动发布仍未启用。本阶段取消对不存在的 xiyunews-production 环境的硬依赖，保留main/可信源/成功/手动启用门槛。[GitHub 文档](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments)说明私有仓环境能力有套餐限制，不购买升级或移除现役保护，不把本机OAuth复制为业务凭据。

服务器专用可信 SSH 已恢复并完成新仓 SHA 切换；新 Bot 为原群管理员，已有行情、公告和资金流向共 11 条自然发送成功回执。步骤与实际记录见 [服务器清单](realtime-server-migration.md) 和 [新 Bot 记录](../realtime/docs/releases/deploy-20261002-xiyunews-bot.md)，不再等待失效旧配置、重复 /start 或要求给旧 Bot 授权。

### 自动发布凭据的隐藏输入

操作时确认新建令牌及写入 GitHub Secrets 后，由运营者在本机交互终端执行 `python3 scripts/configure_edge_deploy_token.py`，粘贴到禁止回显的提示，不把 Token 放到命令参数、环境文件或聊天中。脚本只读校验 Token 状态、指定账户的现役调度器身份、统一发布尚未启用，再通过 stdin 调用 `gh secret set`，回读只取两个 Secret 名称；不修改 Cloudflare 运行配置、不启用变量或部署。需要已登录的 `gh` 和本机 `/usr/bin/curl`；HTTP 不跟随重定向，错误不回显上游输出。若中途失败，只报告部分配置可能存在，不擅自删除或重复轮换。

此脚本只解决 GitHub 的 Cloudflare 自动发布权限，不补齐新 Worker 的 GitHub dispatch/Admin/Recovery/Telegram 运行 Secret，也不验证写权限或业务上线。它假定现役调度器尚未改名，须在改名前执行；原地改名后不要按旧名称重跑。需要轮换时另行审查，不能把读校验成功当部署成功。

若提示 GitHub 只读失败，先在发生失败的同一终端运行 `python3 scripts/configure_edge_deploy_token.py --check-github`；该模式不要求令牌、不会写 Secret，也不会读取原值。脚本在隐藏输入前预检，并区分 CLI 缺失、登录失效、仓库权限、限额和网络错误，只输出固定提示，不显示上游正文。PATH 没有 gh 时尝试本机既有 `/opt/homebrew/bin/gh`，不自动安装、换账号或修改代理；需要登录时由运营者完成，不从其他会话复制认证凭据。修复后复用已经创建的 Cloudflare Token，不必再次创建。

## 切换与验收

### GitHub 运行凭据的隐藏输入

运营者已完成 GitHub Mobile 验证并在操作时确认创建单仓库运行 Token：仅 ohxiyu/xiyunews 的 Contents/Actions 读写、Metadata 只读，无账户权限，2027-01-01到期。已点击 Generate token，但没有读取创建后的页面或截图；令牌是否实际生成由运营者查看页面并复制，不把点击当配置完成。此令牌本身可改选中仓库的任意内容，不只是新闻文件；不使用本机广权限 gh/OAuth 凭据替代。

在本机交互终端运行 `python3 scripts/configure_edge_runtime_token.py`，将新 GitHub Token 粘贴到禁止回显的提示。脚本先核对自动发布未启用、指定账户内 xiyunews 存在、公开健康标识与固定 SHA 完整、双开关关闭、两个目标 Secret 不存在，然后只读核对私有仓和 Actions 可访问；写前再次预检，通过 Wrangler stdin 一次提交 ADMIN_GITHUB_TOKEN/GITHUB_DISPATCH_TOKEN，回读只取名称。错误不输出上游正文，禁止参数/管道/输入回显降级，不写令牌文件，关闭 Wrangler 文件日志和遥测；部分成功不自动重试覆盖。

`--check-only` 模式不读令牌、不写配置，本机已实际通过；19项离线回归均用假 Token。工具不启用 Cron/主域/Access/自动发布、不写测试新闻或派发任务、不触碰旧项目，也不补 Recovery/Telegram/Access 凭据。初始 Secrets 已存在时拒绝覆盖，轮换需发布负责人另行安排。保留新页面至运营者完成复制，不让助手读取一次性秘密值。

1. 已完成基础合并、暂停预览和安全配置；最终配置与切换保护在同一串行 PR199 完成回归，合并后从确切 main SHA 部署。切换前的临时运行配置保持无 Cron/无主域/双开关 false，不关闭非正式 origin 的后台拒绝。
2. 保持新 Cron 暂停，核对 `/health` 项目与 source/artifact SHA、`/ready` 和免 AI 发布路径，内容须与现生产一致。
3. 选无活跃日报/分发任务窗口，先给旧 dispatcher/watchdog 部署已验证的停用保护（XIYUNEWS_LEGACY_DISABLED=true）并清空旧Cron，保留业务实现/Secrets/状态/历史版本；等待在途调用结束并回读停用状态。Cron撤销有传播延迟，因此旧回调必须在任务入口no-op，不能只凭清空列表就启新Cron。
4. 使用最终配置的 transfer migration 迁入 RecoveryGate，去掉 script_name；禁止先创建目标类。保持 STATE 同一 KV ID，回读 namespace_id/归属；源和目标代码相同，仅保留原状态，不为了测试写租约/预算或重置数据库。迁移阶段新 Cron 仍暂停。
5. 经确认将新主域从 Pages 转入 Worker Custom Domain，保持同路径、查询参数与 Access；验收匿名拦截和登录 Quick Post 读取，不发布测试新闻。
6. 最终统一配置填回原三组 Cron：`26 23 * * *`、`36,46,56 23 * * *`、`*/5 * * * *`。确认双开关开启后才启用自动部署变量，验证自然 workflow_dispatch 和至少两次自然 watchdog 检查。
7. 新主域公开输出与后台、服务器新仓完整 SHA/三现货分片/自然 message_id 全部核验后，才退役旧项目与旧仓。浏览器删除需操作时确认；保留仍使用的 DO/KV、实时域/API、SQLite、环境文件和备份。

状态迁移依据 [Cloudflare transfer migration](https://developers.cloudflare.com/durable-objects/reference/durable-object-class-migrations-legacy/#transfer-migration)，网站迁移依据 [Pages → Workers](https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/)。保留现役服务不等于迁移完成，HTTP 200 不等于自然推送；失败时不擅自回滚或启动第二发送者。

## 工具链安全验证

### 原设置复用的工具与边界

[Cloudflare说明](https://developers.cloudflare.com/workers/configuration/cron-triggers/)Cron变更可能最多15分钟传播。本轮为旧dispatcher与watchdog增加精确true停用保护，默认未设置时原行为不变；旧Cron回调不请求API/写KV/通知，旧publication/check返回503 retired，health回读停用状态。此保护源代码准备并测试，尚未部署到旧项目；只在实际切换阶段启用，统一项目不设置该旧服务专用变量。新旧回调及自然发送验收仍分别核对，不把部署成功当传播完成。

在生产配置授权下，scripts/configure_edge_preserved_settings.py（uv run python，Python3.11+）先检查暂停目标、已有两个 GitHub 运行 Secret、暂存恢复 Secret 未存在。--inspect-only 仅核验来源、不输出值或保存 Secrets；原 Pages 官方 download config 只导出 plaintext 设置，CLI生成文件位于仓库外0700临时目录，toml为0600，只选三个 Access 字段。服务器通过严格指纹 SSH/root0600配置读取现役 Bot，验证进程、源码及话题不变、备份只有唯一 positive 私聊 ID、getMe/getChat 正确；没有提取原 CF 密文或发送消息。

实际配置只在内存和受保护子进程 stdin 传递选定字段，错误不转发上游正文、Wrangler文件日志/遥测关闭。新 Recovery 随机密钥保存到统一 Worker 的 RECOVERY_CHECK_TOKEN 和仓库 XIYUNEWS_RECOVERY_CHECK_TOKEN，旧仓库 Secret 不覆盖。所有初始字段存在时拒绝重跑，不自动删除或重复轮换；部分失败保留现场。工具18项与运行Token工具19项假数据测试、实际来源检查及名称回读通过，不等于正式域/自然Cron/手机收件验收。

原锁定 Node 开发依赖 audit 报告 7 项（5 high、2 moderate，Wrangler/Miniflare/Undici/Sharp/Vitest 链）。本轮已锁定 Vitest 4.1.11、Wrangler 4.131.0 和配套 workers-types 5.20260910.1，并用 overrides 锁定 Undici 7.29.1、Sharp 0.35.4；保留测试池 0.22.0，不用 force/legacy-peer-deps。重新安装后完整 npm audit 为 0，94 项边缘测试、类型检查和原调度器 dry-run 通过。

`npm run check` 与统一生产发布工作流均包含覆盖开发依赖的低级别审计门槛，不以 omit-dev 隐藏工具链问题。32a838fb 的 CI37012988502 已完成真实 Jekyll/资产构建及新版本 dry-run，全部可用检查成功；这不是实际部署，也不据原告警宣称主站曾被攻击。没有新增收费服务或模型。服务器连接、版本、Bot 管理员及三类自然回执已验证；Cloudflare 安全配置与生产切换仍未完成，现役边缘服务保留至接管和自然验收。
