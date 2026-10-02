# 2026-09-24 行情覆盖修复与大盘合并部署

部署状态：deployed
源码提交：38194b2acad231ccc2ad72ae4131314a28071053
运行版本：2.1.0 后端 systemd fomobtc，PID 156000，/opt/fomobtc/current 指向该 SHA 的 release；前端未变更。
验收结果：2026-09-24 11:28（北京时间）切换；systemd active；公网 health source_commit 为目标 SHA，宇宙 382 对（原 441，含 61 个下架币）；263 秒时 spot_stream_0/1 live，spot_stream_2 因 USDPUSDT 无成交 K 线 warming（PR #37 修复）；/api/ready 503（公告源降级及分片 2）。Telegram 未启用，未发送消息。
回退信息：旧 release f131fc0d8d0cc84f3ad7546aa904636208982c35 保留；备份 /opt/fomobtc/backups/20260924T032837Z-before-38194b2（SQLite integrity ok、env、previous_release）；依赖不变，沿用 98103447 虚拟环境链接。
授权记录：用户 2026-09-24 “提交部署”及“你直接给我审核一下合并”；未新增密钥。

## 过程
- git archive 上传 main，SHA-256 与本地一致；新目录解包、链接原虚拟环境、compileall 通过；与旧 release 仅 market/store/delivery 三个运行文件不同，requirements.lock 相同。
- 停服务，SQLite backup API 备份并 integrity_check；原子切换 current，更新 SOURCE_COMMIT，启动；失败自动回滚逻辑未触发。
