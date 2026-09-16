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
- 只监控现货；24h成交额低于50万USDT不监控；high≥1亿阈值2.5%，mid≥1000万阈值6%，low阈值10%。分钟桶口径约2–3分钟，非严格180秒。
- 同币种滚动24小时生成一次预警/通知；从预警生成计时，涨跌/升级共用。通知关闭期间网页预警也占额度，启用不会补发旧预警。重启不重置。
- 公告按文章去重；初始历史基线不推送；营销类默认不推送。中文正文/简讯ready才可发送；自动翻译尚未接入。
- 行情队列120秒过期，公告1小时过期。超时/中断可能已送达时记unknown，不自动假定失败；429遵守retry_after；5xx有限退避重试。保留回执。

## 后续优先级
P0：安全配置Bot和目标；收件验收；清理Telegram行情中英文技术说明，统一中文可读文案并测试转义/长度。
P1：官方中文缺失时接入用户选定的翻译服务；区分采集失败、翻译等待、过期、发送失败。
P2：自然事件延迟P95/P99、断线恢复与24小时稳定性。Binance/Hyperliquid当前为轮询降级，不承诺实时SLA。
暂缓：前端美化、图表、市值增强、历史回填、多市场扩张。

## 2026-09-16 私聊准备
用户已创建机器人，暂不加入群组。先在机器人私聊点击开始或发送/start，再由用户通过服务器编辑器将Token写入/etc/fomobtc.env，不要粘贴到聊天、命令参数或git。保持TELEGRAM_ENABLED=false，通过getUpdates识别私聊chat.id并核验目标后填写TELEGRAM_CHAT_ID。保留原有配置项，不覆盖整份文件。不关闭群组隐私模式、不申请群组权限。仍按上面的队列检查和启用顺序验收；本轮未发送消息。
