# xiyunews 单项目运行清单

2026-10-03 已完成实际生产接管：单个 `xiyunews` Worker 提供 https://xiyu.news 的网站、后台/API、日报调度和实时看门狗；原 RecoveryGate 与 STATE KV 保留。业务代码 PR199 已合并，部署后证据串行回写 [Issue201](https://github.com/ohxiyu/xiyunews/issues/201)，父任务 [Issue198](https://github.com/ohxiyu/xiyunews/issues/198) 的剩余验收/退役仍开放。具体版本和未验证项以 [当前交接](handoff.md) 与 [上线记录](releases/2026-10-03-cloudflare-production-verification.md) 为准，不再执行旧的原地改名或初始Token流程。

## 当前入口与状态

| 资源 | 当前职责与边界 |
| --- | --- |
| 私有 ohxiyu/xiyunews | main 管业务代码，realtime/ 保留完整原历史；依赖、数据库与目标分开。 |
| Worker xiyunews | 正式域、静态 Assets、原后台 handler、调度和看门狗；源/出版完整SHA可由/health回读。 |
| RECOVERY_GATE | 原 namespace d4f55a5a95624e7e9776bbf050cf1ee7，已transfer至xiyunews本地类；不创建空替代、不delete migration。 |
| STATE | 原KV469346950dfc4f36b8d9bf9997d960fa；只读核验，不能清空failing/alerted或重置去重。 |
| 旧 Pages bmtnews | 已解除xiyu.news及对应CNAME，仍暂时保留历史；不是当前主域生产。 |
| 旧 dispatcher/watchdog | 已部署停用保护、XIYUNEWS_LEGACY_DISABLED=true、Cron为空；暂时保留，不能按旧创建配置重跑。 |
| 东京systemd fomobtc | 新仓d6a9d3f部署保持，原目录、SQLite/env、话题3/5/7不变；实时 API 主域 api.xiyu.news，旧 api.fomobtc.com 过渡保留。 |

## 自动发布

`cloudflare-unified.yml` 的 `XIYUNEWS_EDGE_ENABLED` 已设为精确 `true`。只接受可信main上的成功出版事件或main手动派发；同一生产concurrency组串行发布，固定读取main/gh-pages完整SHA，Jekyll渲染、公开资产校验、完整npm audit后部署同一项目，不采集、不调用AI、不写gh-pages/缓存/发送队列。

通常让出版成功自动触发即可。纯部署排查时，已获发布授权的负责人可以运行：

```bash
gh workflow run cloudflare-unified.yml --repo ohxiyu/xiyunews --ref main
gh run list --repo ohxiyu/xiyunews --workflow cloudflare-unified.yml --limit 5
curl -fsS https://xiyu.news/health
```

工作流成功后仍需核对source/artifact完整SHA、普通首页/API/RSS/PWA和自然运行；CI/dry-run/预览200不能替代生产。不得用混有多个快照的本机Assets父目录手工上传。首次实际部署验证链接在上线记录中，失败时不盲目重轮换凭据或重跑AI。

## 调度与恢复

原UTC三组Cron保持：`26 23 * * *`、`36,46,56 23 * * *`、`*/5 * * * *`；上海每日07:26定稿、刊期边界07:00、四小时采集规则不变。两种定时组件由同一入口独立执行，publication失败不抑制实时看门狗；旧服务专用的XIYUNEWS_LEGACY_DISABLED不能设到新项目上。

两条GitHub协调调用使用同一个精确true开关、`https://xiyu.news/publication/check` 与单独 `XIYUNEWS_RECOVERY_CHECK_TOKEN`，统一Worker中对应RECOVERY_CHECK_TOKEN。新Key缺失/接口失败必须停止，不使用旧端点/旧密钥回退或绕过共享锁。旧仓RECOVERY_CHECK_TOKEN没有覆盖；配置初始工具均拒绝覆盖已存在的Secrets，不重跑。

