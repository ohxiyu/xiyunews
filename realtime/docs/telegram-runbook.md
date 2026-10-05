# Telegram 运行与验收

## 当前结构
systemd `fomobtc` → Python asyncio采集 → SQLite事件/发送队列 → Telegram Bot API。
网页前端已下线，只保留只读API；关闭健康检查页面不影响服务。入口src/platform/app.py；发送src/platform/delivery.py；持久化src/platform/store.py；配置src/platform/settings.py。

2026-10-03看门狗已并入统一Cloudflare项目xiyunews，旧独立Worker停用、Cron为空；原STATE和话题不变，初始凭据已补齐。当前发布/验收只跟随[根交接](../../project-docs/handoff.md)，下方带历史日期的初始化脚本不能作为再次执行授权，不重跑setup_watchdog或测试发送。证据见[统一边缘接管](releases/cloudflare-cutover-20261003.md)。

### 当前 Bot 与原话题（2026-10-02）

运营者明确指定 `@xiyunewsbot` 并要求保留原群和话题，已通过本机隐藏输入更新实时服务与现役看门狗。21:03:05单服务重启，21:06只读核验运行Bot为xiyunewsbot、原群administrator，排除Token后全部环境配置与备份相同；行情/公告/资金流向仍使用话题3/5/7。不要重跑下面历史私聊或话题创建脚本，它们会修改目标或创建话题；自然消息回执与手机收件单独验收，详见 [切换证据](releases/deploy-20261002-xiyunews-bot.md)。

本次看门狗只更换TELEGRAM_BOT_TOKEN，不重写ALERT_CHAT_ID，不清KV或修改Cron。运营者已报告对新Bot发送/start，21:24核验新Bot收到切换后私聊/start且私聊可读取，不需重复发送；实际告警送达尚未验收，也未直接比对加密ALERT_CHAT_ID。原Bot曾因只读群内身份为member遭拒绝，这是历史问题，不再要求恢复旧Bot权限；管理员身份或/start均不等于已经取得自然送达回执。

## 配置
东京服务器配置文件 `/etc/fomobtc.env`，root:root，0600。当前SSH使用运营者电脑 `/Users/minutesdr/.ssh/xiyunews_tokyo_config` 中 `xiyunews-tokyo`，兼容 `fomobtc-tokyo`；2026-10-02专用访问已获操作时确认并通过严格主机校验。私钥留本机，不进仓库；新电脑没有此配置时需重新取得安全连接，不复制私钥到聊天。详见 [连接验证](releases/ssh-access-20261002.md)。
必需环境变量：`TELEGRAM_BOT_TOKEN`、`TELEGRAM_CHAT_ID`。公告可单独设置 `TELEGRAM_ANNOUNCEMENT_CHAT_ID`，否则使用默认Chat。启用开关 `TELEGRAM_ENABLED=true`。
默认 `TELEGRAM_CHAT_INTERVAL=3.1` 秒。Token不得出现在聊天、命令输出、git或日志URL中。只记录配置是否存在。

## 启用顺序
1. 核对当前服务只有一个实例、源码提交、数据库备份。不要重置事件、seen、冷却或发送队列。
2. 用户将Token和Chat ID写入安全配置。Bot须已加入目标群/频道并获发消息权限；私聊须先向Bot发/start。
3. 用已配置Token调用getMe核验Bot，getChat核验目标，日志只记录成功/失败及脱敏结果；不输出请求URL或Token。
4. 核对既有pending/sending/unknown，禁止盲目重发unknown；确认没有历史补发队列后启用并重启单实例服务。
5. 向用户明确授权的目标发送标记清楚的测试消息；记录HTTP ok及message_id，再由用户确认手机收件。这两项不能互相替代。
6. 观察一条自然触发的现货或中文公告自动发送，记录事件ID、发现时间、发送时间、回执及手机验收。测试消息不能证明自然事件端到端成功。

## 固定业务规则
- 仅 USDT 现货，24h 成交额至少 50 万 USDT；最近 3 分钟涨跌超过门槛（按成交额 2% / 3% / 5%）并持续 3 秒即提醒（2.6.0 起唯一规则）；参数见[数据契约](data-contract.md)。
- 同币种同方向 1 小时一次，期间较上次提醒价再涨/跌 10% 立即再提醒；创 24 小时新高/新低时附注。重启持久化，通知关闭期间也记门控，开启不补发旧事件。行情标题与 API 一致。
- 公告按文章去重；初始历史基线不推送；营销类默认不推送。中文正文/简讯ready才可发送；自动翻译尚未接入。
- 行情队列120秒过期，公告1小时过期。超时/中断可能已送达时记unknown，不自动假定失败；429遵守retry_after；5xx有限退避重试。保留回执。

