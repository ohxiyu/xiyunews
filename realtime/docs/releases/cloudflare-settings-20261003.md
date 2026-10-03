# 统一边缘项目运行设置：已保存，生产未切换

Task: https://github.com/ohxiyu/xiyunews/issues/198
PR: https://github.com/ohxiyu/xiyunews/pull/199
Source commit: 服务器仍d6a9d3f29ef93c138842342c973b3049fb7bc252，不重新发布实时业务代码。
Deployment: partial，统一暂停Worker运行Secret变更版本ae8f5365-8fa6-417e-9d43-0046e8219e94；原fomobtc-watchdog仍生产。

2026-10-03按运营者生产配置授权，从服务器现役/root0600环境和进程读取@xiyunewsbot，核对源码、管理员相关配置与话题3/5/7保持。按照原scripts/setup_watchdog.sh的配置来源查话题切换前/etc/fomobtc.env.bak-*，仅有唯一positive私聊ID，getChat验证为private；并未重跑旧脚本的sendMessage或修改目标、创建话题、重启服务。原Cloudflare加密ALERT_CHAT_ID不能读取直接比较，新的目标来源与原设置脚本一致，实际告警收件仍待自然条件验收。

选定TELEGRAM_BOT_TOKEN/ALERT_CHAT_ID只经安全SSH子进程及Wrangler stdin保存为统一Worker加密Secrets，值没有发到模型、聊天、Git或文件日志；原看门狗的Secrets/Cron/KV未改。STATE仍计划复用469346950dfc4f36b8d9bf9997d960fa，新运行开关false，没有第二个定时发送者。

安全设置工具18项及运行Token工具19项假数据回归、实际只读来源检查通过，统一8个Secret名称及暂停health回读正确；根1019项、94项边缘和audit0通过。本轮完整实时双版本以当前PR远端CI为准，不能沿用前一提交通过。没有服务器数据库/阈值/信源/NGINX/群简介变更，也没有测试消息、历史补发或人为制造告警。

后续切换主域、迁原DO、停旧Cron后再启新Cron，验收新看门狗至少两次自然调用及STATE状态。手机收件与实际私聊告警仍独立记录，不用配置存在或/start代替证明；旧项目只有真实验收后才退役。根[交接](../../../project-docs/handoff.md)是唯一执行指针。

复查官方Cron传播延迟后，新代码为旧watchdog加入XIYUNEWS_LEGACY_DISABLED精确true入口no-op，离线断言旧回调不访问健康API、不读写KV或通知；默认未设置时行为保持。该保护尚未部署旧项目，也不设置在统一Worker；清空旧Cron后还需等待在途执行结束和回读停用证据，再启新调度，不提前声称旧资源停止。
