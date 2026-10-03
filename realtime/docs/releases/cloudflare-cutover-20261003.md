# 实时看门狗并入 xiyunews：实际部署

Task: https://github.com/ohxiyu/xiyunews/issues/201，父任务 Issue198。
Source commit: 边缘 b2aeb97f8481bfad123277463c24bddac0895f8c；东京服务仍d6a9d3f29ef93c138842342c973b3049fb7bc252，不将边缘SHA当服务器重新发布。
Worker version: 00b0f0f6-f6cf-4ba7-9b79-96644eb6c7dc（统一自动部署后公网回读）。
Deployment: 2026-10-03统一Worker实际生产接管，首次[GitHub部署37122753609](https://github.com/ohxiyu/xiyunews/actions/runs/37122753609)成功；旧watchdog版本90b876b9-c47d-494b-afdc-9c3839be80a9已停用、无Cron。
Verification: 统一版本双开关true、原KV/DO和8个运行Secret名称保持；三现货分片live、单服务active、队列0，两轮自然看门狗通过，手机/实际私聊告警未验收。
Rollback: 原服务器release、SQLite/env备份保留，边缘原状态保持；任何回退需授权并先核对唯一调度者，不能恢复独立watchdog默认Cron造成双通知。

## 已执行

旧watchdog部署精确true停用保护并撤下Cron，回读原STATE KV ID469346950dfc4f36b8d9bf9997d960fa及两Secret名称保留；延迟旧回调直接no-op。统一Worker复用同一看门狗组件和KV，正式配置原*/5 Cron，使用已安全复用的@xiyunewsbot/原备份私聊目的地，不将运维提醒发送到话题群。

原RecoveryGate也已迁入统一Worker，namespace_id=d4f55a5a95624e7e9776bbf050cf1ee7保持；没有新建空状态、清库或写测试值。实际域迁移与自动部署的完整步骤见[根上线记录](../../../project-docs/releases/2026-10-03-cloudflare-production-verification.md)，本记录不提供另一个操作入口。

## 东京只读复核

严格指纹SSH回读MainPID235825/NRestarts0、ActiveState=active、current指向新仓d6a9d3f release；公网health的完整source_commit一致，Telegram启用，spot_stream_0/1/2全部live、ingestion_queue=0。Hyperliquid仍degraded，ready限制保留；没有为了迁移隐藏来源缺陷或重启服务。

原群xiyu.news、管理员@xiyunewsbot、话题3/5/7保留。自然消息回执、手机收件、私聊告警分别验收；本次不测试发送、不造故障、不重放旧消息，服务器env/SQLite/阈值/地址簿/nginx没有改动。

只读SQLite（mode=ro）核验Bot切换后125条sent、78条archived，无失败状态；最新行情1364、公告1352、流入1361，均为真实自然消息回执，不是本轮测试发送。统一两轮自然Cron计划12:30:51Z及12:35:51Z，均版本00b0f0f6、watchdog:ok、outcome=ok、exceptions=[]。

## 待验收

统一入口两轮自然scheduled已通过，下次真正到期的dispatch还需回读；实际私聊告警和手机收件未证明。旧资源仍保留，移除旧Worker时不能删除现用STATE/DO；旧仓仅main、无tags/开放PR、37个关闭PR均merged、main祖先已核验，但非Git历史不是subtree备份，不按主仓旧别名删除主仓。当前指针见[根交接](../../../project-docs/handoff.md)。
