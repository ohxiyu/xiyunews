# 2026-10-02 新 Bot 凭据切换

部署状态：deployed
源码提交：d6a9d3f29ef93c138842342c973b3049fb7bc252
运行版本：2.6.0，systemd fomobtc，2026-10-02 21:03:05 Asia/Shanghai启动，MainPID235825、NRestarts0；源码release不变。现役看门狗Secret Change于21:03:11.654发布，版本a5330597-ee57-4a61-91f0-9a34cb431676为100%流量；未部署新Worker业务代码或统一Worker。
验收结果：21:06运行进程getMe为xiyunewsbot、与服务器配置Token一致，getChat为原forum群xiyuNews，getChatMember为administrator；原群和话题3/5/7保持、排除Token后所有配置与备份相同。三个spot分片live，SOURCE_COMMIT仍为新仓合并SHA，KV状态failing=0/alerted=false/lastAlert=0。截至该时点切换后没有新自然事件或message_id，不宣称送达或手机验收完成；Hyperliquid既有degraded保留。
回退信息：切换前配置与一致SQLite备份位于服务器root-only /opt/fomobtc/backups/xiyunews-bot-7dbntpvf，目录0700、文件0600；原release与先前迁移备份保留。没有回滚、补发或清队列；回退须单独授权，不恢复备份数据库覆盖新发送记录，不假设旧Bot仍有群权限。
授权记录：运营者指定新Bot为xiyunewsbot，明确确认“已经是管理员，保留原话题”；同意替换实时服务及看门狗凭据，并在本机隐藏输入中提供Token。没有扩大到更改群权限、创建话题、修改阈值/信源、改日报频道、新增Cloudflare访问密钥或删除旧资源。

## 安全输入与实际变更

临时本机脚本先按固定known_hosts校验SSH，再只读确认服务版本、群/话题与看门狗密钥名称。修复了桌面终端PATH可能找不到Node的兼容性问题，使用已安装Node绝对路径；纯JSON或带CLI通知/ANSI的输出均经过离线回归，错误仅输出分类。Token通过禁止回显的交互输入进入内存，经SSH stdin加密传送，不写本机文件、命令参数、环境变量、聊天或Git；Wrangler关闭磁盘日志和遥测，仅把Token经stdin更新到现役看门狗。

新Token先通过getMe、getChat和getChatMember核对身份与原群管理员资格，再备份配置、停止原systemd单实例、用SQLite backup API生成一致备份。只替换TELEGRAM_BOT_TOKEN并原子保存，随后由同一个systemd服务启动；不会启动第二实例。独立只读回读证实其余配置不变，话题为行情3、公告5、资金流向7，权限仍root0600。

## 未验证和下一步

没有发送测试消息、创建话题或人为制造行情。等待新Bot下一条真实触发消息，记录事件ID、发现/发送时间与telegram_id，再由运营者确认手机收件；旧Bot的failed/unknown不重放。现役看门狗私聊保留原ALERT_CHAT_ID，运营者需对新Bot/start，密钥更新和KV无告警不证明私聊送达。管理员can_manage_topics当前为false，不修改此权限，也不改动原话题；若自然发送实际被拒绝，先基于回执诊断，不盲目扩大权限。

## 切换后自然看门狗与回归

捕获新版本a5330597-ee57-4a61-91f0-9a34cb431676的真实Cron：计划时间21:10:23（Asia/Shanghai），实际事件时间21:10:32.765，outcome=ok、日志watchdog: ok、exceptions为空；没有人工派发或触发告警。21:11再次只读确认服务MainPID235825/NRestarts0、原群管理员身份和配置保留，切换后仍没有新自然事件。root-only备份目录0700、配置与SQLite文件0600，备份integrity_check=ok。

本轮交接修改通过根完整Python回归、根治理、实时61项测试和实时仓库契约；远端CI以PR197后续head为准。只更新运维说明与证据，没有发布应用新源码，不能把文档检查或看门狗无告警当作新Bot手机收件验证。

关联：[当前交接](../handoff.md)、[Telegram运行手册](../telegram-runbook.md)、[原新仓部署](deploy-20261002-xiyunews-repository.md)、[根交接](../../../project-docs/handoff.md)、[PR197](https://github.com/ohxiyu/xiyunews/pull/197)。Cloudflare单项目切换仍未实施，不提前删除现役服务或恢复入口。

## 后续私聊初始化确认（21:24）

运营者报告已/start；新Bot API核验到切换后的一条私聊/start，消息时间21:05:15（Asia/Shanghai），该私聊getChat可读取。不输出私聊ID、用户资料、其他消息或Token，没有发送测试消息或通过offset确认/清除更新；不再要求重复/start。未直接比对Cloudflare加密ALERT_CHAT_ID，私聊初始化不证明现役看门狗实际告警已经送达。

新看门狗计划21:15:23的第二轮自然Cron实际事件21:15:37.068，outcome=ok、日志watchdog: ok、exceptions为空；与21:10一轮一起，连续两次新版本检查通过。21:24服务仍MainPID235825/NRestarts0，原群administrator和话题3/5/7保留，仍没有切换后新自然事件。358807bc的CI37011428036及Pages预览全部可用检查通过，CodeQL跳过；本次补充仅为运维证据，不更换配置或部署应用。

## 后续三类自然回执验收

只读读取原 SQLite 在切换时间 1790946185 之后的事件，取得 11 条 `sent` 和 6 条按原规则 `archived`，没有失败/未知状态。以下是三类自然消息的最新成功回执，不是人为制造事件或测试发送。

| 类别 | 来源与事件 | Telegram message_id | 发送时间（Unix） |
| --- | --- | --- | --- |
| 行情 | Binance 现货 MOVRUSDT | 1251 | 1790953172.0610588 |
| 公告 | Bitget 公告 | 1250 | 1790952962.8294048 |
| 资金流向 | Binance USDC 流入 | 1249 | 1790952812.5198238 |

服务仍 active、MainPID235825/NRestarts0，getMe 为 @xiyunewsbot、原群 administrator，原话题 3/5/7 与其他配置未改。自然 Telegram API 回执已经确认，因此不再把“无新自然 message_id”列为阻塞；这不等于运营者手机收件或看门狗私聊实际告警已验证。群实际名称仍为 `xiyuNews`，精确统一为 `xiyu.news` 的资料更改尚未执行。
