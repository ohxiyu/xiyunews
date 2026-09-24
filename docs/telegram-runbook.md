# Telegram 运行与验收

## 当前结构
systemd `fomobtc` → Python asyncio采集 → SQLite事件/发送队列 → Telegram Bot API。
网页只是只读API客户端，关闭网页不影响服务。入口src/platform/app.py；发送src/platform/delivery.py；持久化src/platform/store.py；配置src/platform/settings.py。

## 配置
东京服务器配置文件 `/etc/fomobtc.env`，root:root，0600。SSH使用本机 `/Users/qxx/.ssh/fomobtc_tokyo_config` 中 `fomobtc-tokyo`；私钥留本机，不进仓库。没有该文件的新Agent需用户提供已有安全连接方式。
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
- 仅 USDT 现货，24h 成交额至少 50 万 USDT；突发滚动 1/3 分钟 + 3 秒确认，趋势 15 分钟收盘确认 6/24 小时涨跌及区间位置；参数见[数据契约](data-contract.md)。
- 取消同币种 24h 限制。突发按方向 15 分钟且重新越线；趋势按方向 6 小时，可追加一次突破。重启持久化，通知关闭期间也记门控，开启不补发旧事件。行情只发送规范中文标题，与网页一致。
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
在本机运行 `ssh -t -F ~/.ssh/fomobtc_tokyo_config fomobtc-tokyo 'sudo bash /opt/fomobtc/current/scripts/setup_telegram.sh'`。脚本隐藏输入 Token（不进命令行/日志），getMe 核验机器人，提示私聊 /start 后用 getUpdates 取私聊 Chat ID 并请用户确认，显示待发送队列，发送测试消息并等待用户确认手机收件，之后备份 /etc/fomobtc.env（0600）、写入 Token/Chat ID/TELEGRAM_ENABLED=true 并重启；启动失败自动恢复备份。自然事件推送仍需单独观察记录。

## 币安公告实时流（scripts/setup_binance_announcements.sh）
在本机运行 `ssh -t -F ~/.ssh/fomobtc_tokyo_config fomobtc-tokyo 'sudo bash /opt/fomobtc/current/scripts/setup_binance_announcements.sh'`。币安 API Key 只勾“启用读取”，IP 可不限制。脚本隐藏输入 Key/Secret，用签名的 /sapi/v1/account/apiRestrictions 校验有效且只读（开启任何交易、提现、划转权限即拒绝），备份 /etc/fomobtc.env 后写入并重启，40 秒内 binance_announcements 未变为 live 则自动恢复。
