# 群内信息流与事件追踪

Issue: https://github.com/ohxiyu/xiyunews/issues/234
Branch: agent/telegram-group-topics
PR: https://github.com/ohxiyu/xiyunews/pull/235
Baseline: 9d051a9d7c06cd3166217ce9203f4c524d013b21

运营者确认每日信息流＋每日事件进展两个话题的方案，并同意执行。当前会话为唯一 owner，只新增两个目的地，不改原频道、三个实时话题、Bot Token、源配置或服务器服务；不新增 AI 调用、不补历史。原工作区 tests/test_entity_profiles 2.py 未触碰。

## 本轮实际结果

实现只读消息快照准备模块：使用出版 API 与同一重点追踪索引，保留全部日报标题、前三条事实首句、固定日期/序号链接，长消息按完整条目分割，事件保留原 ID、状态、节点证据及已结束事件供后续收尾。仅供离线准备，尚未接入 Worker/工作流，不能宣称已经自动推送。

新增两话题专用初始化脚本，默认只读检查，不重跑原三话题脚本。创建前持久化未知状态，可能已创建但丢失回执时拒绝自动重复；Token 不写入回执或日志。此脚本尚未执行创建操作。

2026-10-12 使用既有 SSH 配置，严格主机校验、BatchMode 与 sudo -n 读取既有配置，在服务器进程内调用 getMe/getChat/getChatMember。确认 Bot 为 xiyunewsbot、群名 xiyu.news、forum=true、administrator=true，但 can_manage_topics=false。未扩大权限、未创建话题、未写 /etc/fomobtc.env、未重启服务、未发送消息。客户端只读替代路径尝试过，但 Telegram 的内容不提供可用 AX 操作；没有修改管理员设置。

阻塞：必须由运营者决定，只为现有 Bot 开启管理话题权限，或由管理员手动创建两个话题后提供话题链接。不能把“已经是管理员”当作具备所有管理权限。

## 准备阶段记录（已解除权限阻塞）

代码仅准备完成，发送与去重状态机、Worker 接入、配置绑定及自然回执均未完成。准备模块的离线测试另记录；PR 保持 Draft，不合并、不部署。获权限方向后先回读权限/话题，完成独立持久化发送记录、未知结果保护和自然发送验收。

离线回归：新增快照测试 5 项，完整主项目 pytest 1,061 项通过、4 项跳过；治理检查和 git diff --check 通过。验证范围只有准备代码与既有功能，不代表发送器、话题创建、生产或自然推送已经验收。

Source commit: 本轮未部署，现役 9d051a9d7c06cd3166217ce9203f4c524d013b21。
Worker version: not changed；现役只读核验 2431d2dd-5e7e-49f0-8226-6492698aac79。
Deployment: not performed；没有派发真实采集、AI、测试发送或部署工作流。
Verification: 仅配置存在、身份/群组/权限只读核验及离线消息准备测试，两个话题不存在创建成功回执，自动推送未配置。
Rollback: 无生产变更，无需回退；准备分支不能直接用于生产。

## 权限恢复与完整实现（2026-10-13）

运营者报告「现在有权限了」，严格主机校验重新读取权限确认 can_manage_topics=true。仅调用专用两话题脚本创建「📰 每日信息流」及「🧭 事件追踪」，返回两个不同的新话题 ID，服务器保留 mode 0600 私有回执；没有修改服务器环境或服务、没有发送新闻。绑定仅写入既有 KV 的 telegram-group:v1:config，启用日期为 2026-10-13；聊天/话题 ID 不提交仓库。

统一 Worker 使用独立命名 RecoveryGate 对象持久化每日任务与逐段回执。发送前记录 sending，明确成功记录 message_id，超时/非 JSON/回执不匹配保留 unknown，不自动重发；明确限流/暂时拒绝最多重试三次，遵循 retry_after。两个话题发送与排版失败隔离。仅复用既有五分钟 Cron，不修改调度、实时规则或任何密钥。

部署流水线在 Jekyll 渲染后从同一不可变 gh-pages 构建内部消息快照（公开 URL 返回 404）。快照、API 与首页当日日期必须一致，不发送昨日/未来/混合构建。日报保留全部标题、前三条事实首句和固定日期链接；事件初次标明当前概览，后续只发送新增实质节点及既有追踪的结束状态，最多六个重点事件，排名/改写/来源重复不算进展。观测节点与确认送达状态分开，未知首次送达不会在次日重复旧节点。

