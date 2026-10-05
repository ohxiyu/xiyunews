# 实时 API 域名迁移任务与验证入口

当前任务为[Issue216](https://github.com/ohxiyu/xiyunews/issues/216)。业务变更、DNS/证书/代理部署和监控自然验收的唯一证据维护在[根发布记录](../../../project-docs/releases/2026-10-05-realtime-api-domain.md)，不复制相互冲突的当前版本。

api.xiyu.news 为新主接口，api.fomobtc.com 过渡保留。只改域名代理和看门狗目标，不重新部署或重启采集发送应用。服务器SOURCE_COMMIT、数据库/env/Telegram目的地保持；WorkerSHA与东京应用SHA分别核验。2026-10-05业务PR217合并、nginx新旧TLS、统一部署37329563017和15:05:32Z自然watchdog已通过；完整精确ID、回退备份与未验证的手机通知见根证据，Issue218仅补录文档，不再次部署。