## 后续优先级
P0：安全配置Bot和目标；收件验收；行情中文标题已实现，实际自然事件交付仍待验证。
P1：官方中文缺失时接入用户选定的翻译服务；区分采集失败、翻译等待、过期、发送失败。
P2：自然事件延迟P95/P99、断线恢复与24小时稳定性。Binance/Hyperliquid当前为轮询降级，不承诺实时SLA。
暂缓：图表、市值增强、历史回填、多市场扩张。

## 2026-09-16 私聊准备
用户已创建机器人，暂不加入群组。先在机器人私聊点击开始或发送/start，再由用户通过服务器编辑器将Token写入/etc/fomobtc.env，不要粘贴到聊天、命令参数或git。保持TELEGRAM_ENABLED=false，通过getUpdates识别私聊chat.id并核验目标后填写TELEGRAM_CHAT_ID。保留原有配置项，不覆盖整份文件。不关闭群组隐私模式、不申请群组权限。仍按上面的队列检查和启用顺序验收；本轮未发送消息。

## 一键私聊配置（scripts/setup_telegram.sh）
在本机运行 `ssh -t -F /Users/minutesdr/.ssh/xiyunews_tokyo_config xiyunews-tokyo 'sudo bash /opt/fomobtc/current/scripts/setup_telegram.sh'`。脚本隐藏输入 Token（不进命令行/日志），getMe 核验机器人，提示私聊 /start 后用 getUpdates 取私聊 Chat ID 并请用户确认，显示待发送队列，发送测试消息并等待用户确认手机收件，之后备份 /etc/fomobtc.env（0600）、写入 Token/Chat ID/TELEGRAM_ENABLED=true 并重启；启动失败自动恢复备份。自然事件推送仍需单独观察记录。

## 币安公告实时流（scripts/setup_binance_announcements.sh）
在本机运行 `ssh -t -F /Users/minutesdr/.ssh/xiyunews_tokyo_config xiyunews-tokyo 'sudo bash /opt/fomobtc/current/scripts/setup_binance_announcements.sh'`。币安 API Key 只勾“启用读取”，IP 可不限制。脚本隐藏输入 Key/Secret，用签名的 /sapi/v1/account/apiRestrictions 校验有效且只读（开启任何交易、提现、划转权限即拒绝），备份 /etc/fomobtc.env 后写入并重启，40 秒内 binance_announcements 未变为 live 则自动恢复。

## 群组话题（scripts/setup_telegram_topics.sh，2.5.0）
新建群组并开启“话题”，把机器人设为管理员并勾选“管理话题”，在群里发送 /start@机器人名，然后运行 `ssh -t -F /Users/minutesdr/.ssh/xiyunews_tokyo_config xiyunews-tokyo 'sudo bash /opt/fomobtc/current/scripts/setup_telegram_topics.sh'`。脚本创建 📈 行情异动 / 📢 交易所公告 / 💰 资金流向 三个话题并发送测试消息，确认后写入 TELEGRAM_CHAT_ID 与 TELEGRAM_TOPIC_*，私聊不再接收推送。

## 群组权限与入口（2026-09-25）
成员只读：默认权限只保留表情回应，其余（发言、媒体、投票、邀请、置顶、管理话题）全部关闭；机器人为管理员不受影响。入口 https://fomobtc.com 302 跳转到机器人创建的邀请链接 https://t.me/+mdTufn9GK1UyODk0 （名称 fomobtc.com）。跳转由服务器 nginx 提供（scripts/deploy/nginx.conf）；若撤销该链接，需同步修改两处 return 302 并重新加载 nginx。

## 看门狗提醒（现行）
统一Worker `xiyunews` 每5分钟检查 https://api.xiyu.news/api/health，连续两次异常时通过同一机器人私聊运营者，不发到话题群；仍异常每2小时提醒，恢复后通知一次。旧 api.fomobtc.com 仅过渡保留；原KV保留，新目的地来源和安全注入已有记录；实际私聊收件未证明时如实标注，不能靠制造故障或测试消息验收。旧 `fomobtc-watchdog` 已停用，不执行独立部署或setup_watchdog.sh；现行操作入口只维护在[根单项目清单](../../project-docs/cloudflare-single-project.md)。