[Cloudflare说明](https://developers.cloudflare.com/workers/configuration/cron-triggers/)Cron变更可能最多15分钟传播。旧dispatcher/watchdog已部署入口no-op保护，不能仅凭Cron列表为空就声称旧回调不会执行；读自然日志时区分旧no-op、统一scheduled与GitHub实际workflow_dispatch。不要人为制造故障、重放队列或手动发送测试消息作为验收。

## 状态迁移与域名

已按 [transfer migration](https://developers.cloudflare.com/durable-objects/reference/durable-object-class-migrations-legacy/#transfer-migration) 将原RecoveryGate移至新Worker，namespace ID未变，STATE仍同一KV。先停旧调度、迁移暂停状态、核对原ID，再接主域和启新Cron；已完成的迁移不能当首次初始化重复执行，也不改服务器数据库或依赖。

xiyu.news已从Pages转为Worker Custom Domain，路径和查询参数由原网站handler/Assets继续处理；HTML旧链接可能由Assets规范化重定向，最终应200。bmt.news旧区/绑定已删除，不恢复旧域跳转，不触碰仍使用的fomobtc.com/API。Pages→Workers依据见[官方迁移说明](https://developers.cloudflare.com/workers/static-assets/migration-guides/migrate-from-pages/)。

www.xiyu.news 使用同 zone 的运维绑定 `www.xiyu.news/* → xiyunews`，复用已有代理 DNS/TLS，由同一 Worker 精确 Host 301 保留路径/查询到主域。该绑定不列入自动发布的非 Custom Domain 路由：既有 CI Token 无区路由管理权限，不能扩大权限或让每次部署反复报错；Wrangler 在没有声明普通 routes 时不调用区路由写入或清除。代码发布仍只声明主域 Custom Domain。重建环境时先由授权运维账号核验已有 www 路由无他人脚本冲突，再建立此精确绑定，禁止删除外部托管 DNS；具体错误/创建/验收见 [www 记录](releases/2026-10-13-www-entry.md)。

2026-10-05 接口迁移任务：新增专用 DNS-only A `api.xiyu.news` → 47.79.36.171，东京 nginx/独立证书提供 `/api/*`，统一看门狗改读 `https://api.xiyu.news/api/health`。旧域仅过渡保留；不修改主站、www 或通配符记录，不修改 STATE、Telegram 或发送服务。证书与 nginx 发布不等于 Worker 已发布，实际阶段以[迁移证据](releases/2026-10-05-realtime-api-domain.md)为准。

## 后台与凭据

保留原Access单账号、六路径、issuer/AUD/允许邮箱，正式域匿名请求仍进入Access；预览后台wrong-origin403，不关闭该保护。Quick Post复用原handler，令牌只在Worker中，公共页面无业务密钥。登录后仅只读验收，不发表生产测试新闻；登录页仍有BMTNews Admin显示名，需要仅改名称、保持所有权限设置。

运行8个Secret及GitHub两个部署Secret已通过隐藏输入/安全原设置复用补齐。Wrangler官方Pages下载仅取三个plaintext Access设置；服务器Bot与私聊目标仅在受保护进程内存/stdin传递，新恢复Key独立随机生成；未导出旧Cloudflare密文或复制CLI OAuth为业务Token。不要要求运营者重复Token或/start，不从截图、日志、剪贴板或聊天读取一次性秘密。

## 退役与剩余验收

新主域和原状态已接管；自动部署、两轮自然watchdog、自然dispatch、后台登录读取须分别补录。手机收件/实际私聊告警未验收时如实注明，无告警不能代替收件证据。旧三个边缘项目及旧独立仓库仍暂保留，完成验收并核对旧仓所有分支/PR/独有历史后，再按具体范围退役；浏览器删除和Access保存按操作时确认，不能据域解绑确认扩大范围。

必须保留现用DO/KV、实时域/API/DNS/nginx、服务器SQLite/env/备份、SSH和主仓。旧bmtnews-standalone是主仓重定向别名，不能按旧名删除；不影响其他产品或新增收费服务。实际结果回写独立文档PR，不直接提交main，不改历史release。
