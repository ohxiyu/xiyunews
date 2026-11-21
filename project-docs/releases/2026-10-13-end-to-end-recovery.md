# 第3项：端到端有限恢复

Source commit: PR合并前待记录；前置4521b69738750774a75018612896019c101a0058
Worker version: 部署后回读，当前18caa7c0-ee7c-4daf-a50d-8f2cb7744457
Deployment: 待当前PR通过后安装独立guardian和触发cloudflare-unified.yml
Verification: 离线覆盖停机/忙碌/暂停/3次24h预算、nginx定向注入；Worker覆盖失败30m冷却与2次4h预算、未知响应保留冷却和现役发布排队。生产与自然故障尚未验收。
Rollback: 旧Worker18caa7c0-ee7c-4daf-a50d-8f2cb7744457；如确需回退另获明确指示。可暂停guardian而不操作原实时服务。

仅当执行器inactive/failed、enabled、无Runner.Worker、无paused标志时执行systemctl start，绝不restart活跃任务。有限自愈最大3次/24h、30m冷却，先持久化预算再I/O。状态文件只包含service/status/checked_at/starts_24h，不证明GitHub网络连接正常；/ops/runtime.json是只读且no-store。原fomobtc进程、凭据、数据库、推送话题与Cron保持。

采集失败不再按启动时间误判fresh，尊重运营者cancelled。RecoveryGate按4h独立对象有限派发，未知响应消耗预算，避免重复AI调用；部署现役/卡住状态先等待，不重复构建。排队不擅自取消其他维护者任务。

安装：在严格SSH身份校验下，从合并SHA导出ops/runtime，服务器root运行python3 install.py。nginx只增加api.xiyu.news HTTPS段的精确只读路径；配置先备份0600，nginx -t失败自动还原，成功仅reload。暂停文件/var/lib/xiyunews-runtime/paused由运营者或任务隔离维护流程管理。

前置验收：PR263纯文档CI38386364633治理14s、范围11s成功；Python/web/edge/realtime明确跳过，原Pages预览成功。

当前实际：PR265于2026-10-13 19:14上海合并6dbc9bffe38db730ad6a300ab4dfcb5146f5792f，CI38387763044全部适用项成功（Python1m20s/web2m/edge3m43s/实时3.11与3.12均成功）。严格SSH安装guardian Result=success，定时器启用；只读runtime返回新鲜idle、starts_24h=0。原实时PID235825、NRestarts0。统一Worker发布38388839156进行中，不能把服务器安装等同Worker上线。

统一发布38388839156随后success；health回读Worker7c0f3e05-92a8-4bfc-937c-4bbbbf5b7c39、source6dbc9bffe38db730ad6a300ab4dfcb5146f5792f、artifact cd1b66613bd72f3a51622425565bc1b9775c34f1，runner=idle且状态新鲜。真实停机恢复未刻意制造，有限恢复离线故障测试与现役安装分别成立。