离线验证：实际出版数据快照成功生成；123 项 Worker 测试、audit、类型检查、dispatcher dry-run 通过，覆盖幂等、限流、暂停、未知结果、崩溃恢复、跨日、事件排版失败及来源转义。主项目全量 pytest 1,063 passed、4 skipped，治理与 diff 检查通过，CI 另补。未真实调用 AI、Telegram sendMessage 或生成新闻。

实现阶段记录时五阶段仍待 CI/合并/部署；下节记录已完成结果。网站最新日报为 2026-10-12，启用日已是 2026-10-13，不会补发 12 日内容。今日自然出版之后再核验两话题 message_id 和客户端展示；不能将 created/deployed 当作 sent。

运维：只读使用 wrangler kv key get telegram-group:v1:last-status --remote 和既有命名空间读取日期、bot_verified、各任务状态及回执；不公开发送接口。若结果 unknown，先由运营者核对群内是否已到达，不删除记录或盲目重发。停用本功能可在批准后仅将该配置 enabled 改为 false；不暂停统一 Worker，不影响旧频道/实时服务。回滚代码仍须运营者授权。

## 合并与生产部署证据

跟进 Issue: https://github.com/ohxiyu/xiyunews/issues/236；branch agent/telegram-group-deployment-record，当前会话唯一 owner。初始文档范围在发现运行时缺陷后已更新为群发送模块及测试、本记录和 handoff；不改运行配置或密钥。应用 PR235 在同步 origin/main 后于 2026-10-13 00:15:42（Asia/Shanghai）合并。CI [38275854964](https://github.com/ohxiyu/xiyunews/actions/runs/38275854964) 的 test、governance、edge-build、realtime 3.11/3.12 和 Pages 全部通过，CodeQL 按既有私有仓库条件 skipped。

Source commit: ed6211c53b15467e72e92eb9f6c28fd90d326f53。
Artifact commit: d5a1b6da90305d132dcf7157183d082d2f60169a（未生成/改写新闻）。
Worker version: 313f00fb-1f53-4d3a-ab5f-ea1b30bc8273。
Deployment: [38276156648](https://github.com/ohxiyu/xiyunews/actions/runs/38276156648)，已批准 workflow_dispatch、可信 main、既有 keep-vars 部署成功，没有直接 CLI 部署/改 Cron/密钥。
Verification: 2026-10-13 00:18 Asia/Shanghai，/health source/artifact/version 匹配且 status=ok，dispatcher/watchdog 仍 true、原 Cron 列表不变；首页、/api/latest.json、/threads/ 均 200，/api/_telegram-group.json 为 404。新 KV 配置已回读匹配，start_date=2026-10-13。自然 Cron 身份状态和两话题当日自然送达尚待后续回读。
Rollback: 无自动回滚；需要批准时仅停用群配置，不暂停旧功能，未知发送先查群内回执再决定处理。

PR235 五阶段：code complete；tests complete；PR merged complete；deployed complete；production verified pending。2026-10-13 00:20 自然 Cron 回读 enabled=true、date=2026-10-13、bot_verified=false、两个任务 not_prepared，未发送任何新闻。没有把 Cron 已运行称为机器人身份或自动推送可用。

## 运行时兼容性修正

修正版 PR: https://github.com/ohxiyu/xiyunews/pull/237。

定位证据：项目安装的 workerd 二进制明确报错，redirect 只实现 follow/manual，error 未实现。原网络 mock 未构造真实 Request，掩盖了请求在发出前就被运行时拒绝的差异；不据此更换 Token、重建话题或增加权限。修正为 manual，显式拒绝 3xx，既不跟随跳转也不泄露 Token 到跳转目的地。所有模拟 Bot API 先构造真实 workerd Request，再替换网络响应，并补重定向拒绝测试。修正版沿用原已批准功能部署，真实自然回执仍需当天出版后确认。

修正版本地验证：124 项 Worker 测试、audit 无漏洞、types/tsc、dispatcher dry-run 通过。Python 未修改，沿用同源完整 1,063 passed、4 skipped，并由 CI 再次回归；治理/diff 在提交前再次校验。修正版 PR/部署/自然身份核验 pending。
