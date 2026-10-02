# Cloudflare 单项目生产接管：进行中

Task: https://github.com/ohxiyu/xiyunews/issues/198
Source commit: 基线 91fb5981cd09a51be7c3ef8c355eb6ee179f60fa，PR197 的实际 merge SHA。
Worker version: 统一项目未部署；现役调度器和看门狗版本见基础记录。
Deployment: pending；尚未保存 Cloudflare 权限或 Secret，未改主域、Cron、DO/KV 或服务器配置。
Verification: 前序基础 99d2465e 的 CI37024644728 全部可用检查和 Pages 预览通过；CodeQL 跳过。当前阶段的新增回归结果随后追加，不沿用基础测试当本阶段全量验证。
Rollback: 当前阶段未生产切换；保留现役项目与服务器备份，不双调度、不擅自回滚或覆盖发送数据库。

## 顺序与边界

PR197 于 2026-10-02T15:09:10Z 合并，Issue196 基础关闭，当前负责人从新 main 建立 agent/xiyunews-edge-cutover，复用唯一干净工作区。生产接管不是基础合并的自动结果；网站 UI、采集窗口、实时阈值、话题和服务器部署方式不改。

新增协调入口受同一个 `XIYUNEWS_EDGE_ENABLED` 变量控制，迁移前仍走旧入口，启用后走 `https://xiyu.news/publication/check`。两条自动调用工作流都传递变量，只有小写精确 `true` 生效；新入口失败不回退旧入口，也不绕过共享锁直接派发，回归全部使用模拟响应和测试 Token。

Safari 现役 Worker 设置提供名称字段，官方 Workers Beta PATCH 也支持只更新 name、其他字段不变；这说明存在可评估的原地改名入口，不证明 DO、Cron、子域和 Secrets 已成功保留。当前未保存改名或改变配置。实际执行前必须回读不可变 Worker ID、DO namespace ID、Secret 名称和 Cron；失败不重置状态、不盲目继续。

自动发布令牌只准备到创建前：现役单账户 Workers Scripts 编辑、2027-01-01 到期，无 DNS/Access/账单权限。这类账户级权限仍能编辑同账户其他 Worker，已经向运营者说明，不宣称仅能编辑 xiyunews；尚未创建或读取值。运行 Secret 的安全注入仍是实际阻塞，不用广权限 CLI 或 OAuth 凭据替代，不能导出旧加密值或添加明文接口。

发现基础工作流硬引用的 xiyunews-production 环境不存在，私有仓环境能力还受套餐限制，当前 API 没有返回 plan。改为仓库级 Secret 路径，不要求购买或创建环境，main/可信源/成功/手动启用保护不变；新增离线回归检查，不移除任何现役环境保护。实际部署凭据依然尚未配置，默认不发布。

准备 `scripts/configure_edge_deploy_token.py` 作为运营者确认后执行的隐藏输入工具：拒绝非交互输入与回显降级，Token 只在内存/stdin，固定 HTTPS API 且不跟随重定向，只读核验账户和调度器后加密写入两个仓库部署 Secret。错误不显示上游正文，部分失败不自动删除/重试，自动发布已启用时拒绝此初始配置流程；不读取旧 Secret、不启用生产、不创建 Token。所有新增测试采用假 Token 和模拟命令，不运行实际凭据写入。

初次回读实时服务器三类自然消息 1251/1250/1249，共 11 条 sent；后续只读核验增长到 18 条 sent、9 条按规则 archived，最新资金流向 1258、公告 1257、行情 1254，无失败状态。原群话题保留，手机收件及看门狗私聊实际告警仍未独立验证，不制造告警或重放旧消息。旧 Cloudflare 资源仍承担业务，不能先删除。

## 群名称实际统一与验证

运营者此前明确确认 Telegram 名称为 xiyu.news，本次仅更正现役实时群实际大小写/格式。服务器进程 getMe 为 @xiyunewsbot，原群 administrator 且已有 can_change_info=true；核对新仓 SHA、原群/话题3/5/7之后调用 setChatTitle。2026-10-02T15:22:48.674197Z（上海23:22:48）getChat 回读为 xiyu.news，forum=true，简介逐值保持；不改成员权限、创建话题、重启服务、改 Token/配置或另发宣布/测试消息。Token始终留在服务器，不进入本机、Git 或日志；Telegram 自身可能生成改名服务记录，这不是业务测试推送。

## 本阶段离线及真实构建

主站完整 968 项、治理、实时独立61项/契约和看门狗3项通过。新增7项协调接口/工作流门槛与8项安全配置工具测试，全用模拟响应/假Token，不真实请求AI或发送消息。初次本机默认Ruby4缺少csv导致Jekyll失败，改用现有Ruby3.3.12，与CI配置一致；未因此改主项目Gemfile或提交本机生成的lock。233597f892c086e82d5cc13f3a7041448242424b的出版快照真实Jekyll渲染成功，prepare_edge_assets校验成功，统一Wrangler dry-run读取8364个资产、入口压缩22.72KiB；该结果不是Worker已发布。

关联：[当前交接](../handoff.md)、[切换清单](../cloudflare-single-project.md)、[基础记录](2026-10-02-cloudflare-unified-foundation.md)、[新 Bot 自然回执](../../realtime/docs/releases/deploy-20261002-xiyunews-bot.md)。
